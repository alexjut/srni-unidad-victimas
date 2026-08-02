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


# ── 1-bis. Repetido no es lo mismo que ambiguo ───────────────────────────────

def test_no_pregunta_cuando_el_veredicto_dice_que_es_la_misma_persona(
    catalogo, client_auth
):
    """
    El 92 % del padrón real: el mismo documento repetido porque el Oracle de
    origen duplicó a la persona. Preguntar ahí es ruido — y el ruido enseña al
    encuestador a ignorar el aviso justo antes del 7 % en que importa.
    """
    from apps.victimas.models import ColisionDocumento

    _crear_victima(catalogo, documento="1030547250", nombre="ALBA", apellido="TAPIA")
    completa = _crear_victima(catalogo, documento="1030547250", nombre="ALBA",
                              apellido="TAPIA", cons_persona=77)
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "1030547250"), clase="DUPLICADO_FUENTE",
        filas=2, personas=1, victima_preferida=completa,
    )

    resp = client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "1030547250"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(completa.id)      # la más completa


def test_sigue_preguntando_cuando_el_veredicto_dice_AMBIGUO(catalogo, client_auth):
    from apps.victimas.models import ColisionDocumento

    _crear_victima(catalogo, documento="1030547250", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="1030547250", nombre="ROSA", apellido="PEREZ")
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "1030547250"), clase="AMBIGUO",
        filas=2, personas=2, victima_preferida=None,
    )

    resp = client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "1030547250"},
        format="json",
    )
    assert resp.status_code == 409
    assert len(resp.json()["candidatos"]) == 2


def test_un_documento_de_relleno_no_devuelve_a_nadie(catalogo, client_auth):
    """
    Buscar `99` no puede devolver a una de las 3.780 personas que lo comparten.
    Tampoco es un 404 —la persona puede existir—: es un documento que no sirve
    para identificar, y eso hay que decirlo.
    """
    from apps.victimas.models import ColisionDocumento

    _crear_victima(catalogo, documento="99", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="99", nombre="PEDRO", apellido="PEREZ")
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "99"), clase="NO_IDENTIFICANTE",
        filas=2, personas=0, victima_preferida=None,
    )

    resp = client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "99"},
        format="json",
    )
    assert resp.status_code == 409
    data = resp.json()
    assert data["no_identificante"] is True
    assert "candidatos" not in data          # no se muestra a nadie
    assert "alta manual" in data["detail"]


def test_sin_veredicto_se_pregunta_igual(catalogo, client_auth):
    """
    Default seguro: si la clasificación no corrió todavía, el sistema no asume
    que es la misma persona. Prefiere la pregunta de más.
    """
    _crear_victima(catalogo, documento="1030547250", nombre="ALBA", apellido="TAPIA")
    _crear_victima(catalogo, documento="1030547250", nombre="ALBA", apellido="TAPIA")

    resp = client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "1030547250"},
        format="json",
    )
    assert resp.status_code == 409


def test_consultar_fuente_tampoco_avisa_si_es_la_misma_persona(catalogo, client_auth, settings):
    """El camino de la APK, con el mismo criterio que el web."""
    from apps.victimas.models import ColisionDocumento

    settings.VICTIMA_REPOSITORY = "DJANGO"
    _crear_victima(catalogo, documento="1030547250", nombre="ALBA", apellido="TAPIA")
    completa = _crear_victima(catalogo, documento="1030547250", nombre="ALBA",
                              apellido="TAPIA", cons_persona=77)
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "1030547250"), clase="DUPLICADO_FUENTE",
        filas=2, personas=1, victima_preferida=completa,
    )

    resp = client_auth.post(
        "/api/victimas/consultar-fuente/",
        {"tipo_documento": "CC", "numero_documento": "1030547250"},
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["candidatos"] == []
    assert "CONFIRME" not in data["mensaje"]


# ── 1-ter. el respaldo por número mezcla documentos distintos ────────────────

def test_el_respaldo_por_numero_no_descarta_a_las_personas_de_otro_documento(
    catalogo, client_auth, settings
):
    """
    El 14,5 % del padrón está cargado SIN tipo de documento, así que la búsqueda
    cae a un respaldo que empareja solo por número. Ese resultado mezcla filas de
    documentos distintos —la misma cédula como CC, como TI y sin tipo—.

    Resolver ese conjunto con el veredicto de la primera fila borraba a las
    personas de los otros documentos: el mismo borrado silencioso que este código
    existe para impedir, entrando por la puerta de atrás.
    """
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import ColisionDocumento
    from apps.victimas.repository import DjangoVictimaRepository

    settings.VICTIMA_REPOSITORY = "DJANGO"
    ti = TipoDocumento.objects.create(codigo="TI", nombre="Tarjeta de Identidad")

    # Dos filas de ALBA con tipo CC → el veredicto dice que son la misma persona.
    _crear_victima(catalogo, documento="1030547250", nombre="ALBA", apellido="TAPIA")
    alba = _crear_victima(catalogo, documento="1030547250", nombre="ALBA",
                          apellido="TAPIA", cons_persona=77)
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "1030547250"), clase="DUPLICADO_FUENTE",
        filas=2, personas=1, victima_preferida=alba,
    )
    # Y una persona DISTINTA con el mismo número, registrada como TI.
    otra = _crear_victima(catalogo, documento="1030547250", nombre="ROSA",
                          apellido="PEREZ", tipo_documento=ti)
    otra.numero_documento_hash = doc_hash("TI", "1030547250")
    otra.save(update_fields=["numero_documento_hash"])

    # Se busca con un tipo que no tiene filas propias (CE) → cae al respaldo.
    r = DjangoVictimaRepository().buscar_por_documento("CE", "1030547250")

    assert r.encontrado is True
    # Las dos personas siguen ahí: ALBA (una sola vez) y ROSA.
    nombres = {r.victima.primer_nombre} | {c.primer_nombre for c in r.candidatos}
    assert nombres == {"ALBA", "ROSA"}
    assert "VERIFIQUE" in r.mensaje


