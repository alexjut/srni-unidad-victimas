"""
Management command: importar_usuarios_legacy

Trae el catálogo de encuestadores del legacy (`GIC_USUARIO`, ~8.100 filas) a
SICAV, y **mide qué tan rota está la autoría** del histórico.

──────────────────────────────────────────────────────────────────────────────
POR QUÉ ESTE CATÁLOGO NO ES UN "NICE TO HAVE"
──────────────────────────────────────────────────────────────────────────────
`GIC_HOGAR.USU_USUARIOCREACION` es una cadena suelta: no hay FK. Sin este
catálogo pasan tres cosas, en orden de gravedad:

1. **Un hogar puede ser invisible por culpa del usuario.** "Mis encuestas" se
   arma con `INNER JOIN GIC_USUARIO US ON US.USU_USUARIO = T.USU_USUARIOCREACION`
   (`src_GIC_N_CARACTERIZACION.sql:2451`). Si el usuario que capturó no tiene
   fila, el hogar no sale del listado **aunque esté cerrado y archivado**.

2. **No se puede enrutar una novedad.** Llega "el funcionario X caracterizó a
   esta persona y no aparece" y no hay a quién preguntarle ni cómo saber qué más
   capturó ese día.

3. **SICAV escribe hoy con un ÚNICO usuario de servicio.** Ese es el problema
   grande. `GIC_INSERT_HOGAR1` solo crea un hogar si el usuario **no tiene
   ninguno en ACTIVA**; si lo tiene, no crea nada y devuelve el código del viejo.
   Con un usuario compartido para todo SICAV, basta que **un** hogar quede
   abierto para que el siguiente —de otro encuestador, de otro municipio— caiga
   dentro. Traer este catálogo es el primer paso para dar de alta un
   `USU_IDUSUARIO` por encuestador y desactivar esa bomba.

──────────────────────────────────────────────────────────────────────────────
LO QUE ESTE COMANDO **NO** ARREGLA
──────────────────────────────────────────────────────────────────────────────
La autoría del histórico ya está rota y traerla no la repara. Medido antes en
producción: **1.077.712 hogares (97,7 %)** con un `USU_USUARIOCREACION`
inexistente en `GIC_USUARIO`, 9.424 cadenas distintas contra ~8.100 usuarios, y
el `USU_IDUSUARIO` sin cruzar en el 99,7 %.

Este comando **mide** ese hueco (`--medir-autoria`) para que deje de ser una nota
en un documento y pase a ser un número que se puede seguir. Cerrarlo hacia atrás
es otra decisión, y no es nuestra.

──────────────────────────────────────────────────────────────────────────────
QUÉ SE TRAE Y QUÉ NO
──────────────────────────────────────────────────────────────────────────────
Son funcionarios, no víctimas. Aun así se trae lo mínimo útil: quedan **fuera**
`USU_CONTRASENA` y `USU_TOKEN` (credenciales, que no hay por qué replicar) y los
campos de bloqueo. El documento sí entra: cuando el login del legacy no coincide
con el de SICAV, es lo único que reconoce a la misma persona.

En Oracle: **SOLO LECTURA**. Lo único que escribe es nuestro PostgreSQL, y solo
con `--confirmar`.

Uso:
    python manage.py importar_usuarios_legacy                    # DRY-RUN
    python manage.py importar_usuarios_legacy --confirmar
    python manage.py importar_usuarios_legacy --medir-autoria    # solo medir
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sincronizacion.models import UsuarioLegacy
from apps.sincronizacion.oracle.conexion import abrir_conexion, describir_destino
from apps.sincronizacion.oracle.mapeo import fecha_oracle_a_django

CONSULTA_USUARIOS = """
    SELECT usu_idusuario, usu_usuario,
           usu_primernombre, usu_segundonombre,
           usu_primerapellido, usu_segundoapellido,
           usu_documento, usu_correoelectronico,
           ent_identidad, est_idestado, usu_codigo,
           usu_dadodebaja, id_usuariovivanto, usu_fechacreacion
      FROM gic_usuario
     ORDER BY usu_idusuario
