"""
Management command: diagnosticar_encuesta_legacy

Responde una sola pregunta, la que llega del territorio: **"se caracterizó a esta
persona y la encuesta no aparece — ¿dónde está?"**

──────────────────────────────────────────────────────────────────────────────
POR QUÉ HACE FALTA UN COMANDO PARA ESTO
──────────────────────────────────────────────────────────────────────────────
Porque en el legacy "no aparece" tiene **al menos seis causas distintas**, todas
se ven igual desde la consulta, y en cuatro de ellas **el dato NO se perdió**:
está escrito y solo le falta un paso para ser visible. Distinguirlas mirando ocho
tablas a mano, caso por caso, no escala — y la diferencia entre una y otra es si
hay que volver a la vereda o no.

Las causas, con lo que las delata:

1. **La encuesta nunca se cerró.** `SP_ACTUALIZAR_ESTADO_ENCUESTA(...,'4')` solo
   archiva si el hogar tiene **más de 3 capítulos** terminados; con 3 o menos cae
   en un `ELSE NULL` literal y **termina sin error**. El aplicativo mostró
   "guardado". El hogar queda ACTIVA y las respuestas se quedan en
   `GIC_N_RESPUESTASENCUESTA` (la tabla de trabajo), sin pasar nunca a
   `GIC_N_RESPUESTASENCUESTA_C`, que es **la única que leen los reportes**.
   ⇒ *El dato está. Es recuperable.*

2. **El hogar se fundió con otro.** `GIC_INSERT_HOGAR1` solo crea si el usuario
   **no tiene ningún hogar en ACTIVA**; si lo tiene, no crea nada y devuelve el
   código del hogar viejo. Todo lo que el encuestador capture después entra en la
   caracterización anterior, que puede ser de otra familia.
   ⇒ *El dato está, colgado del hogar equivocado.*

3. **La persona existe pero es invisible para la búsqueda por documento.** Los
   reportes y la consulta cruzan por `R_NUMERODOC` —la columna espejo—, no por
   `PER_NUMERODOC`. Una fila con el espejo vacío existe y no la encuentra nadie.
   ⇒ *El dato está, y la consulta miente.*

4. **Se cerró pero sin archivar.** `CERRAR_ENCUESTA` (que no es el mismo
   procedure) hace `UPDATE ESTADO='CERRADA'` y no mueve nada: hogar marcado como
   terminado con cero respuestas en la definitiva. El peor estado posible.

5. **Nunca llegó a la base.** La aplicación móvil vieja no escribe en la base:
   deja un JSON en un FTP que recogen **cuatro jobs encadenados de noche**
   (20:15 → 20:45 → 22:30 → 23:30). Si cualquiera falla, no hay error para nadie
   y el encuestador ya vio "enviado".
   ⇒ *Este es el único caso en que el dato puede haberse perdido de verdad.*

6. **Se migró al histórico.** `GIC_HOGAR_HISTORICO` existe y hay un job a la
   01:30; una consulta que solo mire `GIC_HOGAR` no lo encuentra.

7. **El encuestador no existe en `GIC_USUARIO`.** `SP_REPORTE_MIEMBROSXCODIGO`
   arma "mis encuestas" con un **`INNER JOIN GIC_USUARIO US ON US.USU_USUARIO =
   T.USU_USUARIOCREACION`** (`src_GIC_N_CARACTERIZACION.sql:2451`). Si el usuario
   que capturó no tiene fila en esa tabla, el hogar **desaparece del listado**
   aunque esté cerrado, archivado y perfecto.
   Y no es un caso raro: medido sobre producción, **1.077.712 hogares (97,7 %)**
   tienen un `USU_USUARIOCREACION` que no existe en `GIC_USUARIO`, y el
   `USU_IDUSUARIO` no cruza en el 99,7 %.
   ⇒ *El dato está, y el listado que lo debería mostrar lo excluye por un JOIN.*

──────────────────────────────────────────────────────────────────────────────
SOLO LECTURA — SIN EXCEPCIONES
──────────────────────────────────────────────────────────────────────────────
Este comando **solo ejecuta SELECT**. No tiene `--confirmar` ni forma de
escribir, a propósito: es la herramienta que se usa cuando algo ya salió mal, y
en ese momento la tentación de "arreglarlo de una" es máxima. Reparar es otra
decisión, con respaldo previo y por la ruta de procedures.

No imprime PII. De los nombres y documentos informa si están **presentes o
vacíos** —que es justamente el diagnóstico del caso 3— nunca su contenido.

──────────────────────────────────────────────────────────────────────────────
USO
──────────────────────────────────────────────────────────────────────────────
    # Un caso reportado desde el territorio
    python manage.py diagnosticar_encuesta_legacy --documento 1070752540

    # Todo lo de un encuestador (p.ej. tras una novedad)
    python manage.py diagnosticar_encuesta_legacy --usuario JGUARINH --dias 90

    # Un hogar concreto
    python manage.py diagnosticar_encuesta_legacy --hogar 999999-2W832

    # BARRIDO: encontrar todas las encuestas invisibles antes de que las reporten
    python manage.py diagnosticar_encuesta_legacy --perdidas --dias 60
"""
from django.core.management.base import BaseCommand, CommandError

from apps.sincronizacion.oracle import procedimientos as P
from apps.sincronizacion.oracle.conexion import abrir_conexion, describir_destino
from apps.sincronizacion.oracle.diagnostico import (
    _presente, barrido, diagnosticar, hogares_de_persona, hogares_de_usuario,
    personas_por_documento,
)