def test_un_documento_de_relleno_no_devuelve_a_nadie_por_el_repositorio(
    catalogo, settings
):
    """El camino de la APK: mismo criterio que el web, o en campo se cuela."""
    from apps.victimas.models import ColisionDocumento
    from apps.victimas.repository import DjangoVictimaRepository

    settings.VICTIMA_REPOSITORY = "DJANGO"
    _crear_victima(catalogo, documento="99", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="99", nombre="PEDRO", apellido="PEREZ")
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "99"), clase="NO_IDENTIFICANTE",
        filas=2, personas=0, victima_preferida=None,
    )

    r = DjangoVictimaRepository().buscar_por_documento("CC", "99")
    assert r.encontrado is False          # → la APK ofrece alta manual
    assert r.victima is None
    assert "no identifica" in r.mensaje


def test_documento_de_relleno_con_una_sola_fila_tampoco_la_devuelve(
    catalogo, client_auth
):
    """
    El veredicto se consultaba solo con MÁS de una coincidencia. Un documento de
    relleno puede quedar con una sola fila para un tipo dado, y entonces se
    devolvía a esa persona como si el número la identificara.
    """
    from apps.victimas.models import ColisionDocumento

    _crear_victima(catalogo, documento="0", nombre="MARIA", apellido="GOMEZ")
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "0"), clase="NO_IDENTIFICANTE",
        filas=1, personas=0, victima_preferida=None,
    )

    resp = client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "0"},
        format="json",
    )
    assert resp.status_code == 409
    assert resp.json()["no_identificante"] is True


def test_la_busqueda_web_encuentra_a_quien_esta_cargado_sin_tipo(catalogo, client_auth):
    """
    1.126.615 víctimas (14,5 % del padrón) están cargadas SIN tipo de documento.
    La vista web filtraba además por `tipo_documento__codigo`, así que respondía
    404 "no se encontró ninguna víctima con ese documento" — literalmente falso, y
    es la frase que empuja a dar de alta a mano a alguien que ya está.
    """
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import num_hash

    v = _crear_victima(catalogo, documento="52147896", nombre="LUZ", apellido="DIAZ")
    # Como la fuente: sin tipo, y el hash de identidad calculado con tipo vacío.
    Victima.objects.filter(pk=v.pk).update(
        tipo_documento=None,
        numero_documento_hash=doc_hash("", "52147896"),
        numero_documento_hash_sin_tipo=num_hash("52147896"),
    )

    resp = client_auth.post(
        "/api/victimas/buscar/",
        {"tipo_documento_codigo": "CC", "numero_documento": "52147896"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(v.id)


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


# ── 2-bis. la precarga con la que arranca la jornada ─────────────────────────

def test_la_precarga_marca_los_documentos_ambiguos(catalogo, client_auth, settings):
    """
    La precarga es lo primero que baja al dispositivo al abrir sesión. Si viaja
    sin la marca, en campo y sin señal la app muestra a una de las dos personas
    como si fuera la única.
    """
    from apps.victimas.models import ColisionDocumento

    settings.VICTIMA_REPOSITORY = "DJANGO"
    _crear_victima(catalogo, documento="1030547250", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="1030547250", nombre="ROSA", apellido="PEREZ")
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "1030547250"), clase="AMBIGUO",
        filas=2, personas=2, victima_preferida=None,
    )

    resp = client_auth.get("/api/victimas/precarga/")
    assert resp.status_code == 200
    padron = resp.json()["padron"]

    # Las dos viajan, y las dos marcadas.
    assert len(padron) == 2
    assert {p["clase_colision"] for p in padron} == {"AMBIGUO"}


def test_la_precarga_no_repite_a_la_misma_persona(catalogo, client_auth, settings):
    from apps.victimas.models import ColisionDocumento

    settings.VICTIMA_REPOSITORY = "DJANGO"
    _crear_victima(catalogo, documento="1030547250", nombre="ALBA", apellido="TAPIA")
    completa = _crear_victima(catalogo, documento="1030547250", nombre="ALBA",
                              apellido="TAPIA", cons_persona=77)
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "1030547250"), clase="DUPLICADO_FUENTE",
        filas=2, personas=1, victima_preferida=completa,
    )

    padron = client_auth.get("/api/victimas/precarga/").json()["padron"]
    assert len(padron) == 1
    assert padron[0]["cons_persona"] == 77
    assert padron[0]["clase_colision"] is None


