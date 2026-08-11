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
    assert m['esquema'] == 3
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


# ── Filtro de Bloom del universo (esquema 3) ─────────────────────────────────
#
# El padrón lleva a quien tiene ficha. El universo son 12,68 M de personas, y las
# 8,12 M que solo están ahí no cabían: con nombre y datos costaban ~190 MB. El
# filtro responde "¿está en el universo?" en 21,7 MiB, que es lo único que hace
# falta para habilitar un alta manual en campo — el nombre se lo pregunta el
# encuestador a la persona, que está enfrente.

def _sembrar_universo(documento, cons):
    """Una fila del universo, con el hash SIN tipo que es el que usa el filtro."""
    import datetime

    from apps.victimas.models import PersonaUniverso
    from apps.victimas.repository.base import num_hash

    return PersonaUniverso.objects.create(
        cons_persona_universo=cons,
        corte='TEMP_UNIV_VICT_PER_MI010726ALL',
        fecha_corte=datetime.date(2026, 7, 1),
        numero_documento=documento, tipo_documento='CC',
        numero_documento_hash_sin_tipo=num_hash(documento),
        primer_nombre='ROSA', primer_apellido='MOSQUERA',
        genero='Mujer', num_hechos=4,
    )


@pytest.mark.django_db
def test_bloom_reconoce_a_quien_solo_esta_en_el_universo(media_padron):
    """
    Los casos reales del 11-ago: cédulas que están en el RUV y no en el padrón.

    Sin filtro, en campo y sin señal responden "no encontrada" — falso, y deja a
    una víctima reconocida sin poder caracterizarse.
    """
    from apps.victimas.bloom import contiene
    from apps.victimas.repository.base import num_hash

    solo_universo = ['28683981', '93021801', '1075263069']
    for i, doc in enumerate(solo_universo):
        _sembrar_universo(doc, 17309123 + i)

    call_command('generar_padron')

    padron_dir = os.path.join(str(media_padron), 'padron')
    with open(os.path.join(padron_dir, 'padron-latest.json'), encoding='utf-8') as fh:
        m = json.load(fh)

    assert m['esquema'] == 3
    assert m['bloom'] is not None, 'el archivo salió sin filtro del universo'
    assert m['bloom']['n'] == len(solo_universo)
    assert m['bloom']['formato'] == 1

    conn = sqlite3.connect(os.path.join(padron_dir, m['archivo']))
    try:
        formato, mm, kk, n, p, bits = conn.execute(
            'SELECT formato, m, k, n, p, bits FROM universo_bloom').fetchone()

        assert mm == m['bloom']['m'] and kk == m['bloom']['k']
        assert len(bits) == mm // 8, 'el blob no tiene el tamaño que declara m'

        # Lo que hará la APK: hash SIN tipo → consulta al filtro.
        for doc in solo_universo:
            assert contiene(bits, mm, kk, num_hash(doc)), \
                f'{doc} está en el universo y el filtro no lo reconoce'
    finally:
        conn.close()


@pytest.mark.django_db
def test_bloom_se_consulta_sin_el_tipo_de_documento(media_padron):
    """
    La trampa a evitar: la tabla `padron` usa doc_hash(tipo, numero) y el filtro
    usa num_hash(numero). Consultar el filtro con el hash de identidad no
    encuentra NADA, y el fallo es silencioso —responde "no está" y ya—.
    """
    from apps.victimas.bloom import contiene
    from apps.victimas.repository.base import num_hash

    _sembrar_universo('28683981', 17309123)
    call_command('generar_padron')

    padron_dir = os.path.join(str(media_padron), 'padron')
    with open(os.path.join(padron_dir, 'padron-latest.json'), encoding='utf-8') as fh:
        m = json.load(fh)

    conn = sqlite3.connect(os.path.join(padron_dir, m['archivo']))
    try:
        mm, kk, bits = conn.execute(
            'SELECT m, k, bits FROM universo_bloom').fetchone()

        assert contiene(bits, mm, kk, num_hash('28683981'))
        assert not contiene(bits, mm, kk, doc_hash('CC', '28683981'))
    finally:
        conn.close()


