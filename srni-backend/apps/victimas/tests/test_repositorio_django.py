"""
Tests del repositorio sobre nuestra propia base.

Lo que se protege:

1. **Que la búsqueda por documento funcione con PII cifrada.** `numero_documento` es
   un `EncryptedField` y Fernet no es determinista: un `filter(numero_documento=…)`
   no encontraría nunca nada. Toda búsqueda pasa por `numero_documento_hash`. Si
   alguien "simplifica" eso, estos tests se ponen rojos.
2. **Que una persona no elegible se devuelva como ENCONTRADA, con su motivo.**
   Responder "no existe" cuando en realidad está excluida o ya fue caracterizada le
   miente al encuestador que la tiene enfrente.
3. **Que el padrón se itere en streaming**, que es lo que permite generarlo sin
   cargar millones de filas en memoria.
"""
import datetime

import pytest
from django.test import override_settings

from apps.victimas.repository import DjangoVictimaRepository, get_repository
from apps.victimas.repository.base import doc_hash

pytestmark = pytest.mark.django_db


@pytest.fixture
def catalogo(db):
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento
    from apps.victimas.models import CatalogoHechoVictimizante

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula de Ciudadanía")
    depto = Departamento.objects.create(codigo_dane="05", nombre="Antioquia")
    muni = Municipio.objects.create(codigo_dane="05001", nombre="Medellín", departamento=depto)
    hecho = CatalogoHechoVictimizante.objects.create(
        codigo="HV01", nombre="Desplazamiento forzado")
    return {"tipo": tipo, "municipio": muni, "hecho": hecho}


def _crear_victima(catalogo, *, documento="1030547250", estado="INCLUIDO",
                   habilitado=True, fecha_ult=None):
    from apps.victimas.models import Victima
    return Victima.objects.create(
        tipo_documento=catalogo["tipo"],
        numero_documento=documento,
        numero_documento_hash=doc_hash("CC", documento),
        primer_nombre="MARIA", segundo_nombre="LUISA",
        primer_apellido="GOMEZ", segundo_apellido="RENDON",
        fecha_nacimiento="1985-06-15",
        genero="F",
        estado_ruv=estado,
        habilitado_para_caracterizacion=habilitado,
        fecha_ult_caracterizacion=fecha_ult,
        pertenencia_etnica="NINGUNA",
        discapacidad=False,
        municipio_residencia=catalogo["municipio"],
    )


# ── 1. la búsqueda con PII cifrada ───────────────────────────────────────────
def test_encuentra_por_documento_aunque_el_campo_este_cifrado(catalogo):
    _crear_victima(catalogo)
    r = DjangoVictimaRepository().buscar_por_documento("CC", "1030547250")
    assert r.encontrado is True
    assert r.victima.primer_nombre == "MARIA"
    assert r.victima.numero_documento == "1030547250"
    assert r.fuente == "SICAV"


def test_no_encontrada_no_es_un_error(catalogo):
    """El contrato lo dice: 'jamás lanza excepción por no encontrado'."""
    r = DjangoVictimaRepository().buscar_por_documento("CC", "99999999")
    assert r.encontrado is False
    assert r.victima is None
    assert r.mensaje


def test_el_tipo_forma_parte_de_la_llave_pero_el_respaldo_avisa(catalogo):
    """
    El mismo número con otro tipo NO es un match de identidad. Pero tampoco se
    responde "no existe": el índice de respaldo la encuentra y se advierte que
    verifique, porque puede ser la misma persona con el tipo mal registrado —o otra
    distinta—. Esa distinción la hace el encuestador, no una regla.
    """
    _crear_victima(catalogo, documento="1030547250")
    r = DjangoVictimaRepository().buscar_por_documento("TI", "1030547250")
    assert r.encontrado is True
    assert "VERIFIQUE" in r.mensaje
    # y el registro que devuelve es de tipo CC, no TI: el aviso no es decorativo
    assert r.victima.tipo_documento == "CC"


# ── 2. no elegible ≠ inexistente ─────────────────────────────────────────────
def test_una_persona_excluida_se_encuentra_y_se_explica(catalogo):
    _crear_victima(catalogo, estado="EXCLUIDO", habilitado=False)
    r = DjangoVictimaRepository().buscar_por_documento("CC", "1030547250")
    assert r.encontrado is True          # ← lo importante
    assert "excluida" in r.mensaje.lower()


def test_ya_caracterizada_dice_cuando(catalogo):
    _crear_victima(catalogo, habilitado=False,
                   fecha_ult=datetime.datetime(2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc))
    r = DjangoVictimaRepository().buscar_por_documento("CC", "1030547250")
    assert r.encontrado is True
    assert "2026-03-14" in r.mensaje


def test_habilitacion_es_consulta_ligera_y_da_la_razon(catalogo):
    _crear_victima(catalogo, estado="EXCLUIDO", habilitado=False)
    e = DjangoVictimaRepository().verificar_habilitacion("CC", "1030547250")
    assert e.habilitado is False and e.razon


