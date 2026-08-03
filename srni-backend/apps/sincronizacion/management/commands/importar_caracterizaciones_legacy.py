"""
Management command: importar_caracterizaciones_legacy

Trae las caracterizaciones que un encuestador hizo en el legacy, para que al
entrar a SICAV **vea lo que ya hizo** — con el estado real de cada una.

──────────────────────────────────────────────────────────────────────────────
POR QUÉ NO SE CRUZA POR `GIC_USUARIO`
──────────────────────────────────────────────────────────────────────────────
Porque perdería casi todo. El legacy arma "mis encuestas" con
`INNER JOIN GIC_USUARIO US ON US.USU_USUARIO = T.USU_USUARIOCREACION`
(`src_GIC_N_CARACTERIZACION.sql:2451`), y medido en producción **1.077.712
hogares (97,7 %)** tienen un creador que **no existe** en esa tabla.

`JGUARINH`, el del caso de Pandi, es uno: **18 caracterizaciones** y ninguna fila
de usuario. Si esta importación repitiera ese JOIN, ese encuestador entraría a
SICAV y vería cero — exactamente el problema que venimos a resolver.

Acá el vínculo es la **cadena** `USU_USUARIOCREACION`, comparada con el
`codigo_usuario` de SICAV. El catálogo se usa solo para enriquecer (nombre,
correo, id de Vivanto) cuando la fila existe.

──────────────────────────────────────────────────────────────────────────────
QUÉ TRAE Y QUÉ NO
──────────────────────────────────────────────────────────────────────────────
Trae el **recibo**, no la caracterización: código, fecha, estado, cuántas
personas, cuántas respuestas quedaron en cada tabla, cuántos capítulos, y el
veredicto de si los reportes la ven. **Sin PII**: ni nombres, ni documentos, ni
respuestas.

Eso último no es solo prudencia. Que el listado diga "la hiciste **y no está
contando**" es lo que lo vuelve útil: sin esa columna es una lista de códigos.

En Oracle: **SOLO LECTURA**. Lo único que escribe es nuestro PostgreSQL, con
`--confirmar`.

Uso:
    python manage.py importar_caracterizaciones_legacy --usuario JGUARINH
    python manage.py importar_caracterizaciones_legacy --usuarios-de-sicav --confirmar
    python manage.py importar_caracterizaciones_legacy --usuario JGUARINH --confirmar
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.sincronizacion.models import CaracterizacionLegacy, UsuarioLegacy
from apps.sincronizacion.oracle.conexion import abrir_conexion, describir_destino
from apps.sincronizacion.oracle.diagnostico import ESTADOS_VISIBLES, dictaminar
from apps.sincronizacion.oracle.mapeo import fecha_oracle_a_django

#: Todo lo que hace falta para el recibo de un hogar, en UNA consulta por
#: encuestador. Los conteos van como subconsultas escalares: son cuatro lookups
#: por índice sobre hogares de UN usuario (decenas de filas), no un barrido.
#: Cruzar estas cuatro tablas con joins para 1,1 M de hogares sería otra cosa —
#: por eso este comando trabaja por usuario y no de golpe.
CONSULTA = """
    SELECT h.hog_codigo, h.usu_usuariocreacion, h.usu_idusuario, h.estado,
           h.usu_fechacreacion, h.fecha_estado,
           (SELECT COUNT(*) FROM gic_miembros_hogar m
             WHERE m.hog_codigo = h.hog_codigo),
           (SELECT COUNT(*) FROM gic_n_respuestasencuesta_c c
             WHERE c.hog_codigo = h.hog_codigo),
           (SELECT COUNT(*) FROM gic_n_respuestasencuesta r
             WHERE r.hog_codigo = h.hog_codigo),
           (SELECT COUNT(*) FROM gic_n_capitulos_ter t
             WHERE t.hog_codigo = h.hog_codigo)
      FROM gic_hogar h
     WHERE UPPER(h.usu_usuariocreacion) = UPPER(:u)
     ORDER BY h.usu_fechacreacion DESC
