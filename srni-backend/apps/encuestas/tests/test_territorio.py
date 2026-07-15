"""
Tests de paridad — Bloque 4 (cascada territorial GIC_SP_OB* / GIC_N_RELACION_DT_PUNTO).

Verifican que la cascada se puebla en orden y valida coherencia jerárquica
(cada nivel debe pertenecer a su padre), replicando la fila única por hogar
(IDPERSONA='1') como campos de la SesionEncuesta.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.encuestas.models import SesionEncuesta
from apps.encuestas.services import set_cascada_territorial, CascadaTerritorialError
from apps.formulario.models import Instrumento
from apps.hogares.models import Hogar
from apps.parametricas.models import (
    Departamento, Municipio, DireccionTerritorial, PuntoAtencion, TipoDocumento,
)
from apps.victimas.models import Victima

Usuario = get_user_model()


class CascadaTerritorialTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create(
            codigo_usuario="228206", email="e@uariv.test", nombre_completo="Enc"
        )
        tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
        victima = Victima.objects.create(
            tipo_documento=tipo, numero_documento="900001",
            primer_nombre="A", primer_apellido="B",
            fecha_nacimiento="1990-01-01", genero="M",
        )
        self.hogar = Hogar.objects.create(
            codigo_hogar="228206-AAAAA", autorizado=victima,
            estado="BORRADOR", creado_por=self.user,
        )
        self.instrumento = Instrumento.objects.create(
            codigo="TERRITORIAL", nombre="Territorial", version="V8",
            vigente_desde=date(2021, 10, 7),
        )
        self.sesion = SesionEncuesta.objects.create(
            hogar=self.hogar, instrumento=self.instrumento, encuestador=self.user,
        )

        # Geografía coherente.
        self.depto = Departamento.objects.create(codigo_dane="05", nombre="Antioquia")
        self.depto_otro = Departamento.objects.create(codigo_dane="76", nombre="Valle")
        self.municipio = Municipio.objects.create(
            codigo_dane="05001", nombre="Medellín", departamento=self.depto
        )
        self.municipio_otro = Municipio.objects.create(
            codigo_dane="76001", nombre="Cali", departamento=self.depto_otro
        )
        self.dt = DireccionTerritorial.objects.create(codigo="DT-ANT", nombre="DT Antioquia")
        self.dt.departamentos.add(self.depto)
        self.punto = PuntoAtencion.objects.create(
            codigo="PA-MED", nombre="Punto Medellín",
            direccion_territorial=self.dt, municipio=self.municipio,
        )
        self.punto_otra_dt = PuntoAtencion.objects.create(
            codigo="PA-CAL", nombre="Punto Cali",
            direccion_territorial=DireccionTerritorial.objects.create(
                codigo="DT-VAL", nombre="DT Valle"),
            municipio=self.municipio_otro,
        )

    def test_cascada_completa_coherente(self):
        set_cascada_territorial(
            self.sesion, direccion_territorial=self.dt, departamento=self.depto,
            punto=self.punto, municipio=self.municipio,
        )
        s = SesionEncuesta.objects.get(pk=self.sesion.pk)
        self.assertEqual(s.direccion_territorial_id, self.dt.pk)
        self.assertEqual(s.departamento_atencion_id, self.depto.pk)
        self.assertEqual(s.punto_atencion_id, self.punto.pk)
        self.assertEqual(s.municipio_atencion_id, self.municipio.pk)

    def test_departamento_fuera_de_la_dt_falla(self):
        with self.assertRaises(CascadaTerritorialError):
            set_cascada_territorial(
                self.sesion, direccion_territorial=self.dt, departamento=self.depto_otro,
            )

    def test_municipio_fuera_del_departamento_falla(self):
        with self.assertRaises(CascadaTerritorialError):
            set_cascada_territorial(
                self.sesion, direccion_territorial=self.dt, departamento=self.depto,
                municipio=self.municipio_otro,
            )

    def test_punto_de_otra_dt_falla(self):
        with self.assertRaises(CascadaTerritorialError):
            set_cascada_territorial(
                self.sesion, direccion_territorial=self.dt, punto=self.punto_otra_dt,
            )

    def test_departamento_sin_dt_falla(self):
        with self.assertRaises(CascadaTerritorialError):
            set_cascada_territorial(self.sesion, departamento=self.depto)

    def test_incremental_dt_primero_luego_departamento(self):
        # Insert-once (DT) y luego update (departamento) sobre la misma sesión.
        set_cascada_territorial(self.sesion, direccion_territorial=self.dt)
        set_cascada_territorial(self.sesion, departamento=self.depto)
        s = SesionEncuesta.objects.get(pk=self.sesion.pk)
        self.assertEqual(s.direccion_territorial_id, self.dt.pk)
        self.assertEqual(s.departamento_atencion_id, self.depto.pk)
