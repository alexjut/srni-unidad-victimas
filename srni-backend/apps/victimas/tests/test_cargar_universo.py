"""
Carga del universo de víctimas.

Sin Oracle ni red: se prueba la resolución del corte, el desempate y el enlace,
que es donde se pierde el dato en silencio.
"""

import datetime

import pytest

from apps.victimas.management.commands import cargar_universo_victimas as C
from apps.victimas.models import DescarteUniverso, PersonaUniverso, Victima
from apps.victimas.repository.base import num_hash

CORTE = "TEMP_UNIV_VICT_PER_MI010726ALL"


# ── Resolución del corte por fecha ───────────────────────────────────────────

def test_el_nombre_del_corte_se_arma_por_fecha_y_no_esta_embebido():
    assert C.nombre_de_corte(datetime.date(2026, 7, 1)) == CORTE
    assert C.nombre_de_corte(datetime.date(2026, 8, 15)) == \
        "TEMP_UNIV_VICT_PER_MI010826ALL"


def test_del_nombre_se_deduce_la_fecha_para_medir_su_antiguedad():
    assert C.fecha_de_corte(CORTE) == datetime.date(2026, 7, 1)
    assert C.fecha_de_corte("TEMP_UNIV_VICT_PER_MI011225ALL") == datetime.date(2025, 12, 1)


def test_un_nombre_que_no_matchea_no_revienta_devuelve_None():
    """
    Si mañana cambian el patrón, el comando debe avisar que no puede controlar
    la antigüedad — no caerse ni, peor, dar por bueno un corte viejo.
    """
    assert C.fecha_de_corte("OTRA_TABLA") is None
    assert C.fecha_de_corte("") is None
    assert C.fecha_de_corte(None) is None


def test_el_umbral_de_alerta_existe_y_es_mensual():
    """La generación es mensual: 45 días ya es un corte perdido."""
    assert C.DIAS_ALERTA_CORTE == 45


# ── Desempate: determinista, siempre ─────────────────────────────────────────

def _p(cons, **kw):
    datos = dict(cons_persona_universo=cons, corte=CORTE,
                 primer_nombre="", segundo_nombre="", primer_apellido="",
                 segundo_apellido="", genero="", pertenencia_etnica="",
                 ciclo_vital="", tipo_documento="", num_hechos=0)
    datos.update(kw)
    return PersonaUniverso(**datos)


@pytest.mark.parametrize("regla", sorted(C.DESEMPATES))
def test_toda_regla_termina_en_el_id_y_por_eso_es_determinista(regla):
    """
    Sin un criterio final único, dos corridas podrían elegir filas distintas y
    el padrón cambiaría solo, sin que nadie tocara nada.
    """
    orden = C.Command._orden_de(regla)
    iguales = [_p(300), _p(100), _p(200)]
    iguales.sort(key=orden)
    assert [p.cons_persona_universo for p in iguales] == [100, 200, 300]


def test_por_defecto_gana_la_fila_mas_completa():
    orden = C.Command._orden_de("completitud")
    pobre = _p(100)
    rica = _p(999, primer_nombre="ANA", primer_apellido="GOMEZ", genero="Mujer")
    filas = sorted([pobre, rica], key=orden)
    assert filas[0].cons_persona_universo == 999


def test_con_la_regla_hechos_gana_quien_tiene_mas_aunque_este_menos_completa():
    orden = C.Command._orden_de("hechos")
    completa = _p(100, primer_nombre="ANA", primer_apellido="GOMEZ", num_hechos=1)
    con_hechos = _p(999, num_hechos=5)
    filas = sorted([completa, con_hechos], key=orden)
    assert filas[0].cons_persona_universo == 999


def test_num_hechos_nulo_no_rompe_el_orden():
    orden = C.Command._orden_de("hechos")
    filas = sorted([_p(100, num_hechos=None), _p(200, num_hechos=2)], key=orden)
    assert filas[0].cons_persona_universo == 200


# ── Construcción del registro ────────────────────────────────────────────────

def _fila(cons=23988216, doc="28548486", tipo="CC"):
    return (cons, tipo, doc, "RUBIELA", "", "DIAZ", "TRIANA",
            "Mujer", "Ninguna", 0, "", "entre 29 y 59", 3)


def test_el_id_del_universo_va_a_su_campo_y_no_a_cons_persona():
    """
    Cero coincidencias en 243.610 pares medidos: son numeraciones distintas, y
    `cons_persona` es lo que se escribe al legacy.
    """
    r = C.Command()._a_registro(_fila(), CORTE, datetime.date(2026, 7, 1))

    assert r.cons_persona_universo == 23988216
    assert not hasattr(r, "cons_persona")