"""

#: Cuánto de la autoría del histórico se puede resolver con este catálogo. Se
#: miden dos cosas distintas: la cadena (`USU_USUARIOCREACION`, que es lo que usa
#: el INNER JOIN de "mis encuestas") y el id (`USU_IDUSUARIO`, que es lo que usan
#: los reportes de productividad).
#:
#: ⚠️ Con `EXISTS` correlacionados esto NO termina: son dos búsquedas por cada
#: una de las 1,1 M de filas de `gic_hogar` (medido: >5 min y seguía). Con dos
#: LEFT JOIN, `GIC_USUARIO` cabe en memoria —8.172 filas— y Oracle resuelve todo
#: con hash joins en una sola pasada. Es la misma lección que ya había costado
#: caro en `cargar_fechas_caracterizacion`: sobre esta base, correlacionar por
#: fila es la diferencia entre segundos y horas.
#:
#: El LEFT JOIN no multiplica filas porque los dos lados son únicos, y está
#: medido: `GIC_USUARIO` tiene 8.172 filas y 8.172 `usu_usuario` distintos, y
#: `usu_idusuario` es su PK. Si algún día dejara de serlo, los porcentajes
#: pasarían de 100 % y se vería.
MEDIR_AUTORIA = """
    SELECT COUNT(*),
           COUNT(uc.usu_usuario),
           COUNT(ui.usu_idusuario)
      FROM gic_hogar h
      LEFT JOIN gic_usuario uc
             ON UPPER(uc.usu_usuario) = UPPER(h.usu_usuariocreacion)
      LEFT JOIN gic_usuario ui
             ON ui.usu_idusuario = h.usu_idusuario
