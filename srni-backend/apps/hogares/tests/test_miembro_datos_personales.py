"""
El listado de miembros entrega nombre y documento **utilizables**.

Nace de un defecto reportado en campo el 11-sep-2026: al conformar un hogar, el
autorizado salía completo y **los demás integrantes llegaban con el primer
nombre y nada más** —sin segundo nombre, sin apellidos y sin cédula—.

La causa estaba repartida: el servidor entregaba el nombre solo como una cadena
concatenada y el documento no lo entregaba en absoluto, así que la aplicación
partía la cadena y se quedaba con el primer pedazo.

Lo que se fija acá es el contrato: los cuatro campos del nombre y el documento
salen **separados**, y para TODOS los integrantes, no solo para el autorizado.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.hogares.models import Hogar, MiembroHogar
from apps.hogares.serializers import MiembroHogarListSerializer
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()


class MiembroDatosPersonalesTests(TestCase):
    def setUp(self):
        self.tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
        self.user = Usuario.objects.create(
            codigo_usuario="QAMIEMBROS", email="qa@uariv.test",
            nombre_completo="QA Miembros")
        self.autorizado = Victima.objects.create(
            tipo_documento=self.tipo, numero_documento="1000000001",
            primer_nombre="ANA", segundo_nombre="LUCIA",
            primer_apellido="TORRES", segundo_apellido="MORA",
            fecha_nacimiento="1985-05-05", genero="F")
        self.hogar = Hogar.objects.create(
            autorizado=self.autorizado, creado_por=self.user, numero_personas=2)

    def _serializar(self, miembro):
        return MiembroHogarListSerializer(miembro).data

    # ── el integrante vinculado al padrón ──────────────────────────────────
    def test_miembro_con_victima_entrega_las_cuatro_partes_y_el_documento(self):
        """
        Es el caso que fallaba: un integrante que NO es el autorizado.

        Sus datos personales viven en la víctima vinculada, no en el propio
        miembro, y hasta el arreglo el serializer no los miraba.
        """
        otra = Victima.objects.create(
            tipo_documento=self.tipo, numero_documento="1000000002",
            primer_nombre="JOSE", segundo_nombre="LUIS",
            primer_apellido="VARGAS", segundo_apellido="MORA",
            fecha_nacimiento="2010-01-01", genero="M")
        miembro = MiembroHogar.objects.create(
            hogar=self.hogar, victima=otra, parentesco="HIJO",
            genero="M", es_autorizado=False, rol="MIEMBRO")

        d = self._serializar(miembro)
        self.assertEqual(d["primer_nombre"], "JOSE")
        self.assertEqual(d["segundo_nombre"], "LUIS")
        self.assertEqual(d["primer_apellido"], "VARGAS")
        self.assertEqual(d["segundo_apellido"], "MORA")
        self.assertEqual(d["numero_documento"], "1000000002")
        self.assertEqual(d["tipo_documento_codigo"], "CC")

    def test_el_autorizado_sigue_completo(self):
        """El que ya funcionaba tiene que seguir funcionando."""
        miembro = MiembroHogar.objects.create(
            hogar=self.hogar, victima=self.autorizado, parentesco="",
            genero="F", es_autorizado=True, rol="MIEMBRO")

        d = self._serializar(miembro)
        self.assertEqual(d["primer_nombre"], "ANA")
        self.assertEqual(d["segundo_apellido"], "MORA")
        self.assertEqual(d["numero_documento"], "1000000001")

    # ── el integrante que no está en el padrón (alta manual en campo) ──────
    def test_miembro_sin_victima_reparte_el_nombre_con_la_convencion_espanola(self):
        """
        Acá sí hay que repartir la cadena: es lo único que hay.

        Cuatro tokens ⇒ dos nombres y dos apellidos. Es la convención del país y
        acierta en el caso corriente; el caso ambiguo no se puede resolver sin
        preguntar, y por eso este camino es el respaldo y no el principal.
        """
        miembro = MiembroHogar.objects.create(
            hogar=self.hogar, nombre_completo="MARIA FERNANDA GOMEZ SUAREZ",
            numero_documento="5000000001", tipo_documento=self.tipo,
            parentesco="MADRE", genero="F", es_autorizado=False, rol="MIEMBRO")

        d = self._serializar(miembro)
        self.assertEqual(d["primer_nombre"], "MARIA")
        self.assertEqual(d["segundo_nombre"], "FERNANDA")
        self.assertEqual(d["primer_apellido"], "GOMEZ")
        self.assertEqual(d["segundo_apellido"], "SUAREZ")
        self.assertEqual(d["numero_documento"], "5000000001")

    def test_tres_tokens_son_un_nombre_y_dos_apellidos(self):
        miembro = MiembroHogar.objects.create(
            hogar=self.hogar, nombre_completo="PEDRO GOMEZ SUAREZ",
            parentesco="HIJO", genero="M", es_autorizado=False, rol="MIEMBRO")

        d = self._serializar(miembro)
        self.assertEqual(d["primer_nombre"], "PEDRO")
        self.assertEqual(d["segundo_nombre"], "")
        self.assertEqual(d["primer_apellido"], "GOMEZ")
        self.assertEqual(d["segundo_apellido"], "SUAREZ")

    def test_nombre_vacio_no_revienta(self):
        """Un integrante recién creado puede no tener nada todavía."""
        miembro = MiembroHogar.objects.create(
            hogar=self.hogar, parentesco="OTRO", genero="ND",
            es_autorizado=False, rol="MIEMBRO")

        d = self._serializar(miembro)
        self.assertEqual(d["primer_nombre"], "")
        self.assertEqual(d["numero_documento"], "")
        self.assertEqual(d["tipo_documento_codigo"], "")

    # ── precedencia ────────────────────────────────────────────────────────
    def test_el_documento_propio_del_miembro_le_gana_al_del_padron(self):
        """
        Cuando el encuestador corrige la cédula en campo, la escribe en el
        miembro. El del padrón es justamente el que se está corrigiendo, así que
        no puede ganarle.
        """
        otra = Victima.objects.create(
            tipo_documento=self.tipo, numero_documento="1000000003",
            primer_nombre="LUZ", primer_apellido="RIOS",
            fecha_nacimiento="1990-02-02", genero="F")
        miembro = MiembroHogar.objects.create(
            hogar=self.hogar, victima=otra, numero_documento="9999999999",
            parentesco="HERMANO", genero="F", es_autorizado=False, rol="MIEMBRO")

        d = self._serializar(miembro)
        self.assertEqual(d["numero_documento"], "9999999999")
        # El nombre sí sale del padrón: no se estaba corrigiendo.
        self.assertEqual(d["primer_nombre"], "LUZ")
