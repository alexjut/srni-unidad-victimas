"""
Tests de paridad — Bloque 1 (GIC_INSERT_HOGAR1).

Verifican que el servicio Django reproduce:
- Formato de HOG_CODIGO = {id_usuario}-{alfanumérico} + unicidad con reintento.
- Regla "1 hogar abierto por usuario" (no crea otro; devuelve el existente).
"""
import re
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.hogares.models import Hogar
from apps.hogares.services import (
    crear_hogar,
    generar_codigo_hogar,
    hogar_abierto_del_usuario,
    ESTADO_ABIERTO,
)
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima

Usuario = get_user_model()

_seq = {"n": 0}


def _doc():
    _seq["n"] += 1
    return f"100000{_seq['n']:03d}"


def crear_usuario(codigo="228206"):
    return Usuario.objects.create(
        codigo_usuario=codigo, email=f"{codigo}@uariv.test", nombre_completo="Encuestador"
    )


def crear_victima(tipo):
    return Victima.objects.create(
        tipo_documento=tipo,
        numero_documento=_doc(),
        primer_nombre="ANA",
        primer_apellido="GOMEZ",
        fecha_nacimiento="1990-01-01",
        genero="F",
    )


class AltaHogarTests(TestCase):
    def setUp(self):
        self.tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
        self.user = crear_usuario()

    def test_codigo_tiene_formato_codigo_usuario_guion_alfanumerico(self):
        # Prefijo = codigo_usuario (análogo del ID_USUARIO numérico de Oracle),
        # no el PK UUID del Usuario Django.
        codigo = generar_codigo_hogar(self.user)
        self.assertRegex(codigo, r"^.+-[A-Z2-9]{5}$")
        self.assertTrue(codigo.startswith(f"{self.user.codigo_usuario}-"))

    def test_codigo_reintenta_ante_colision(self):
        # Pre-existe un hogar con el primer código candidato → debe regenerar.
        v = crear_victima(self.tipo)
        Hogar.objects.create(
            codigo_hogar=f"{self.user.codigo_usuario}-AAAAA", autorizado=v,
            estado=ESTADO_ABIERTO, creado_por=self.user,
        )
        with mock.patch(
            "apps.hogares.services.codigo_hogar._codigo_aleatorio",
            side_effect=["AAAAA", "BBBBB"],
        ):
            codigo = generar_codigo_hogar(self.user)
        self.assertEqual(codigo, f"{self.user.codigo_usuario}-BBBBB")

    def test_crea_hogar_nuevo_abierto(self):
        v = crear_victima(self.tipo)
        res = crear_hogar(user=self.user, autorizado=v)
        self.assertTrue(res.creado)
        self.assertEqual(res.hogar.estado, ESTADO_ABIERTO)
        self.assertEqual(res.hogar.creado_por_id, self.user.pk)
        self.assertTrue(res.hogar.codigo_hogar)

    def test_no_crea_segundo_hogar_abierto_del_mismo_usuario(self):
        # Regla ACTIVA-única: aunque el autorizado sea otro, el usuario ya tiene
        # un hogar abierto ⇒ se devuelve el existente sin crear otro.
        v1 = crear_victima(self.tipo)
        v2 = crear_victima(self.tipo)
        primero = crear_hogar(user=self.user, autorizado=v1)
        segundo = crear_hogar(user=self.user, autorizado=v2)

        self.assertTrue(primero.creado)
        self.assertFalse(segundo.creado)
        self.assertEqual(segundo.hogar.pk, primero.hogar.pk)
        self.assertEqual(Hogar.objects.filter(creado_por=self.user).count(), 1)

    def test_otro_usuario_si_puede_crear(self):
        v1 = crear_victima(self.tipo)
        v2 = crear_victima(self.tipo)
        otro = crear_usuario(codigo="164689")
        crear_hogar(user=self.user, autorizado=v1)
        res = crear_hogar(user=otro, autorizado=v2)
        self.assertTrue(res.creado)

    def test_hogar_abierto_del_usuario_devuelve_none_sin_hogar(self):
        self.assertIsNone(hogar_abierto_del_usuario(self.user))
