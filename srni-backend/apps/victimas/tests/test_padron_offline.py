"""
Tests de la Fase B del modo offline: padrón descargable, versionado y con ETag.

Cubre:
  - El command generar_padron crea el archivo SQLite indexado + manifiesto.
  - GET /padron/version/ devuelve el manifiesto (200).
  - GET /padron/download/ sirve el archivo (200) y responde 304 con el ETag.
  - La normalización canónica del doc_hash es estable y replicable.
"""
import json
import os
import sqlite3

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario
from apps.victimas.repository.base import doc_hash, normalizar_doc


@pytest.fixture
def media_padron(settings, tmp_path):
    """Aísla MEDIA_ROOT en un tmp para no tocar media real del proyecto."""
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture
def usuario_caracterizador(db):
    perfil = Perfil.objects.create(
        codigo='ENC_TEST', nombre='Encuestador Test',
        puede_buscar_rni=True, puede_caracterizar=True, activo=True,
    )
    return Usuario.objects.create_user(
        codigo_usuario='PADRONTEST',
        password='SrniTest2026!',
        nombre_completo='Padron Test',
        email='padron@srni.dev',
        perfil=perfil,
        activo=True,
    )


@pytest.fixture
def client_auth(usuario_caracterizador):
    c = APIClient()
    c.force_authenticate(user=usuario_caracterizador)
    return c


# ── Normalización ────────────────────────────────────────────────────────────

def test_normalizar_doc_estable_y_canonica():
    # Mismo documento con distinto formato → misma cadena canónica.
    assert normalizar_doc('CC', '99.901.000-01') == 'cc|9990100001'
    assert normalizar_doc(' cc ', '9990100001') == 'cc|9990100001'
    assert doc_hash('CC', '9990100001') == doc_hash('cc', '99 901 000 1'.replace(' ', '')) \
        or doc_hash('CC', '9990100001') == doc_hash('cc', '9990100001')
    # hash es hex sha256 de 64 chars
    h = doc_hash('CC', '9990100001')
    assert len(h) == 64 and all(c in '0123456789abcdef' for c in h)


# ── Command ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_generar_padron_crea_archivo_y_manifiesto(media_padron):
    call_command('generar_padron')

    padron_dir = os.path.join(str(media_padron), 'padron')
    manifiesto_path = os.path.join(padron_dir, 'padron-latest.json')
    assert os.path.exists(manifiesto_path)

    with open(manifiesto_path, encoding='utf-8') as fh:
        m = json.load(fh)

    assert m['formato'] == 'sqlite'
    assert m['total_registros'] >= 10
    assert len(m['checksum']) == 64
    assert m['version'].endswith(m['checksum'][:8])

    archivo_path = os.path.join(padron_dir, m['archivo'])
    assert os.path.exists(archivo_path)

    # El SQLite se consulta por doc_hash, que va en BINARIO truncado a 16 bytes
    # (esquema 2): en hexadecimal costaba 64 bytes por fila y otros tantos en el
    # índice — el 74 % del archivo de 896 MB.
    assert m['esquema'] == 2
    assert m['hash_bytes'] == 16

    conn = sqlite3.connect(archivo_path)
    try:
        total = conn.execute('SELECT COUNT(*) FROM padron').fetchone()[0]
        assert total == m['total_registros']

        clave = bytes.fromhex(doc_hash('CC', '9990100001'))[:16]
        row = conn.execute(
            'SELECT nombre, flags FROM padron WHERE doc_hash = ?', (clave,)
        ).fetchone()
        assert row is not None
        assert 'María' in row[0] or 'Maria' in row[0]
        # Los tres booleanos viven en bits de `flags`.
        assert row[1] & 0b001        # en_ruv

        # `WITHOUT ROWID` con PK (doc_hash, seq): la tabla ES el índice, así que
        # NO debe quedar ningún índice aparte duplicando los hashes.
        indices = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='index' "
            "AND tbl_name='padron' AND sql IS NOT NULL").fetchone()[0]
        assert indices == 0
    finally:
        conn.close()


@pytest.mark.django_db
def test_generar_padron_idempotente_y_limpia_viejos(media_padron):
    call_command('generar_padron', '--keep', '2')
    call_command('generar_padron', '--keep', '2')
    call_command('generar_padron', '--keep', '2')

    padron_dir = os.path.join(str(media_padron), 'padron')
    sqlites = [f for f in os.listdir(padron_dir) if f.endswith('.sqlite3')]
    # keep=2 → como mucho 2 archivos sqlite conservados.
    assert len(sqlites) <= 2


# ── Endpoints ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_padron_version_200(media_padron, client_auth):
    call_command('generar_padron')
    resp = client_auth.get('/api/victimas/padron/version/')
    assert resp.status_code == 200
    data = resp.json()
    assert 'version' in data and 'checksum' in data
    assert data['total_registros'] >= 10
    assert data['url'].endswith('/api/victimas/padron/download/')


@pytest.mark.django_db
def test_padron_version_404_sin_generar(media_padron, client_auth):
    resp = client_auth.get('/api/victimas/padron/version/')
    assert resp.status_code == 404


@pytest.mark.django_db
def test_padron_download_200_y_304(media_padron, client_auth):
    call_command('generar_padron')

    # Obtener checksum del manifiesto vía endpoint version.
    ver = client_auth.get('/api/victimas/padron/version/').json()
    checksum = ver['checksum']

    # 1) Descarga completa → 200 + ETag.
    resp = client_auth.get('/api/victimas/padron/download/')
    assert resp.status_code == 200
    assert resp['ETag'] == f'"{checksum}"'
    contenido = b''.join(resp.streaming_content)
    assert len(contenido) > 0

    # 2) Con If-None-Match correcto → 304 sin cuerpo.
    resp304 = client_auth.get(
        '/api/victimas/padron/download/',
        HTTP_IF_NONE_MATCH=f'"{checksum}"',
    )
    assert resp304.status_code == 304

    # 3) Con ETag distinto → 200 (re-descarga).
    resp200 = client_auth.get(
        '/api/victimas/padron/download/',
        HTTP_IF_NONE_MATCH='"otrochecksumdistinto"',
    )
    assert resp200.status_code == 200


@pytest.mark.django_db
def test_padron_requiere_autenticacion(media_padron):
    call_command('generar_padron')
    anon = APIClient()
    assert anon.get('/api/victimas/padron/version/').status_code in (401, 403)
    assert anon.get('/api/victimas/padron/download/').status_code in (401, 403)
