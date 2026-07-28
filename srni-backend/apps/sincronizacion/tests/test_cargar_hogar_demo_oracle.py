"""
Tests del andamio del Escalón 1 (`cargar_hogar_demo_oracle`).

El escenario existe para probar la ruta de escritura a Oracle, así que lo que hay que
proteger es que siga sirviendo para eso: que el territorio sembrado **cruce a los ids
reales** de GIC_N_DT_PUNTOS_ATENCION, que haya respuestas de los dos niveles, y que el
hogar quede con creador (o USUA_CREACION viajaría vacío = NULL para Oracle).
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.encuestas.models import SesionEncuesta
from apps.formulario.models import Instrumento
from apps.hogares.models import Hogar, MiembroHogar
from apps.parametricas.models import (
    Departamento, DireccionTerritorial, Municipio, TipoDocumento,
)
from apps.victimas.models import Victima

Usuario = get_user_model()


class CargarHogarDemoOracleTests(TestCase):
    def setUp(self):
        self.tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
        victima = Victima.objects.create(
            tipo_documento=self.tipo, numero_documento="9996000001",
            primer_nombre="Demo", primer_apellido="Titular",
            fecha_nacimiento="1985-01-01", genero="F",
        )
        # creado_por=None a propósito: así viene en dump/hogares_demo_10.json.
        self.hogar = Hogar.objects.create(
            codigo_hogar="LISTO-96001", autorizado=victima, estado="ACTIVO",
            creado_por=None,
        )
        MiembroHogar.objects.create(
            hogar=self.hogar, nombre_completo="DEMO TITULAR PRUEBA",
            tipo_documento=self.tipo, numero_documento="9996000001",
            parentesco="", es_autorizado=True, fecha_nacimiento=date(1985, 1, 1),
        )
        Instrumento.objects.create(
            codigo="TERRITORIAL", nombre="Territorial", version="V8",
            vigente_desde=date(2021, 10, 7),
        )
        # Paramétricas con los nombres REALES que el comando cruza contra Oracle.
        self.depto = Departamento.objects.create(codigo_dane="73", nombre="Tolima")
        Municipio.objects.create(
            codigo_dane="73026", nombre="ALVARADO", departamento=self.depto,
        )
        dt = DireccionTerritorial.objects.create(
            codigo="DT_CENTRAL", nombre="DIRECCION TERRITORIAL CENTRAL",
        )
        dt.departamentos.add(self.depto)

    def test_monta_el_escenario_completo(self):
        from apps.sincronizacion.management.commands.cargar_hogar_demo_oracle import (
            PREGUNTAS_DEMO,
        )
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        sesion = SesionEncuesta.objects.get(hogar=self.hogar)
        self.assertEqual(sesion.respuestas.count(), len(PREGUNTAS_DEMO))

    def test_siembra_la_respuesta_geografica_con_el_dane_sin_normalizar(self):
        """
        El escenario debe traer el DANE tal como lo manda el móvil ('05001', con el
        cero), no ya traducido: si se sembrara '5001' el demo pasaría aunque la
        traducción estuviera rota, y el Escalón 2 no probaría nada.
        """
        from apps.sincronizacion.oracle import mapeo
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        sesion = SesionEncuesta.objects.get(hogar=self.hogar)
        geo = sesion.respuestas.get(pregunta__id_preg=3)
        self.assertEqual(geo.valor, "05001")
        self.assertIsNone(geo.miembro_id)          # 'Lugar de Residencia' es de hogar
        resolver = mapeo.ResolverCatalogos(estricto=True)
        # y al escribir se traduce a lo que Oracle sabe resolver
        self.assertEqual(mapeo._texto_respuesta(geo, resolver), "5001")
        self.assertEqual(resolver.resolver_res_idrespuesta(geo), 6)

    def test_territorio_sembrado_cruza_a_los_ids_reales_de_oracle(self):
        # Es la razón de ser del escenario: si no cruza, el Escalón 1 no prueba nada.
        from apps.sincronizacion.oracle.mapeo import ResolverCatalogos
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        sesion = SesionEncuesta.objects.get(hogar=self.hogar)
        ids = ResolverCatalogos(estricto=True).resolver_territorio(sesion)
        self.assertEqual(ids, {"id_dt": 7, "id_depto": 30, "id_pt": 13, "id_ma": 32})

    def test_siembra_los_dos_niveles_de_respuesta(self):
        # El paso RESPUESTA recorre dos caminos distintos según haya miembro o no.
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        sesion = SesionEncuesta.objects.get(hogar=self.hogar)
        niveles = {r.pregunta.nivel: r.miembro_id for r in sesion.respuestas.all()}
        self.assertEqual(set(niveles), {"PERSONA", "HOGAR"})
        self.assertIsNone(niveles["HOGAR"])        # nivel hogar ⇒ miembro NULL
        self.assertIsNotNone(niveles["PERSONA"])

    def test_asigna_creador_si_el_fixture_lo_dejo_nulo(self):
        # Sin creado_por, USUA_CREACION iría '' y para Oracle '' ES NULL: el INSERT
        # violaría el NOT NULL y GIC_INSERT_HOGAR1 se tragaría el error sin escribir.
        self.assertIsNone(self.hogar.creado_por)
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        self.hogar.refresh_from_db()
        self.assertIsNotNone(self.hogar.creado_por)
        self.assertTrue(self.hogar.creado_por.codigo_usuario)

    def test_usua_creacion_no_viaja_vacio(self):
        from apps.sincronizacion.oracle import mapeo
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        self.hogar.refresh_from_db()
        binds = mapeo.binds_hogar(
            self.hogar, user=self.hogar.creado_por,
            catalogos=mapeo.ResolverCatalogos(estricto=False),
        )
        self.assertNotEqual(binds["usua_creacion"], "")

    def test_es_idempotente(self):
        from apps.sincronizacion.management.commands.cargar_hogar_demo_oracle import (
            PREGUNTAS_DEMO,
        )
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        self.assertEqual(SesionEncuesta.objects.filter(hogar=self.hogar).count(), 1)
        sesion = SesionEncuesta.objects.get(hogar=self.hogar)
        self.assertEqual(sesion.respuestas.count(), len(PREGUNTAS_DEMO))

    def test_sin_hogar_da_error_accionable(self):
        Hogar.objects.all().delete()
        with self.assertRaises(CommandError) as exc:
            call_command("cargar_hogar_demo_oracle", verbosity=0)
        self.assertIn("loaddata", str(exc.exception))  # dice CÓMO arreglarlo

    def test_sin_parametricas_da_error_accionable(self):
        Municipio.objects.all().delete()
        with self.assertRaises(CommandError) as exc:
            call_command("cargar_hogar_demo_oracle", verbosity=0)
        self.assertIn("cargar_departamentos_municipios", str(exc.exception))

    def test_dry_run_completo_sobre_el_hogar_demo(self):
        # La corrida que el Escalón 1 revisa: todos los pasos, ninguno reventado.
        from apps.sincronizacion.oracle.escritor import EscritorOracle
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        self.hogar.refresh_from_db()
        resultado = EscritorOracle(confirmar=False).procesar_hogar(self.hogar)
        pasos = {p.paso for p in resultado.pasos}
        self.assertEqual(pasos, {"HOGAR", "PERSONA", "MIEMBRO", "TERRITORIO", "RESPUESTA"})
        self.assertTrue(resultado.dry_run)

    def test_el_territorio_del_dry_run_lleva_ids_reales_no_marcadores(self):
        from apps.sincronizacion.oracle.escritor import EscritorOracle
        call_command("cargar_hogar_demo_oracle", verbosity=0)
        self.hogar.refresh_from_db()
        resultado = EscritorOracle(confirmar=False).procesar_hogar(self.hogar)
        terr = next(p for p in resultado.pasos if p.paso == "TERRITORIO")
        self.assertEqual(terr.detalle["territorio_resuelto"],
                         {"id_dt": 7, "id_depto": 30, "id_pt": 13, "id_ma": 32})
