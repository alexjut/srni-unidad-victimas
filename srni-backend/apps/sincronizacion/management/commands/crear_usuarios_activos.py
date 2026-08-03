"""
Management command: crear_usuarios_activos

Crea cuentas de SICAV para los encuestadores que **están trabajando hoy**, con su
identidad real, para que al entrar vean lo que ya hicieron.

──────────────────────────────────────────────────────────────────────────────
POR QUÉ NO SE CREAN DESDE `GIC_USUARIO`
──────────────────────────────────────────────────────────────────────────────
Porque ese catálogo está **muerto desde 2017**. Sus altas por año:

    2017: 1.994   2016: 3.046   2015: 2.646   2014: 482   2013: 3

Nada después. Y se nota donde importa: de los **1.153 encuestadores que
capturaron en los últimos 90 días, solo 26 tienen ficha ahí**. `JGUARINH` no
está, y tiene 18 caracterizaciones.

Crear cuentas desde `GIC_USUARIO` habría producido 8.172 cuentas de gente que en
su mayoría ya no trabaja —superficie de ataque, no un favor— y **habría dejado
fuera al 97 % de quienes sí están capturando**.

──────────────────────────────────────────────────────────────────────────────
DÓNDE ESTÁ EL DIRECTORIO DE VERDAD
──────────────────────────────────────────────────────────────────────────────
En Vivanto: `ADMINUSUARIOS.USUARIO` (81.352 filas) ⨝ `ADMINUSUARIOS.PERSONA`,
por el dblink que ya se usaba para el padrón.

Y ahí se cerró un cabo suelto: **`GIC_HOGAR.USU_IDUSUARIO` es el `IDUSUARIO` de
Vivanto**, no el de `GIC_USUARIO`. `JGUARINH` es `idusuario=197035` en Vivanto, y
sus hogares se llaman `197035-31TUK`. Por eso ese campo "no cruzaba" con el
catálogo local en el 99,7 % de los casos: nunca apuntó ahí. Lo que parecía dato
roto era una lectura equivocada de nuestra parte.

El directorio de Vivanto además está **sano**, al revés que el local. Medido
sobre los activos de 90 días: 1.150 de 1.153 encontrados (99,7 %), todos
marcados activos, todos con correo y **cero correos repetidos** — contra los 608
duplicados de `GIC_USUARIO`.

──────────────────────────────────────────────────────────────────────────────
LA CONTRASEÑA NO SE COPIA. NUNCA.
──────────────────────────────────────────────────────────────────────────────
`ADMINUSUARIOS.USUARIO` tiene una columna `CONTRASENA` y este comando **no la
lee**. Replicar credenciales de un sistema a otro multiplica el daño de
cualquier filtración y deja dos verdades sobre la misma clave.

Las cuentas se crean con contraseña **inutilizable**
(`set_unusable_password()`): existen, tienen su identidad y su trabajo asociado,
y **no se puede entrar con ellas** hasta que alguien defina cómo se entrega el
acceso. Eso es a propósito: crear 1.150 cuentas con clave conocida sería peor que
no crearlas.

⚠️ **Queda pendiente decidir el mecanismo de acceso** (restablecimiento por
correo, o que SICAV valide contra Vivanto). Hasta entonces estas cuentas sirven
para asociar el trabajo, no para iniciar sesión.

En Oracle: **SOLO LECTURA**. Escribe en PostgreSQL solo con `--confirmar`.

Uso:
    python manage.py crear_usuarios_activos --dias 90
    python manage.py crear_usuarios_activos --dias 30 --confirmar
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sincronizacion.oracle.conexion import abrir_conexion, describir_destino

#: Encuestadores con captura en la ventana, cruzados con el directorio VIVO.
#: El `DISTINCT` va primero, en una CTE: sin él el join se haría contra 8.017
#: hogares en vez de contra 600 logins.
#:
#: La `Ñ` viene rota en algunos logins y hay que repararla ANTES de agrupar.
#: Medido con `DUMP()` sobre producción: `ADMONTAÑOP` existe con la `Ñ` correcta
#: (`0,d1`, 2.167 hogares) y también como `ADMONTAÃ?OP` (`0,c3,0,3f`), que es el
#: UTF-8 de la `Ñ` escrito por un cliente con el juego de caracteres mal
#: configurado, con el segundo byte ya perdido como `?`. Son **6 logins y 131
#: hogares** cuyo autor, sin esto, no se resuelve: su encuestador nunca los vería
#: en "lo que hice".
#:
#: La reparación **no adivina**: reemplaza y deja que el `LEFT JOIN` contra el
#: directorio decida. Si el login reparado existe en Vivanto, era eso; si no,
#: queda sin cruzar y se reporta. No se acepta ninguna identidad que el
#: directorio no confirme.
CONSULTA = """
  WITH activos AS (
    SELECT REPLACE(UPPER(TRIM(usu_usuariocreacion)), 'Ã?', 'Ñ') login,
           COUNT(*) hogares,
           MAX(usu_fechacreacion) ultima
      FROM gic_hogar
     WHERE usu_fechacreacion >= SYSDATE - :n
       AND usu_usuariocreacion IS NOT NULL
     GROUP BY REPLACE(UPPER(TRIM(usu_usuariocreacion)), 'Ã?', 'Ñ')
  )
  SELECT a.login, a.hogares, a.ultima,
         u.idusuario, u.activo,
         p.primernombre, p.segundonombre, p.primerapellido, p.segundoapellido,
         p.correo, p.documento
    FROM activos a
    LEFT JOIN ADMINUSUARIOS.USUARIO@DBL_VIVANTO u
           ON UPPER(TRIM(u.usuarioingreso)) = a.login
    LEFT JOIN ADMINUSUARIOS.PERSONA@DBL_VIVANTO p
           ON p.idpersona = u.idpersona
   ORDER BY a.hogares DESC
