"""
Tests de paridad — Bloques 2 y 3 (GIC_INSERT_PERSONAS / GIC_INSERT_MIEMBRO_HOGAR).

Verifican:
- Nombres normalizados a UPPERCASE.
- Guard anti-duplicado: mismo documento en hogar ABIERTO creado <24h ⇒ rechazo.
- El guard NO aplica fuera de 24h ni a hogares no abiertos.
- No se duplica el vínculo (idempotente) para miembros RNI.
- El guard casa miembros RNI por hash de documento.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.hogares.models import Hogar, MiembroHogar
from apps.hogares.services import (
    agregar_miembro,
    crear_hogar,
    documento_ya_en_hogar_activo_reciente,
    MiembroDuplicadoError,
    ESTADO_ABIERTO,
)
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()

_seq = {"n": 0}


def _doc():
    _seq["n"] += 1
    return f"200000{_seq['n']:03d}"


class AltaMiembroTests(TestCase):
    def setUp(self):
        self.tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
        self.user = Usuario.objects.create(
            codigo_usuario="228206", email="e@uariv.test", nombre_completo="Enc"
        )
        self.victima_aut = self._victima()
        self.hogar = crear_hogar(user=self.user, autorizado=self.victima_aut).hogar

    def _victima(self, numero=None):
        return Victima.objects.create(
            tipo_documento=self.tipo,
            numero_documento=numero or _doc(),
            primer_nombre="LUZ",
            primer_apellido="RIOS",
            fecha_nacimiento="1985-05-05",
            genero="F",
        )

    # ---- Bloque 2: UPPERCASE ------------------------------------------------
    def test_nombre_se_guarda_en_mayusculas(self):
        m = agregar_miembro(
            hogar=self.hogar, user=self.user,
            nombre_completo="juan de la cruz", numero_documento="30111",
            tipo_documento=self.tipo,
        )
        recargado = MiembroHogar.objects.get(pk=m.pk)
        self.assertEqual(recargado.nombre_completo, "JUAN DE LA CRUZ")
        self.assertEqual(recargado.numero_documento, "30111")

    # ---- Bloque 2: guard anti-duplicado 24h ---------------------------------
    def test_guard_rechaza_documento_duplicado_en_hogar_abierto_reciente(self):
        agregar_miembro(
            hogar=self.hogar, user=self.user,
            numero_documento="55555", tipo_documento=self.tipo,
        )
        self.assertTrue(documento_ya_en_hogar_activo_reciente("55555"))

        # Otro hogar del mismo tipo intenta el mismo documento → rechazo.
        otro_hogar = Hogar.objects.create(
            codigo_hogar="228206-ZZZZZ", autorizado=self._victima(),
            estado=ESTADO_ABIERTO, creado_por=self.user,
        )
        with self.assertRaises(MiembroDuplicadoError):
            agregar_miembro(
                hogar=otro_hogar, user=self.user,
                numero_documento="55555", tipo_documento=self.tipo,
            )

    def test_guard_no_aplica_fuera_de_24h(self):
        agregar_miembro(
            hogar=self.hogar, user=self.user,
            numero_documento="77777", tipo_documento=self.tipo,
        )
        # Envejecer el hogar más de 24h.
        Hogar.objects.filter(pk=self.hogar.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        self.assertFalse(documento_ya_en_hogar_activo_reciente("77777"))

    def test_guard_no_aplica_a_hogar_no_abierto(self):
        agregar_miembro(
            hogar=self.hogar, user=self.user,
            numero_documento="88888", tipo_documento=self.tipo,
        )
        Hogar.objects.filter(pk=self.hogar.pk).update(estado="ARCHIVADO")
        self.assertFalse(documento_ya_en_hogar_activo_reciente("88888"))

    # ---- Bloque 3: no duplicar vínculo --------------------------------------
    def test_vinculo_rni_no_se_duplica(self):
        v = self._victima("30222")
        m1 = agregar_miembro(hogar=self.hogar, user=self.user, victima=v)
        m2 = agregar_miembro(hogar=self.hogar, user=self.user, victima=v)
        self.assertEqual(m1.pk, m2.pk)
        self.assertEqual(
            MiembroHogar.objects.filter(hogar=self.hogar, victima=v).count(), 1
        )

    def test_guard_casa_miembro_rni_por_hash(self):
        v = self._victima("30333")
        agregar_miembro(hogar=self.hogar, user=self.user, victima=v)
        # El mismo número, ahora como NO-RNI, debe detectarse como duplicado.
        self.assertTrue(documento_ya_en_hogar_activo_reciente("30333"))