def test_un_documento_corto_no_genera_hash_de_busqueda():
    """
    Menos de 5 caracteres no identifica a nadie — hay 1,2 M de documentos de un
    solo carácter en la fuente. Sin hash, esa fila no se devuelve por búsqueda.
    """
    r = C.Command()._a_registro(_fila(doc="99"), CORTE, None)

    assert r.numero_documento_hash_sin_tipo == ""
    assert r.numero_documento_hash == ""


def test_un_documento_usable_genera_los_dos_hashes():
    r = C.Command()._a_registro(_fila(), CORTE, None)

    assert r.numero_documento_hash_sin_tipo == num_hash("28548486")
    assert r.numero_documento_hash != ""


def test_sin_tipo_de_documento_igual_queda_el_hash_de_respaldo():
    """El 14,5 % de la fuente no trae tipo; sin este hash serían inencontrables."""
    r = C.Command()._a_registro(_fila(tipo=""), CORTE, None)

    assert r.numero_documento_hash_sin_tipo == num_hash("28548486")
    assert r.numero_documento_hash == ""


def test_una_fila_sin_id_de_fuente_se_descarta_en_vez_de_inventarlo():
    assert C.Command()._a_registro(_fila(cons=None), CORTE, None) is None


# ── Enlace con el padrón, por documento ──────────────────────────────────────

@pytest.mark.django_db
def test_el_enlace_encuentra_a_la_victima_por_documento_no_por_id():
    from apps.parametricas.models import TipoDocumento

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento="28548486",
        numero_documento_hash_sin_tipo=num_hash("28548486"),
        primer_nombre="RUBIELA", primer_apellido="DIAZ",
        fecha_nacimiento="1975-01-01", genero="F",
        cons_persona=958858,          # id del LEGACY: distinto del universo
    )
    PersonaUniverso.objects.create(
        cons_persona_universo=23988216, corte=CORTE,
        numero_documento="28548486",
        numero_documento_hash_sin_tipo=num_hash("28548486"),
    )

    C.Command()._enlazar_con_padron(CORTE, confirmar=True)

    p = PersonaUniverso.objects.get(cons_persona_universo=23988216)
    assert p.victima_id == victima.id
    # Y el id del legacy quedó intacto: es lo que se escribe a Oracle.
    victima.refresh_from_db()
    assert victima.cons_persona == 958858


@pytest.mark.django_db
def test_quien_esta_solo_en_el_universo_queda_sin_enlazar_y_eso_esta_bien():
    """
    Es el hueco que esta tabla viene a cubrir: 28548486 no estaba en SICAV. Que
    quede sin `victima` es el resultado correcto, no un fallo del cruce.
    """
    PersonaUniverso.objects.create(
        cons_persona_universo=23988216, corte=CORTE,
        numero_documento="28548486",
        numero_documento_hash_sin_tipo=num_hash("28548486"),
    )

    C.Command()._enlazar_con_padron(CORTE, confirmar=True)

    assert PersonaUniverso.objects.get(cons_persona_universo=23988216).victima_id is None


# ── Resolución de duplicados: no se borra nada ──────────────────────────────

@pytest.mark.django_db
def test_el_duplicado_pierde_la_preferencia_pero_NO_se_borra():
    """
    Una fila que pierde el desempate sigue siendo un dato real de la fuente.
    Borrarla haría imposible responder después por qué esa persona no aparece.
    """
    h = num_hash("28548486")
    PersonaUniverso.objects.create(
        cons_persona_universo=100, corte=CORTE, numero_documento="28548486",
        numero_documento_hash_sin_tipo=h, primer_nombre="RUBIELA",
        primer_apellido="DIAZ", genero="Mujer")
    PersonaUniverso.objects.create(
        cons_persona_universo=200, corte=CORTE, numero_documento="28548486",
        numero_documento_hash_sin_tipo=h)

    C.Command()._resolver_duplicados(CORTE, "completitud", confirmar=True)

    assert PersonaUniverso.objects.filter(corte=CORTE).count() == 2   # ninguna borrada
    assert PersonaUniverso.objects.get(cons_persona_universo=100).es_preferida is True
    assert PersonaUniverso.objects.get(cons_persona_universo=200).es_preferida is False

    descarte = DescarteUniverso.objects.get(cons_persona_universo=200)
    assert descarte.motivo == "DOCUMENTO_REPETIDO"
    assert "100" in descarte.detalle          # dice quién ganó


@pytest.mark.django_db
def test_sin_documento_no_entra_al_desempate():
    """Las filas sin hash no compiten entre sí: no comparten identidad."""
    PersonaUniverso.objects.create(cons_persona_universo=100, corte=CORTE,
                                   numero_documento="99")
    PersonaUniverso.objects.create(cons_persona_universo=200, corte=CORTE,
                                   numero_documento="0")

    C.Command()._resolver_duplicados(CORTE, "completitud", confirmar=True)

    assert PersonaUniverso.objects.filter(es_preferida=False).count() == 0