def test_habilitada_no_necesita_razon(catalogo):
    _crear_victima(catalogo)
    assert DjangoVictimaRepository().verificar_habilitacion("CC", "1030547250").habilitado is True


# ── 3. hechos, etnia y territorio llegan al DTO ──────────────────────────────
def test_los_hechos_victimizantes_llegan(catalogo):
    from apps.victimas.models import HechoVictima
    victima = _crear_victima(catalogo)
    HechoVictima.objects.create(victima=victima, hecho=catalogo["hecho"],
                                fecha_hecho=datetime.date(2002, 5, 1),
                                lugar_hecho=catalogo["municipio"])
    r = DjangoVictimaRepository().buscar_por_documento("CC", "1030547250")
    assert len(r.victima.hechos_victimizantes) == 1
    assert r.victima.hechos_victimizantes[0].codigo == "HV01"
    assert r.victima.hechos_victimizantes[0].municipio_hecho == "Medellín"


def test_el_municipio_va_con_codigo_dane(catalogo):
    _crear_victima(catalogo)
    r = DjangoVictimaRepository().buscar_por_documento("CC", "1030547250")
    assert r.victima.municipio_residencia_codigo == "05001"


# ── 4. el padrón se itera en streaming ───────────────────────────────────────
def test_iterar_padron_es_un_generador(catalogo):
    """
    Si devolviera una lista, generar el padrón cargaría millones de filas en RAM
    — justo lo que `generar_padron` evita.
    """
    import types
    _crear_victima(catalogo)
    assert isinstance(DjangoVictimaRepository().iterar_padron(), types.GeneratorType)


def test_iterar_padron_devuelve_todas(catalogo):
    for i in range(3):
        _crear_victima(catalogo, documento=f"100000{i}")
    assert len(list(DjangoVictimaRepository().iterar_padron(batch_size=2))) == 3


def test_el_padron_descargable_no_arrastra_los_hechos(catalogo):
    """Es el resumen para identificar a la persona, no su historia completa."""
    from apps.victimas.models import HechoVictima
    victima = _crear_victima(catalogo)
    HechoVictima.objects.create(victima=victima, hecho=catalogo["hecho"])
    assert list(DjangoVictimaRepository().iterar_padron())[0].hechos_victimizantes == []


# ── 5. el selector ───────────────────────────────────────────────────────────
@override_settings(VICTIMA_REPOSITORY="DJANGO")
def test_el_selector_devuelve_el_repositorio_de_nuestra_base():
    assert isinstance(get_repository(), DjangoVictimaRepository)


@override_settings(VICTIMA_REPOSITORY="CUALQUIER_COSA")
def test_un_valor_desconocido_cae_al_mock_no_a_la_base_vacia():
    """
    El fallback es MOCK a propósito: un padrón vacío respondería "no se encontró la
    persona", que se confunde con un dato real y llevaría a concluir que alguien no
    está en el RUV. Los datos del mock son evidentemente de prueba.
    """
    from apps.victimas.repository import MockVictimaRepository
    assert isinstance(get_repository(), MockVictimaRepository)


# ── 6. UNA sola definición del hash ──────────────────────────────────────────
def test_el_modelo_y_el_buscador_usan_el_mismo_hash(catalogo):
    """
    El defecto que esto evita (encontrado el 2026-07-29): `Victima.save()` guardaba
    `sha256(numero.upper())` y el repositorio buscaba por `doc_hash("tipo|numero")`
    en minúsculas y sin puntos. **Dos hashes distintos para la misma cosa**: la
    búsqueda por documento no encontraba absolutamente nada.

    No se notó durante meses porque el repositorio activo era el mock, que busca por
    diccionario y nunca toca el hash. En el momento en que se enchufa la base real,
    el sistema entero deja de encontrar personas.

    Si alguien vuelve a introducir una fórmula propia en el modelo, este test cae.
    """
    victima = _crear_victima(catalogo, documento="1030547250")
    victima.refresh_from_db()
    assert victima.numero_documento_hash == doc_hash("CC", "1030547250")


@pytest.mark.parametrize("escrito", ["1.030.547.250", "1030547250", " 1030547250 ",
                                     "1030-547-250"])
def test_da_igual_como_se_teclee_el_documento(catalogo, escrito):
    """
    El encuestador escribe la cédula como se la dicten. `doc_hash` normaliza puntos,
    guiones y espacios, así que las cuatro formas encuentran a la misma persona —
    con la fórmula vieja, solo la escrita exactamente igual funcionaba.
    """
    _crear_victima(catalogo, documento="1030547250")
    assert DjangoVictimaRepository().buscar_por_documento("CC", escrito).encontrado is True


def test_el_grupo_familiar_no_se_inventa_con_los_miembros_del_hogar(catalogo):
    """
    Devuelve [] deliberadamente: el grupo familiar del RUV y los miembros del hogar
    caracterizado son cosas distintas. Mezclarlos daría un dato falso con apariencia
    de bueno.
    """
    _crear_victima(catalogo)
    assert DjangoVictimaRepository().obtener_grupo_familiar(1) == []