"""

#: `Perfil` con el que se crean. Son encuestadores de campo: el perfil más
#: acotado. Subir permisos es una decisión de alguien, bajarlos después de un
#: incidente ya no sirve de nada.
PERFIL_ENCUESTADOR = "Encuestador de Campo"


def _texto(v) -> str:
    return "" if v is None else str(v).strip()


class Command(BaseCommand):
    help = ("Crea cuentas SICAV para los encuestadores activos, con su identidad "
            "de Vivanto. Oracle SOLO LECTURA.")

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=90,
                            help="Ventana de actividad (default 90).")
        parser.add_argument("--confirmar", action="store_true",
                            help="Crea las cuentas. Sin esto, DRY-RUN.")
        parser.add_argument("--destino", default="produccion",
                            choices=["produccion", "local"])

    def handle(self, *a, **o):
        self.stdout.write(self.style.WARNING(
            f"Oracle SOLO LECTURA · {describir_destino(o['destino'])}"))
        con = abrir_conexion(o["destino"])
        try:
            cur = con.cursor()
            cur.execute(CONSULTA, {"n": o["dias"]})
            filas = cur.fetchall()
        finally:
            con.close()
        self._procesar(filas, dias=o["dias"], confirmar=o["confirmar"])

    def _procesar(self, filas, *, dias, confirmar):
        from apps.autenticacion.models import Perfil, Usuario

        existentes = {c.upper() for c in
                      Usuario.objects.values_list("codigo_usuario", flat=True)}
        correos_usados = {e.lower() for e in
                          Usuario.objects.values_list("email", flat=True) if e}

        crear, sin_ficha, ya_estaban, sin_correo = [], [], [], []
        for (login, hogares, ultima, idusuario, activo, pn, sn, pa, sa,
             correo, doc) in filas:
            login = _texto(login)
            if login.upper() in existentes:
                ya_estaban.append(login)
                continue
            if idusuario is None:
                # Capturó, pero no está en el directorio. No se inventa identidad.
                sin_ficha.append((login, int(hogares or 0)))
                continue
            mail = _texto(correo).lower()
            if not mail or mail in correos_usados:
                sin_correo.append((login, int(hogares or 0), mail or "(vacío)"))
                continue
            correos_usados.add(mail)
            crear.append({
                "codigo_usuario": login,
                "nombre_completo": " ".join(
                    p for p in (_texto(pn), _texto(sn), _texto(pa), _texto(sa)) if p),
                "email": mail,
                "hogares": int(hogares or 0),
            })

        self.stdout.write(f"\n=== Encuestadores con captura en {dias} días: {len(filas)} ===")
        self.stdout.write(f"  ya tienen cuenta en SICAV : {len(ya_estaban)}")
        self.stdout.write(f"  listos para crear         : {len(crear)}")
        if sin_ficha:
            self.stdout.write(self.style.ERROR(
                f"  sin ficha en Vivanto      : {len(sin_ficha)}  "
                f"→ {', '.join(f'{l} ({h})' for l, h in sin_ficha[:6])}"))
            self.stdout.write(
                "     (capturaron, pero no hay de dónde sacar su nombre ni su "
                "correo. No se inventa identidad: hay que pedirlos.)")
        if sin_correo:
            self.stdout.write(self.style.WARNING(
                f"  sin correo utilizable     : {len(sin_correo)}  "
                f"→ {', '.join(l for l, _, _ in sin_correo[:6])}"))

        if not confirmar:
            self.stdout.write(self.style.WARNING(
                "\nDRY-RUN: no se creó ninguna cuenta. Repetí con --confirmar."))
            for c in crear[:8]:
                self.stdout.write(
                    f"    {c['codigo_usuario']:<16} {c['hogares']:>5} hogares")
            return

        perfil = Perfil.objects.filter(nombre=PERFIL_ENCUESTADOR).first()
        creados = 0
        with transaction.atomic():
            for c in crear:
                u = Usuario(codigo_usuario=c["codigo_usuario"],
                            nombre_completo=c["nombre_completo"],
                            email=c["email"], perfil=perfil, activo=True)
                # Ni se copia la de Vivanto ni se inventa una: la cuenta existe
                # para asociar el trabajo, y el acceso se habilita aparte.
                u.set_unusable_password()
                u.save()
                creados += 1
        self.stdout.write(self.style.SUCCESS(
            f"\nCreadas {creados} cuentas (perfil: {perfil}). "
            f"Todas SIN contraseña utilizable."))
        self.stdout.write(self.style.WARNING(
            "  ⚠️ Todavía NO pueden iniciar sesión. Falta decidir cómo se entrega "
            "el acceso: restablecimiento por correo, o que SICAV valide contra "
            "Vivanto. Crear 1.150 cuentas con clave conocida sería peor que no "
            "crearlas."))
