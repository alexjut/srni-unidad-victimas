"""
Tests de la subida de constancia de tutor/cuidador.

Cubre la acción POST /api/hogares/{id}/subir-constancia/:
  - Sube y persiste el archivo + metadata para un miembro TUTOR.
  - Rechaza (400) si el miembro no es TUTOR/CUIDADOR_PERMANENTE.
  - Rechaza (404) si el miembro no pertenece al hogar.
"""
import datetime as dt

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario
from apps.hogares.models import Hogar, MiembroHogar
from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima


@pytest.fixture
def media_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture
def caracterizador(db):
    perfil = Perfil.objects.create(
        codigo='ENC_CONST', nombre='Enc Constancia',
        puede_buscar_rni=True, puede_caracterizar=True, activo=True,
    )
    return Usuario.objects.create_user(
        codigo_usuario='CONSTTEST', password='SrniTest2026!',
        nombre_completo='Const Test', email='const@srni.dev',
        perfil=perfil, activo=True,
    )


@pytest.fixture
def hogar_con_tutor(db, caracterizador):
    td = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    victima = Victima.objects.create(
        cons_persona=1, tipo_documento=td,
        numero_documento='123456', numero_documento_hash='h' * 8,
        primer_nombre='Ana', primer_apellido='Ruiz',
        fecha_nacimiento='1985-01-01', genero='F',
    )
    hogar = Hogar.objects.create(autorizado=victima, creado_por=caracterizador)
    tutor = MiembroHogar.objects.create(
        hogar=hogar, rol='TUTOR', creado_por=caracterizador,
    )
    miembro = MiembroHogar.objects.create(
        hogar=hogar, rol='MIEMBRO', creado_por=caracterizador,
    )
    return hogar, tutor, miembro


@pytest.fixture
def client_auth(caracterizador):
    c = APIClient()
    c.force_authenticate(user=caracterizador)
    return c


def _url(hogar):
    return f'/api/hogares/{hogar.id}/subir-constancia/'


def test_sube_constancia_tutor_ok(media_tmp, client_auth, hogar_con_tutor):
    hogar, tutor, _ = hogar_con_tutor
    archivo = SimpleUploadedFile('constancia.pdf', b'%PDF-1.4 contenido', content_type='application/pdf')
    resp = client_auth.post(_url(hogar), {'miembro_id': str(tutor.id), 'archivo': archivo}, format='multipart')

    assert resp.status_code == 200, resp.content
    tutor.refresh_from_db()
    assert tutor.constancia.name.endswith('.pdf')
    assert tutor.constancia_nombre == 'constancia.pdf'
    assert isinstance(tutor.constancia_subida_en, dt.datetime)


def test_rechaza_miembro_no_tutor(media_tmp, client_auth, hogar_con_tutor):
    hogar, _, miembro = hogar_con_tutor
    archivo = SimpleUploadedFile('x.pdf', b'data', content_type='application/pdf')
    resp = client_auth.post(_url(hogar), {'miembro_id': str(miembro.id), 'archivo': archivo}, format='multipart')

    assert resp.status_code == 400
    miembro.refresh_from_db()
    assert not miembro.constancia


def test_rechaza_miembro_de_otro_hogar(media_tmp, client_auth, hogar_con_tutor, caracterizador):
    hogar, _, _ = hogar_con_tutor
    otro_td = TipoDocumento.objects.create(codigo='TI', nombre='Tarjeta')
    otra_victima = Victima.objects.create(
        cons_persona=2, tipo_documento=otro_td,
        numero_documento='999', numero_documento_hash='g' * 8,
        primer_nombre='Leo', primer_apellido='Paz',
        fecha_nacimiento='1990-01-01', genero='M',
    )
    otro_hogar = Hogar.objects.create(autorizado=otra_victima, creado_por=caracterizador)
    ajeno = MiembroHogar.objects.create(hogar=otro_hogar, rol='TUTOR', creado_por=caracterizador)

    archivo = SimpleUploadedFile('x.pdf', b'data', content_type='application/pdf')
    resp = client_auth.post(_url(hogar), {'miembro_id': str(ajeno.id), 'archivo': archivo}, format='multipart')
    assert resp.status_code == 404