# ── 7. los duplicados NO se fusionan y el sin-tipo se encuentra ──────────────
def test_dos_registros_con_el_mismo_documento_no_se_fusionan(catalogo):
    """
    La decisión de fondo: dos registros con el mismo número pueden ser DOS PERSONAS
    (una CC y una TI), y con el 14,5 % de la fuente sin tipo no siempre se distingue.
    Fusionar por regla mezclaría dos víctimas en una — una desaparecería del padrón.
    Se devuelven ambas y decide el encuestador, que tiene a la persona enfrente.
    """
    completa = _crear_victima(catalogo, documento="1030547250")
    pobre = _crear_victima(catalogo, documento="1030547250")
    pobre.segundo_nombre = ""
    pobre.segundo_apellido = ""
    pobre.pertenencia_etnica = ""
    pobre.municipio_residencia = None
    pobre.save()

    r = DjangoVictimaRepository().buscar_por_documento("CC", "1030547250")
    assert r.encontrado is True
    assert len(r.candidatos) == 1, "el segundo registro debe ofrecerse, no descartarse"
    assert "CONFIRME" in r.mensaje


def test_el_registro_mas_completo_se_ofrece_primero(catalogo):
    """El criterio de completitud ORDENA; no descarta a nadie."""
    pobre = _crear_victima(catalogo, documento="1030547250")
    pobre.segundo_nombre = ""
    pobre.municipio_residencia = None
    pobre.pertenencia_etnica = ""
    pobre.save()
    _crear_victima(catalogo, documento="1030547250")   # la completa, creada después

    r = DjangoVictimaRepository().buscar_por_documento("CC", "1030547250")
    assert r.victima.segundo_nombre == "LUISA"      # ganó la completa, no la primera
    assert r.victima.municipio_residencia_codigo == "05001"


def test_encuentra_a_quien_no_tiene_tipo_de_documento(catalogo):
    """
    El caso de 1.126.615 personas de la fuente. Antes eran inencontrables: el
    encuestador escribe 'CC + número' y el hash de identidad nunca coincidía.
    """
    from apps.victimas.models import Victima
    sin_tipo = Victima.objects.create(
        tipo_documento=None,
        numero_documento="1030547250",
        primer_nombre="MARIA", primer_apellido="GOMEZ",
        fecha_nacimiento="1985-06-15", genero="F",
        estado_ruv="INCLUIDO", habilitado_para_caracterizacion=True,
    )
    assert sin_tipo.numero_documento_hash_sin_tipo

    r = DjangoVictimaRepository().buscar_por_documento("CC", "1030547250")
    assert r.encontrado is True
    assert "VERIFIQUE" in r.mensaje, "debe advertir que el tipo no coincide"


def test_el_respaldo_no_se_usa_si_la_identidad_ya_coincidio(catalogo):
    """Si el match exacto existe, no se cae al índice ambiguo ni se avisa de más."""
    _crear_victima(catalogo, documento="1030547250")
    r = DjangoVictimaRepository().buscar_por_documento("CC", "1030547250")
    assert "VERIFIQUE" not in r.mensaje
    assert r.candidatos == []


# ── de qué fuente responde el sistema ────────────────────────────────────────
def test_el_selector_de_repositorio_es_una_variable_de_settings():
    """
    `get_repository()` lee `settings.VICTIMA_REPOSITORY`. Si el settings no define
    esa variable, `getattr(..., "MOCK")` cae al mock **sin avisar** y la APK muestra
    personas inventadas aunque el padrón real esté cargado.

    Producción estuvo así hasta el 31-jul-2026: el padrón tenía millones de filas y
    las búsquedas respondían ENC001. El síntoma es engañoso porque el sistema
    "funciona" — solo que contesta con otra base.
    """
    from django.conf import settings
    assert hasattr(settings, "VICTIMA_REPOSITORY"), (
        "settings.VICTIMA_REPOSITORY no está definido: get_repository() caería al "
        "MOCK en silencio. Definilo en srni/settings/base.py.")


def test_django_como_valor_devuelve_el_padron_real():
    from django.test import override_settings
    from apps.victimas.repository import get_repository
    from apps.victimas.repository.django_orm import DjangoVictimaRepository

    with override_settings(VICTIMA_REPOSITORY="DJANGO"):
        assert isinstance(get_repository(), DjangoVictimaRepository)


def test_un_valor_desconocido_no_revienta_pero_tampoco_inventa_una_fuente():
    """Un typo en el .env no debe tumbar el sistema, pero tampoco debe pasar por
    el padrón real: cae al mock, que es evidente a simple vista."""
    from django.test import override_settings
    from apps.victimas.repository import get_repository
    from apps.victimas.repository.mock import MockVictimaRepository

    with override_settings(VICTIMA_REPOSITORY="DJANHO"):
        assert isinstance(get_repository(), MockVictimaRepository)