"""


def _texto(v) -> str:
    return "" if v is None else str(v).strip()


def _nombre_completo(pn, sn, pa, sa) -> str:
    return " ".join(p for p in (_texto(pn), _texto(sn), _texto(pa), _texto(sa)) if p)


class Command(BaseCommand):
    help = ("Trae GIC_USUARIO (encuestadores del legacy) a SICAV. "
            "Oracle SOLO LECTURA; escribe en PostgreSQL solo con --confirmar.")

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true",
                            help="Escribe en PostgreSQL. Sin esto, DRY-RUN.")
        parser.add_argument("--medir-autoria", action="store_true",
                            help="Solo mide el hueco de autoría del histórico. "
                                 "Recorre gic_hogar entero (1,1 M): no es rápido, "
                                 "por eso va aparte del import.")
        parser.add_argument("--destino", default="produccion",
                            choices=["produccion", "local"])

    def handle(self, *a, **o):
        self.stdout.write(self.style.WARNING(
            f"Oracle SOLO LECTURA · {describir_destino(o['destino'])}"))
        con = abrir_conexion(o["destino"])
        try:
            cur = con.cursor()
            if o["medir_autoria"]:
                self._medir(cur)
                return
            filas = self._leer(cur)
            # La medición NO va sola en cada import: recorre `gic_hogar` entero
            # (1,1 M de filas) con dos EXISTS correlacionados contra GIC_USUARIO.
            # Traer 8.100 usuarios son segundos; medir la autoría es otra cosa, y
            # que una importación rutinaria se vuelva lenta sin avisar es la forma
            # más segura de que alguien deje de correrla.
        finally:
            con.close()
        self._guardar(filas, confirmar=o["confirmar"])

    # ── lectura ──────────────────────────────────────────────────────────────
    def _leer(self, cur):
        cur.execute(CONSULTA_USUARIOS)
        filas = cur.fetchall()
        self.stdout.write(f"\nGIC_USUARIO: {len(filas)} usuarios.")
        con_vivanto = sum(1 for f in filas if f[12] is not None)
        de_baja = sum(1 for f in filas if str(f[11] or "0").strip() not in ("0", "", "None"))
        self.stdout.write(
            f"  con ID_USUARIOVIVANTO: {con_vivanto} · dados de baja: {de_baja}")
        return filas

    def _medir(self, cur):
        """El hueco de autoría, en números. Es la parte que no se puede arreglar."""
        cur.execute(MEDIR_AUTORIA)
        total, por_cadena, por_id = cur.fetchone()
        total = int(total or 0)
        por_cadena = int(por_cadena or 0)
        por_id = int(por_id or 0)
        self.stdout.write("\n=== Autoría del histórico ===")
        self.stdout.write(f"  hogares: {total:,}")
        if total:
            self.stdout.write(
                f"  con USU_USUARIOCREACION que SÍ existe en GIC_USUARIO: "
                f"{por_cadena:,} ({por_cadena * 100.0 / total:.1f} %)")
            self.stdout.write(
                f"  con USU_IDUSUARIO que SÍ cruza:                       "
                f"{por_id:,} ({por_id * 100.0 / total:.1f} %)")
            huerfanos = total - por_cadena
            if huerfanos:
                self.stdout.write(self.style.ERROR(
                    f"  ⚠️ {huerfanos:,} hogares ({huerfanos * 100.0 / total:.1f} %) "
                    f"tienen un creador que no existe en el catálogo. 'Mis encuestas' "
                    f"los excluye con su INNER JOIN, estén como estén."))

    # ── escritura (nuestra base, no Oracle) ──────────────────────────────────
    def _guardar(self, filas, *, confirmar):
        if not confirmar:
            self.stdout.write(self.style.WARNING(
                f"\nDRY-RUN: {len(filas)} usuarios listos para importar. "
                f"Nada se escribió. Repetí con --confirmar."))
            self._muestra(filas)
            return

        nuevos = actualizados = 0
        with transaction.atomic():
            for f in filas:
                (idu, login, pn, sn, pa, sa, doc, correo, ent, est, cod,
                 baja, vivanto, fcre) = f
                _, creado = UsuarioLegacy.objects.update_or_create(
                    usu_idusuario=int(idu),
                    defaults=dict(
                        usu_usuario=_texto(login),
                        nombre_completo=_nombre_completo(pn, sn, pa, sa),
                        documento=_texto(doc),
                        # El correo del legacy no siempre es un correo válido; si
                        # no lo es se deja vacío en vez de romper la importación
                        # entera por una fila con basura en ese campo.
                        correo=_texto(correo) if "@" in _texto(correo) else "",
                        ent_identidad=int(ent) if ent is not None else None,
                        est_idestado=int(est) if est is not None else None,
                        codigo=_texto(cod),
                        dado_de_baja=_texto(baja) not in ("", "0"),
                        id_usuario_vivanto=int(vivanto) if vivanto is not None else None,
                        creado_en_legacy=fecha_oracle_a_django(fcre),
                    ),
                )
                nuevos += creado
                actualizados += (not creado)
        self.stdout.write(self.style.SUCCESS(
            f"\nImportados: {nuevos} nuevos · {actualizados} actualizados "
            f"({UsuarioLegacy.objects.count()} en total)."))
        self._cruce_con_sicav()

    def _muestra(self, filas, limite=5):
        self.stdout.write("\n  Muestra (sin datos personales):")
        for f in filas[:limite]:
            self.stdout.write(
                f"    usu_idusuario={f[0]} login={_texto(f[1])} "
                f"vivanto={f[12]} baja={_texto(f[11]) not in ('', '0')}")

    def _cruce_con_sicav(self):
        """Cuántos de los del legacy tienen cuenta en SICAV, por código de usuario.

        No enlaza automáticamente: informar el solapamiento es útil; decidir que
        dos cuentas son la misma persona a partir de un login parecido es
        exactamente la clase de suposición que en este proyecto ya salió cara.
        """
        from apps.autenticacion.models import Usuario

        codigos = set(Usuario.objects.values_list("codigo_usuario", flat=True))
        if not codigos:
            return
        coinciden = UsuarioLegacy.objects.filter(usu_usuario__in=codigos).count()
        self.stdout.write(
            f"  cruce con usuarios de SICAV por código: {coinciden} de "
            f"{len(codigos)} cuentas SICAV tienen homónimo en el legacy "
            f"(no se enlazaron solas: eso se decide, no se adivina).")