"""


class Command(BaseCommand):
    help = ("Trae las caracterizaciones del legacy de un encuestador para que las "
            "vea en SICAV. Oracle SOLO LECTURA.")

    def add_arguments(self, parser):
        parser.add_argument("--usuario", help="Login del legacy (p.ej. JGUARINH).")
        parser.add_argument("--usuarios-de-sicav", action="store_true",
                            help="Todos los que tienen cuenta en SICAV, por su "
                                 "codigo_usuario.")
        parser.add_argument("--confirmar", action="store_true",
                            help="Escribe en PostgreSQL. Sin esto, DRY-RUN.")
        parser.add_argument("--destino", default="produccion",
                            choices=["produccion", "local"])

    def handle(self, *a, **o):
        logins = self._logins(o)
        if not logins:
            raise CommandError(
                "Nada que traer. Usá --usuario <login> o --usuarios-de-sicav "
                "(que necesita cuentas con codigo_usuario en SICAV).")

        self.stdout.write(self.style.WARNING(
            f"Oracle SOLO LECTURA · {describir_destino(o['destino'])}"))
        con = abrir_conexion(o["destino"])
        try:
            cur = con.cursor()
            recibos = []
            for login in logins:
                recibos.extend(self._leer(cur, login))
        finally:
            con.close()
        self._guardar(recibos, confirmar=o["confirmar"])

    def _logins(self, o):
        if o.get("usuario"):
            return [o["usuario"]]
        if o.get("usuarios_de_sicav"):
            from apps.autenticacion.models import Usuario
            return sorted(c for c in Usuario.objects.values_list(
                "codigo_usuario", flat=True) if c)
        return []

    def _leer(self, cur, login):
        cur.execute(CONSULTA, {"u": login})
        filas = cur.fetchall()
        visibles = sum(1 for f in filas if (f[3] or "").strip().upper() in ESTADOS_VISIBLES)
        aviso = "" if filas else "  ← sin caracterizaciones a su nombre"
        self.stdout.write(
            f"  {login:<16} {len(filas):>4} caracterización(es) · "
            f"{visibles} visible(s) para los reportes{aviso}")
        return [(login, f) for f in filas]

    def _guardar(self, recibos, *, confirmar):
        preparados = [self._preparar(login, f) for login, f in recibos]
        invisibles = [p for p in preparados if not p["visible_en_reportes"]]

        if not confirmar:
            self.stdout.write(self.style.WARNING(
                f"\nDRY-RUN: {len(preparados)} caracterización(es) listas. "
                f"Nada se escribió. Repetí con --confirmar."))
        else:
            catalogo = {u.usu_usuario.upper(): u for u in UsuarioLegacy.objects.all()}
            with transaction.atomic():
                for p in preparados:
                    # `defaults` sin la PK y sin mutar `p`: los mismos dicts se
                    # vuelven a leer abajo para el aviso, y un `pop` los dejaría
                    # sin `hog_codigo` justo cuando hay que imprimirlo.
                    defaults = {k: v for k, v in p.items() if k != "hog_codigo"}
                    defaults["usuario_legacy"] = catalogo.get(
                        p["usuario_creador"].upper())
                    CaracterizacionLegacy.objects.update_or_create(
                        hog_codigo=p["hog_codigo"], defaults=defaults)
            self.stdout.write(self.style.SUCCESS(
                f"\nGuardadas {len(preparados)} caracterización(es)."))

        if invisibles:
            self.stdout.write(self.style.ERROR(
                f"\n⚠️ {len(invisibles)} de {len(preparados)} NO son visibles para "
                f"los reportes de la UARIV:"))
            for p in invisibles[:15]:
                self.stdout.write(
                    f"    {p['hog_codigo']:<28} {p['estado']:<20} {p['veredicto']}")
            self.stdout.write(
                "  Cada una es trabajo hecho que hoy no cuenta en ningún reporte.")

    @staticmethod
    def _preparar(login, fila):
        (hog, creador, idu, estado, fcre, fest, miembros, definitivas,
         trabajo, capitulos) = fila
        estado_txt = (estado or "").strip()
        # El mismo veredicto que usa el diagnóstico, con lo que ya trajimos: no
        # hace falta volver a Oracle por hogar. Los campos que acá no se miden
        # (validadores, territorio) los rellena `dictaminar` con sus defaults, y
        # por eso NO se guardan sus carencias: serían falsos negativos.
        v = dictaminar({
            "hog_codigo": hog, "donde": "GIC_HOGAR", "estado": estado_txt,
            "creado_por": creador, "id_usuario": idu,
            "miembros": int(miembros or 0), "encuestados": 1,
            "en_trabajo": int(trabajo or 0), "definitivas": int(definitivas or 0),
            "capitulos": int(capitulos or 0),
        })
        return {
            "hog_codigo": hog,
            "usuario_creador": (creador or login or "").strip(),
            "usu_idusuario": int(idu) if idu is not None else None,
            "estado": estado_txt,
            "creado_en_legacy": fecha_oracle_a_django(fcre),
            "fecha_estado": fecha_oracle_a_django(fest),
            "miembros": int(miembros or 0),
            "respuestas_definitivas": int(definitivas or 0),
            "respuestas_trabajo": int(trabajo or 0),
            "capitulos": int(capitulos or 0),
            "veredicto": v["veredicto"],
            "visible_en_reportes": estado_txt.upper() in ESTADOS_VISIBLES
                                   and int(definitivas or 0) > 0,
        }