# ── 3. el manifiesto declara lo que el archivo tiene ─────────────────────────

def test_dos_personas_distintas_con_el_mismo_documento_van_LAS_DOS_al_padron(
    catalogo, settings, tmp_path
):
    """
    El defecto que borraba víctimas del padrón que se lleva a campo.

    Con `doc_hash` como PRIMARY KEY e `INSERT OR REPLACE`, la segunda persona
    pisaba a la primera sin avisar y desaparecía del archivo. Extrapolado sobre
    el padrón real, ~53 mil personas distintas.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    settings.VICTIMA_REPOSITORY = "DJANGO"

    _crear_victima(catalogo, documento="1030547250", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="1030547250", nombre="ROSA", apellido="PEREZ")
    _crear_victima(catalogo, documento="9990100001", nombre="ANA", apellido="DIAZ")

    call_command("generar_padron")

    padron_dir = os.path.join(str(tmp_path), "padron")
    with open(os.path.join(padron_dir, "padron-latest.json"), encoding="utf-8") as fh:
        m = json.load(fh)

    assert m["registros_leidos"] == 3
    assert m["total_registros"] == 3        # ← las tres, ninguna se pierde

    conn = sqlite3.connect(os.path.join(padron_dir, m["archivo"]))
    try:
        clave = bytes.fromhex(doc_hash("CC", "1030547250"))[:16]
        nombres = {
            r[0] for r in conn.execute(
                "SELECT nombre FROM padron WHERE doc_hash = ?", (clave,)
            )
        }
    finally:
        conn.close()
    assert nombres == {"MARIA GOMEZ", "ROSA PEREZ"}


def test_los_duplicados_de_la_fuente_viajan_una_sola_vez(catalogo, settings, tmp_path):
    """
    La otra cara: si el veredicto dice que las filas son la MISMA persona, al
    dispositivo va una sola. En el padrón real hay un documento con 505 filas de
    la misma señora; mandarlas todas es peso sin información.
    """
    from apps.victimas.models import ColisionDocumento

    settings.MEDIA_ROOT = str(tmp_path)
    settings.VICTIMA_REPOSITORY = "DJANGO"

    pobre = _crear_victima(catalogo, documento="1030547250", nombre="ALBA",
                           apellido="TAPIA")
    completa = _crear_victima(catalogo, documento="1030547250", nombre="ALBA",
                              apellido="TAPIA", cons_persona=77)
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "1030547250"), clase="DUPLICADO_FUENTE",
        filas=2, personas=1, victima_preferida=completa,
    )

    call_command("generar_padron")

    padron_dir = os.path.join(str(tmp_path), "padron")
    with open(os.path.join(padron_dir, "padron-latest.json"), encoding="utf-8") as fh:
        m = json.load(fh)

    assert m["total_registros"] == 1
    conn = sqlite3.connect(os.path.join(padron_dir, m["archivo"]))
    try:
        fila = conn.execute(
            "SELECT nombre, cons_persona, clase_colision FROM padron"
        ).fetchone()
    finally:
        conn.close()
    # Viaja la más completa (survivorship), y sin marca: no hay nada que confirmar.
    assert fila == ("ALBA TAPIA", 77, None)
    assert pobre.id != completa.id


def test_un_documento_de_relleno_no_lleva_datos_de_nadie(catalogo, settings, tmp_path):
    """
    `99` tiene 4.297 filas y 3.780 nombres distintos. Al padrón va la marca de que
    ese número no identifica —una vez—, nunca el nombre de una de esas personas.
    """
    from apps.victimas.models import ColisionDocumento

    settings.MEDIA_ROOT = str(tmp_path)
    settings.VICTIMA_REPOSITORY = "DJANGO"

    _crear_victima(catalogo, documento="99", nombre="MARIA", apellido="GOMEZ")
    _crear_victima(catalogo, documento="99", nombre="PEDRO", apellido="PEREZ")
    ColisionDocumento.objects.create(
        doc_hash=doc_hash("CC", "99"), clase="NO_IDENTIFICANTE",
        filas=2, personas=0, victima_preferida=None,
    )

    call_command("generar_padron")

    padron_dir = os.path.join(str(tmp_path), "padron")
    with open(os.path.join(padron_dir, "padron-latest.json"), encoding="utf-8") as fh:
        m = json.load(fh)

    conn = sqlite3.connect(os.path.join(padron_dir, m["archivo"]))
    try:
        filas = conn.execute(
            "SELECT nombre, cons_persona, clase_colision FROM padron WHERE doc_hash = ?",
            (bytes.fromhex(doc_hash("CC", "99"))[:16],),
        ).fetchall()
    finally:
        conn.close()

    assert filas == [("", None, "NO_IDENTIFICANTE")]   # una marca, sin datos
    assert m["documentos_no_identificantes"] == 1
