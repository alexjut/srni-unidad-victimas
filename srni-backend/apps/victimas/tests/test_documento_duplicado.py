"""
Documentos repetidos: lo que pasa cuando dos víctimas comparten (tipo, número).

No es un caso de borde. En el padrón real cargado el 2-ago hay **768.096**
documentos repetidos sobre 4.928.725 distintos —~15,6 % de las búsquedas
posibles— y 1.765.375 personas involucradas. Salió en la primera prueba contra
producción: la búsqueda respondió **500**.

Lo que se protege acá:

1. `POST /api/victimas/buscar/` NO revienta: responde 409 con TODOS los
   candidatos. No elige uno por regla, porque pueden ser dos personas distintas y
   mostrar a una como si fuera la única es entregar datos de otra persona en
   silencio.
2. `POST /api/victimas/consultar-fuente/` **manda** los candidatos. Antes el
   mensaje decía "CONFIRME cuál corresponde" y el serializer se comía la lista:
   el aviso pedía confirmar sin dar con qué.
3. `generar_padron` declara en el manifiesto las filas que el archivo TIENE. La
   PK es `doc_hash`, así que los repetidos colapsan; el contador del bucle decía
   5.926.004 sobre un archivo de 4.928.725.
"""
import json
import os
import sqlite3

import pytest
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario
from apps.victimas.repository.base import doc_hash

pytestmark = pytest.mark.django_db


@pytest.fixture
def catalogo(db):
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula de Ciudadanía")
    depto = Departamento.objects.create(codigo_dane="05", nombre="Antioquia")
    muni = Municipio.objects.create(codigo_dane="05001", nombre="Medellín",
                                    departamento=depto)
    return {"tipo": tipo, "municipio": muni}


def _crear_victima(catalogo, *, documento, nombre, apellido, **extra):
    from apps.victimas.models import Victima

    campos = dict(
        tipo_documento=catalogo["tipo"],
        numero_documento=documento,
        numero_documento_hash=doc_hash("CC", documento),
        primer_nombre=nombre,
        primer_apellido=apellido,
        genero="F",
        estado_ruv="INCLUIDO",
        habilitado_para_caracterizacion=True,
        pertenencia_etnica="NINGUNA",
        discapacidad=False,
        municipio_residencia=catalogo["municipio"],
    )
    campos.update(extra)
    return Victima.objects.create(**campos)


@pytest.fixture
def client_auth(db):
    perfil = Perfil.objects.create(
        codigo="ENC_DUP", nombre="Encuestador Dup",
        puede_buscar_rni=True, puede_caracterizar=True, activo=True,
    )
    usuario = Usuario.objects.create_user(
        codigo_usuario="DUPTEST",
        password="SrniTest2026!",
        nombre_completo="Dup Test",
        email="dup@srni.dev",
        perfil=perfil,
        activo=True,
    )
    c = APIClient()
    c.force_authenticate(user=usuario)
    return c


# ── 1. /buscar/ no revienta ──────────────────────────────────────────────────

def test_buscar_con_documento_repetido_responde_409_con_todos_los_candidatos(
    catalogo, client_auth
):
    """El caso exacto que dio 500 en producción el 2-ago."""
    _crear_victima(catalogo, documento="1030547250", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="1030547250", nombre="ROSA", apellido="PEREZ")

    resp = client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "1030547250"},
        format="json",
    )

    assert resp.status_code == 409
    data = resp.json()
    assert data["ambiguo"] is True
    assert len(data["candidatos"]) == 2
    # El aviso tiene que ser accionable, no un error genérico.
    assert "CONFIRME" in data["detail"]
    assert "2 registros" in data["detail"]


def test_buscar_con_documento_unico_sigue_devolviendo_200(catalogo, client_auth):
    """El arreglo del 409 no puede cambiar el camino normal."""
    _crear_victima(catalogo, documento="1030547250", nombre="MARIA", apellido="GOMEZ")

    resp = client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "1030547250"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["tipo_documento_codigo"] == "CC"


def test_buscar_documento_inexistente_sigue_dando_404(catalogo, client_auth):
    resp = client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "99999999"},
        format="json",
    )
    assert resp.status_code == 404


def test_el_409_queda_auditado_como_ambiguo(catalogo, client_auth):
    """
    Una búsqueda ambigua es justo la que hay que poder reconstruir después: si el
    encuestador eligió mal, el log tiene que decir que había más de un candidato.
    """
    from apps.auditoria.models import LogAcceso

    _crear_victima(catalogo, documento="1030547250", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="1030547250", nombre="ROSA", apellido="PEREZ")

    client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "1030547250"},
        format="json",
    )

    log = LogAcceso.objects.filter(accion="BUSQUEDA_RNI").latest("timestamp")
    assert log.detalle["ambiguo"] is True
    assert log.detalle["coincidencias"] == 2
    # El número de documento NUNCA se guarda en el log, ni siquiera acá.
    assert "1030547250" not in json.dumps(log.detalle)


# ── 2. /consultar-fuente/ manda los candidatos ───────────────────────────────

@override_settings(VICTIMA_REPOSITORY="DJANGO")
def test_consultar_fuente_serializa_los_candidatos(catalogo, client_auth):
    """
    El repositorio ya los devolvía; el serializer los tiraba. Verificado contra
    prod: mensaje "Hay 2 registros… CONFIRME cuál corresponde" con candidatos: 0.
    """
    _crear_victima(catalogo, documento="1030547250", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="1030547250", nombre="ROSA", apellido="PEREZ")

    resp = client_auth.post(
        "/api/victimas/consultar-fuente/",
        {"tipo_documento": "CC", "numero_documento": "1030547250"},
        format="json",
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["encontrado"] is True
    assert "CONFIRME" in data["mensaje"]
    # Lo que faltaba: con qué confirmar.
    assert len(data["candidatos"]) == 1
    nombres = {data["victima"]["primer_nombre"], data["candidatos"][0]["primer_nombre"]}
    assert nombres == {"MARIA", "ROSA"}


# ── 3. el manifiesto declara lo que el archivo tiene ─────────────────────────

def test_el_manifiesto_cuenta_las_filas_del_archivo_no_las_leidas(
    catalogo, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.VICTIMA_REPOSITORY = "DJANGO"

    # Dos comparten documento (colapsan en una fila), una es única.
    _crear_victima(catalogo, documento="1030547250", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="1030547250", nombre="ROSA", apellido="PEREZ")
    _crear_victima(catalogo, documento="9990100001", nombre="ANA", apellido="DIAZ")

    call_command("generar_padron")

    padron_dir = os.path.join(str(tmp_path), "padron")
    with open(os.path.join(padron_dir, "padron-latest.json"), encoding="utf-8") as fh:
        m = json.load(fh)

    assert m["registros_leidos"] == 3
    assert m["total_registros"] == 2        # ← lo que la APK va a encontrar
    assert m["colisiones_documento"] == 1

    conn = sqlite3.connect(os.path.join(padron_dir, m["archivo"]))
    try:
        filas = conn.execute("SELECT count(*) FROM padron").fetchone()[0]
    finally:
        conn.close()
    assert filas == m["total_registros"]