class Command(BaseCommand):
    help = ("Diagnostica por qué una encuesta caracterizada no aparece en los "
            "reportes del legacy. SOLO LECTURA.")

    def add_arguments(self, parser):
        parser.add_argument("--documento", help="Documento de la persona reportada.")
        parser.add_argument("--usuario", help="Usuario del legacy (p.ej. JGUARINH).")
        parser.add_argument("--hogar", help="HOG_CODIGO concreto.")
        parser.add_argument("--perdidas", action="store_true",
                            help="Barrido: encuestas con datos que los reportes no ven.")
        parser.add_argument("--dias", type=int, default=60,
                            help="Ventana hacia atrás (default 60).")
        parser.add_argument("--destino", default="produccion",
                            choices=["produccion", "local"])

    def handle(self, *a, **o):
        modos = [o.get("documento"), o.get("usuario"), o.get("hogar"), o.get("perdidas")]
        if sum(1 for m in modos if m) != 1:
            raise CommandError(
                "Elegí exactamente un modo: --documento, --usuario, --hogar o --perdidas.")

        self.stdout.write(self.style.WARNING(
            f"SOLO LECTURA · {describir_destino(o['destino'])}"))
        con = abrir_conexion(o["destino"])
        try:
            cur = con.cursor()
            if o["perdidas"]:
                self._barrido(cur, o["dias"])
            else:
                self._caso(cur, o)
        finally:
            con.close()

    # ── modos ────────────────────────────────────────────────────────────────
    def _caso(self, cur, o):
        codigos = []
        if o.get("hogar"):
            codigos = [o["hogar"]]
        elif o.get("usuario"):
            codigos = hogares_de_usuario(cur, o["usuario"], o["dias"])
            self.stdout.write(f"\nUsuario {o['usuario']}: {len(codigos)} hogar(es) "
                              f"en los últimos {o['dias']} días.")
        else:
            personas = personas_por_documento(cur, o["documento"])
            self.stdout.write(f"\n=== La persona en GIC_PERSONA: {len(personas)} fila(s) ===")
            if not personas:
                self.stdout.write(self.style.ERROR(
                    "  Ninguna fila con ese documento, ni por PER_NUMERODOC ni por "
                    "R_NUMERODOC. La persona no está en la base."))
                return
            for (pid, por_per, por_r, pn, rn, est, fuente, idmi, fcre, usu) in personas:
                aviso = "" if por_r else "  ⚠️ INVISIBLE para la búsqueda por documento"
                self.stdout.write(
                    f"  per_idpersona={pid} estado={est} fuente={fuente} "
                    f"idmodelint={idmi} creada={fcre} por={usu}")
                self.stdout.write(
                    f"    identidad: PER_* {'presente' if _presente(pn) else 'VACÍA'} · "
                    f"espejo R_* {'presente' if _presente(rn) else 'VACÍA'}"
                    f"{self.style.ERROR(aviso) if aviso else ''}")
                for h in hogares_de_persona(cur, pid):
                    if h not in codigos:
                        codigos.append(h)

        if not codigos:
            self.stdout.write(self.style.ERROR(
                "\nLa persona existe pero NO está en ningún hogar "
                "(GIC_MIEMBROS_HOGAR vacío): la caracterización no la vinculó."))
            return

        for codigo in codigos:
            self._imprimir(diagnosticar(cur, codigo))

    def _imprimir(self, d):
        self.stdout.write(f"\n=== Hogar {d['hog_codigo']} ({d['donde']}) ===")
        if d.get("estado") is not None:
            self.stdout.write(
                f"  estado={d['estado']} creado={d.get('creado_en')} "
                f"por={d.get('creado_por')} (id_usuario={d.get('id_usuario')}, "
                f"perfil={d.get('perfil')})")
            self.stdout.write(
                f"  miembros={d['miembros']} encuestados={d['encuestados']} · "
                f"respuestas: trabajo={d['en_trabajo']} definitiva={d['definitivas']} · "
                f"capítulos={d['capitulos']} · territorio={d['territorio']}")

        estilo = {
            "COMPLETO": self.style.SUCCESS,
            "NO_LLEGO": self.style.ERROR,
            "CERRADO_SIN_ARCHIVAR": self.style.ERROR,
            "SIN_RESPUESTAS": self.style.ERROR,
        }.get(d["veredicto"], self.style.WARNING)
        self.stdout.write(estilo(f"  ⇒ {d['veredicto']}"))
        self.stdout.write(f"    {d['explicacion']}")
        for c in d.get("carencias", []):
            self.stdout.write(f"    · {c}")

    def _barrido(self, cur, dias):
        filas = barrido(cur, dias)
        self.stdout.write(
            f"\n=== Encuestas con datos que los reportes NO ven "
            f"(últimos {dias} días) ===")
        if not filas:
            self.stdout.write(self.style.SUCCESS("  Ninguna. "))
            return
        self.stdout.write(
            f"  {len(filas)} hogar(es). Cada uno tiene respuestas capturadas en la "
            f"tabla de trabajo y un estado que los reportes filtran.\n")
        self.stdout.write("  hogar                estado        usuario      fecha       resp  cap")
        for hog, est, usu, fecha, resp, cap in filas:
            marca = "  ← el cierre no puede funcionar" if cap < P.CAPITULOS_MINIMOS_PARA_CERRAR else ""
            self.stdout.write(
                f"  {str(hog):<20} {str(est):<13} {str(usu or ''):<12} {fecha}  "
                f"{resp:>4}  {cap:>3}{marca}")
        self.stdout.write(self.style.WARNING(
            f"\n  Son {len(filas)} caracterizaciones hechas cuyo dato existe y "
            f"nadie ve. Cada una es una visita a campo que puede no repetirse."))
