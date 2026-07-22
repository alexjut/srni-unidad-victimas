"""
Management command: cargar_hogar_demo_oracle

Prepara UN hogar SICAV listo para ejercitar la ruta de escritura hacia Oracle legacy
(Etapa A). Es el andamio del **Escalón 1 del rollout**: el hogar con el que se corre
`escribir_a_oracle` primero en DRY-RUN y después, con aprobación, `--confirmar` contra
el Oracle **local**.

Qué añade (el fixture `dump/hogares_demo_10.json` NO trae nada de esto):
  - una `SesionEncuesta` con **territorio de atención que SÍ cruza al crosswalk real**
    de `GIC_N_DT_PUNTOS_ATENCION`,
  - un `PuntoAtencion` con el nombre exacto que Oracle conoce,
  - dos respuestas: una de nivel PERSONA y una de nivel HOGAR (los dos caminos que
    recorre el paso RESPUESTA del escritor).

Uso:
    python manage.py loaddata dump/hogares_demo_10.json     # precondición
    python manage.py cargar_hogar_demo_oracle
    python manage.py escribir_a_oracle --hogar LISTO-96001  # DRY-RUN

Idempotente: `update_or_create` + recreación de la sesión demo en cada corrida.

Por qué un command y no un fixture JSON
---------------------------------------
El territorio tiene que cruzar a Oracle **por nombre** (los ids de Oracle son
surrogate, no DANE — ver oracle/mapeo.resolver_territorio). Un fixture tendría que
referenciar `Municipio`/`Departamento` **por PK**, porque esos modelos no definen
`natural_key()`; las PK dependen del orden de carga del CSV DANE y ya hay constancia
de esa fragilidad en `dump/README.md` §Precondiciones. Un command resuelve por nombre
y falla claro si falta la paramétrica, que es justo lo que necesita el Escalón 1.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.encuestas.models import RespuestaEncuesta, SesionEncuesta
from apps.formulario.models import Capitulo, Instrumento, OpcionRespuesta, Pregunta
from apps.hogares.models import Hogar
from apps.parametricas.models import (
    Departamento, DireccionTerritorial, Municipio, PuntoAtencion,
)

HOGAR_DEMO = "LISTO-96001"

# Fila REAL del volcado de GIC_N_DT_PUNTOS_ATENCION (prod, 2026-07-15):
#   IDDT=7 / IDDEPARTAMENTO=30 / IDPUNTOATENCION=13 / IDMUNICIPIO=32
# Se eligió a propósito una combinación que existe en Oracle: así el paso TERRITORIO
# resuelve ids reales en vez de marcadores, que es lo que el Escalón 1 debe demostrar.
# El punto va con TILDE ('ATENCIÓN') aunque Oracle lo tenga sin tilde: ejercita la
# normalización de resolver_territorio en vez de esquivarla.
TERRITORIO_DEMO = {
    "dt": "DIRECCION TERRITORIAL CENTRAL",
    "departamento": "Tolima",
    "municipio_dane": "73026",  # ALVARADO
    "punto_codigo": "PA_DEMO_ORACLE_JORNADAS",
    "punto_nombre": "JORNADAS DE ATENCIÓN Y/O FERIAS DE SERVICIO",
}
IDS_ORACLE_ESPERADOS = {"id_dt": 7, "id_depto": 30, "id_pt": 13, "id_ma": 32}

# Preguntas demo: una por nivel, calcadas del catálogo REAL de Oracle
# (respuestas_oracle.json) para que el paso RESPUESTA resuelva ids de verdad.
#
# `id_preg` es el puente verificado hacia GIC_N_PREGUNTAS.PRE_IDPREGUNTA (14/14 ids,
# 52/59 textos), y la `etiqueta` debe cruzar LITERALMENTE con RES_RESPUESTA de Oracle
# —incluido el paréntesis de "(donde está la alcaldía)"— porque el cruce de opciones
# es por texto normalizado y aquí no se hace fuzzy matching.
#
# ⚠️ `id_resp_vivanto` se deja a propósito con el valor del Diccionario V8 (4599=Mujer,
# 4572=Cabecera) AUNQUE NO sea el RES_IDRESPUESTA de Oracle (69 y 8): así el escenario
# sigue reproduciendo la trampa refutada, y el resolver demuestra que NO lo usa.
PREGUNTAS_DEMO = [
    {
        # Oracle: pregunta 24 'Sexo' → 68 Hombre / 69 Mujer / 968 Intersexual.
        "capitulo": ("DEMO_P", "Demo — nivel persona", "PERSONA", 90),
        "codigo_externo": "DEMO_SEXO", "texto": "Sexo", "nivel": "PERSONA",
        "id_preg": 24,
        "opcion": {"valor": "2", "etiqueta": "Mujer", "id_resp_vivanto": 4599},
        "res_idrespuesta_esperado": 69,
    },
    {
        # Oracle: pregunta 5 'Zona de residencia' → 8 Cabecera / 9 Centro poblado / 10 Rural.
        "capitulo": ("DEMO_H", "Demo — nivel hogar", "HOGAR", 91),
        "codigo_externo": "DEMO_ZONA", "texto": "Zona de residencia", "nivel": "HOGAR",
        "id_preg": 5,
        "opcion": {"valor": "1", "etiqueta": "Cabecera municipal (donde está la alcaldía)",
                   "id_resp_vivanto": 4572},
        "res_idrespuesta_esperado": 8,
    },
]


class Command(BaseCommand):
    help = ("Prepara el hogar demo (sesión + territorio que cruza a Oracle + respuestas) "
            "para el Escalón 1 de la escritura a Oracle legacy.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--hogar", default=HOGAR_DEMO,
            help=f"codigo_hogar sobre el que montar el escenario (por defecto {HOGAR_DEMO}).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        hogar = self._hogar(opts["hogar"])
        self._asegurar_creador(hogar)
        dt, depto, muni, punto = self._territorio()
        instrumento = self._instrumento()

        # La sesión se recrea: es dato de andamio, y así el comando es repetible sin
        # arrastrar respuestas de corridas anteriores.
        SesionEncuesta.objects.filter(hogar=hogar).delete()
        sesion = SesionEncuesta.objects.create(
            hogar=hogar, instrumento=instrumento, encuestador=hogar.creado_por,
            direccion_territorial=dt, departamento_atencion=depto,
            municipio_atencion=muni, punto_atencion=punto,
        )

        miembro = hogar.miembros.first()
        if miembro is None:
            raise CommandError(
                f"El hogar {hogar.codigo_hogar} no tiene miembros: sin ellos no hay "
                f"respuestas de nivel PERSONA que escribir."
            )

        for spec in PREGUNTAS_DEMO:
            pregunta = self._pregunta(instrumento, spec)
            RespuestaEncuesta.objects.create(
                sesion=sesion, pregunta=pregunta,
                # nivel HOGAR ⇒ miembro NULL (así lo modela SICAV)
                miembro=miembro if spec["nivel"] == "PERSONA" else None,
                valor=spec["opcion"]["valor"],
            )

        self._verificar_cruce(sesion)
        self._verificar_respuestas(sesion)
        self.stdout.write(self.style.SUCCESS(
            f"Hogar demo listo: {hogar.codigo_hogar} — {hogar.miembros.count()} miembro(s), "
            f"{sesion.respuestas.count()} respuesta(s)."
        ))
        self.stdout.write(
            f"  territorio: {dt.nombre} / {depto.nombre} / {punto.nombre} / {muni.nombre}\n"
            f"  siguiente:  python manage.py escribir_a_oracle --hogar {hogar.codigo_hogar}"
        )

    # ── piezas ───────────────────────────────────────────────────────────────
    def _hogar(self, codigo):
        try:
            return Hogar.objects.get(codigo_hogar=codigo)
        except Hogar.DoesNotExist:
            raise CommandError(
                f"No existe el hogar {codigo!r}. Carga primero el fixture:\n"
                f"    python manage.py loaddata dump/hogares_demo_10.json"
            )

    def _asegurar_creador(self, hogar):
        """
        Garantiza que el hogar tenga `creado_por` con `codigo_usuario`.

        No es cosmético: `USUA_CREACION` sale de ahí y en el fixture viene `null`, lo
        que produciría cadena vacía. En Oracle **'' ES NULL**, y
        GIC_HOGAR.USU_USUARIOCREACION es NOT NULL ⇒ el INSERT fallaría… y
        GIC_INSERT_HOGAR1 se traga el error con su WHEN OTHERS: no escribiría nada y
        tampoco avisaría. Justo la trampa que el Escalón 1 debe evitar.
        """
        if hogar.creado_por is not None:
            return
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            codigo_usuario="228206",
            defaults={"nombre_completo": "Encuestador Demo Oracle",
                      "email": "demo.oracle@sicav.local", "activo": True},
        )
        hogar.creado_por = user
        hogar.save(update_fields=["creado_por"])
        self.stdout.write(self.style.WARNING(
            f"  {hogar.codigo_hogar} venía sin creado_por (el fixture lo deja null) → "
            f"asignado {user.codigo_usuario}; sin él USUA_CREACION iría vacío y Oracle "
            f"lo trataría como NULL."
        ))

    def _territorio(self):
        try:
            dt = DireccionTerritorial.objects.get(nombre=TERRITORIO_DEMO["dt"])
            depto = Departamento.objects.get(nombre__iexact=TERRITORIO_DEMO["departamento"])
            muni = Municipio.objects.get(codigo_dane=TERRITORIO_DEMO["municipio_dane"])
        except (DireccionTerritorial.DoesNotExist, Departamento.DoesNotExist,
                Municipio.DoesNotExist) as exc:
            raise CommandError(
                f"Falta una paramétrica territorial ({exc}). Carga primero:\n"
                f"    python manage.py cargar_departamentos_municipios --csv=data/municipios_dane.csv\n"
                f"    python manage.py cargar_direcciones_territoriales"
            )
        punto, _ = PuntoAtencion.objects.update_or_create(
            codigo=TERRITORIO_DEMO["punto_codigo"],
            defaults={"nombre": TERRITORIO_DEMO["punto_nombre"], "direccion_territorial": dt,
                      "municipio": muni, "direccion_fisica": "", "activo": True},
        )
        return dt, depto, muni, punto

    def _instrumento(self):
        instrumento = Instrumento.objects.filter(activo=True).first() or Instrumento.objects.first()
        if instrumento is None:
            raise CommandError(
                "No hay ningún Instrumento cargado. Corre primero `cargar_perfil`/"
                "`cargar_diccionario` para tener al menos uno."
            )
        return instrumento

    def _pregunta(self, instrumento, spec):
        codigo, nombre, nivel, orden = spec["capitulo"]
        capitulo, _ = Capitulo.objects.update_or_create(
            instrumento=instrumento, codigo=codigo,
            defaults={"nombre": nombre, "nivel": nivel, "orden": orden},
        )
        pregunta, _ = Pregunta.objects.update_or_create(
            capitulo=capitulo, codigo_externo=spec["codigo_externo"],
            defaults={"variable_bd": spec["codigo_externo"], "texto": spec["texto"],
                      "tipo": "RADIO", "nivel": spec["nivel"], "orden": 1,
                      # El puente hacia GIC_N_PREGUNTAS.PRE_IDPREGUNTA.
                      "id_preg": spec["id_preg"]},
        )
        opcion = spec["opcion"]
        OpcionRespuesta.objects.update_or_create(
            pregunta=pregunta, valor=opcion["valor"],
            defaults={"etiqueta": opcion["etiqueta"],
                      "id_resp_vivanto": opcion["id_resp_vivanto"], "orden": 1},
        )
        return pregunta

    def _verificar_cruce(self, sesion):
        """
        Comprueba que el territorio sembrado resuelve a los ids REALES de Oracle.

        Es la razón de ser del escenario: si esto no cruza, el Escalón 1 no prueba
        nada. Mejor enterarse aquí que con el hogar ya a medio escribir.
        """
        from apps.sincronizacion.oracle.mapeo import MapeoDesconocido, ResolverCatalogos
        try:
            ids = ResolverCatalogos(estricto=True).resolver_territorio(sesion)
        except MapeoDesconocido as exc:
            raise CommandError(f"El territorio sembrado NO cruza a Oracle: {exc}")
        if ids != IDS_ORACLE_ESPERADOS:
            raise CommandError(
                f"El territorio cruza pero a ids inesperados: {ids} != "
                f"{IDS_ORACLE_ESPERADOS}. ¿Cambió catalogos_oracle.json?"
            )
        self.stdout.write(f"  territorio → ids Oracle verificados: {ids}")

    def _verificar_respuestas(self, sesion):
        """
        Comprueba que las respuestas sembradas cruzan al RES_IDRESPUESTA esperado.

        Mismo criterio que el territorio: si el escenario deja de cruzar, mejor saberlo
        aquí. Se resuelve en modo NO estricto porque hoy la escribibilidad no está
        verificada (faltan las 153 huérfanas de la Query C2), así que lo que se afirma
        es el CRUCE, no que ya se pueda escribir.
        """
        from apps.sincronizacion.oracle.mapeo import ResolverCatalogos
        resolver = ResolverCatalogos(estricto=False)
        esperados = {s["codigo_externo"]: s["res_idrespuesta_esperado"] for s in PREGUNTAS_DEMO}
        for respuesta in sesion.respuestas.select_related("pregunta"):
            codigo = respuesta.pregunta.codigo_externo
            resuelto = resolver.resolver_res_idrespuesta(respuesta)
            esperado = esperados[codigo]
            if str(esperado) not in str(resuelto):
                raise CommandError(
                    f"La respuesta de {codigo} no cruza al RES_IDRESPUESTA esperado "
                    f"({esperado}): resolvió {resuelto!r}. ¿Cambió respuestas_oracle.json "
                    f"o la etiqueta de la opción?"
                )
            self.stdout.write(f"  respuesta {codigo:<10} → RES_IDRESPUESTA={esperado} ({resuelto})")