@pytest.mark.django_db
def test_bloom_se_descarga_suelto_sin_bajar_el_padron(media_padron, client_auth):
    """
    El endpoint que hace viable todo esto: 22,7 MB en vez de cientos.

    Si el filtro solo se pudiera sacar del padrón completo, el alta manual
    offline quedaría atada a una descarga enorme sobre una red institucional que
    se corta — y a un disco que está al 81 %.
    """
    from apps.victimas.bloom import contiene
    from apps.victimas.repository.base import num_hash

    _sembrar_universo('28683981', 17309123)
    call_command('generar_padron')

    padron_dir = os.path.join(str(media_padron), 'padron')
    with open(os.path.join(padron_dir, 'padron-latest.json'), encoding='utf-8') as fh:
        m = json.load(fh)

    resp = client_auth.get('/api/victimas/padron/bloom/')
    assert resp.status_code == 200

    bits = b''.join(resp.streaming_content)

    # El cuerpo es EXACTAMENTE el filtro, del tamaño que declara m.
    assert len(bits) == m['bloom']['m'] // 8
    assert resp['Content-Length'] == str(m['bloom']['m'] // 8)
    assert resp['X-Bloom-M'] == str(m['bloom']['m'])
    assert resp['X-Bloom-K'] == str(m['bloom']['k'])

    # Y sirve para lo que tiene que servir.
    assert contiene(bits, m['bloom']['m'], m['bloom']['k'], num_hash('28683981'))
    assert not contiene(bits, m['bloom']['m'], m['bloom']['k'], num_hash('99999999'))


@pytest.mark.django_db
def test_bloom_304_con_etag_propio(media_padron, client_auth):
    """
    El ETag lleva sufijo ':bloom' a propósito.

    Sin él, un cliente que ya tenga el padrón completo mandaría el mismo
    If-None-Match aquí, recibiría 304 y se quedaría sin filtro — con la APK
    convencida de que ya lo tiene.
    """
    _sembrar_universo('28683981', 17309123)
    call_command('generar_padron')

    resp = client_auth.get('/api/victimas/padron/bloom/')
    etag = resp['ETag']
    assert etag.endswith(':bloom"')

    r304 = client_auth.get('/api/victimas/padron/bloom/', HTTP_IF_NONE_MATCH=etag)
    assert r304.status_code == 304

    # El ETag del padrón NO sirve para el filtro.
    with open(os.path.join(str(media_padron), 'padron', 'padron-latest.json'),
              encoding='utf-8') as fh:
        checksum = json.load(fh)['checksum']
    r200 = client_auth.get('/api/victimas/padron/bloom/',
                           HTTP_IF_NONE_MATCH=f'"{checksum}"')
    assert r200.status_code == 200


@pytest.mark.django_db
def test_bloom_404_si_el_padron_no_lo_trae(media_padron, client_auth):
    """Sin universo cargado se dice explícitamente, no se devuelve un filtro vacío."""
    call_command('generar_padron')
    assert client_auth.get('/api/victimas/padron/bloom/').status_code == 404


@pytest.mark.django_db
def test_bloom_requiere_autenticacion(media_padron):
    _sembrar_universo('28683981', 17309123)
    call_command('generar_padron')
    assert APIClient().get('/api/victimas/padron/bloom/').status_code in (401, 403)


@pytest.mark.django_db
def test_la_precarga_publica_la_url_del_filtro(media_padron, client_auth):
    """La APK descubre el filtro por aquí; sin la URL no sabría que existe."""
    _sembrar_universo('28683981', 17309123)
    call_command('generar_padron')

    datos = client_auth.get('/api/victimas/precarga/').json()
    bloom = datos['padron_archivo']['bloom']

    assert bloom is not None
    assert bloom['url'].endswith('/api/victimas/padron/bloom/')
    assert bloom['m'] > 0 and bloom['k'] > 0
    assert datos['padron_archivo']['esquema'] == 3


@pytest.mark.django_db
def test_sin_universo_el_manifiesto_lo_declara(media_padron):
    """
    Sin universo cargado el archivo sigue siendo válido, pero `bloom: null` lo
    dice. Es información, no un hueco: la APK debe volver a responder "no
    encontrada" en vez de asumir que el universo está vacío.
    """
    call_command('generar_padron')

    padron_dir = os.path.join(str(media_padron), 'padron')
    with open(os.path.join(padron_dir, 'padron-latest.json'), encoding='utf-8') as fh:
        m = json.load(fh)

    assert m['bloom'] is None

    conn = sqlite3.connect(os.path.join(padron_dir, m['archivo']))
    try:
        # La tabla existe igual: un cliente que la consulte debe encontrarla
        # vacía, no fallar con "no such table".
        assert conn.execute('SELECT COUNT(*) FROM universo_bloom').fetchone()[0] == 0
    finally:
        conn.close()
