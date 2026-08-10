"""
El universo de víctimas — la tabla que reemplaza a `GIC_PERSONA` como fuente de
"quién existe".

El padrón nacía del legacy de caracterización, o sea del registro de *quién ya
fue caracterizado*. Por eso una víctima que nunca pasó por una entrevista era
invisible para SICAV aunque estuviera en el universo (caso real: 28548486).
"""

import datetime

import pytest
from django.db import IntegrityError, transaction

from apps.victimas.models import DescarteUniverso, PersonaUniverso, Victima
from apps.victimas.repository.base import num_hash

CORTE = 'TEMP_UNIV_VICT_PER_MI010726ALL'
CORTE_AGO = 'TEMP_UNIV_VICT_PER_MI010826ALL'


def _persona(**kw):
    datos = dict(
        cons_persona_universo=23988216,
        tipo_documento='CC',
        numero_documento='28548486',
        numero_documento_hash_sin_tipo=num_hash('28548486'),
        primer_nombre='RUBIELA', primer_apellido='DIAZ', segundo_apellido='TRIANA',
        genero='Mujer', pertenencia_etnica='Ninguna',
        ciclo_vital='entre 29 y 59', num_hechos=3,
        corte=CORTE, fecha_corte=datetime.date(2026, 7, 1),
    )
    datos.update(kw)
    return PersonaUniverso.objects.create(**datos)


# ── La regla que casi nos cuesta duplicar el padrón ──────────────────────────

@pytest.mark.django_db
def test_el_id_del_universo_vive_aparte_de_cons_persona():
    """
    Medido sobre 243.610 pares con el mismo documento: CERO coincidencias entre
    el CONS_PERSONA del universo y el PER_IDPERSONA del legacy. Son espacios de
    identificadores distintos.

    `Victima.cons_persona` es lo que `oracle/mapeo.py` escribe al legacy. Si el
    id del universo lo pisara, la escritura mandaría identificadores de otro
    sistema — no falla, escribe mal en silencio.
    """
    p = _persona()

    # El campo existe y es propio.
    assert p.cons_persona_universo == 23988216
    # Y NO hay ningún campo `cons_persona` en este modelo que pueda confundirse.
    assert not hasattr(p, 'cons_persona')


@pytest.mark.django_db
def test_el_cruce_con_el_padron_es_por_documento_no_por_id(catalogo_tipos):
    """
    El enlace se resuelve por hash de documento. Cruzar por id no encontraría
    nada: son numeraciones distintas.
    """
    victima = Victima.objects.create(
        tipo_documento=catalogo_tipos,
        numero_documento='28548486',
        numero_documento_hash_sin_tipo=num_hash('28548486'),
        primer_nombre='RUBIELA', primer_apellido='DIAZ',
        fecha_nacimiento='1975-01-01', genero='F',
        cons_persona=958858,          # el id del LEGACY, distinto del universo
    )
    p = _persona(victima=victima)

    assert p.victima_id == victima.id
    # Los dos ids conviven sin pisarse, y son distintos.
    assert p.cons_persona_universo != victima.cons_persona
    # Y se encuentran por el mismo hash de documento.
    assert p.numero_documento_hash_sin_tipo == victima.numero_documento_hash_sin_tipo


@pytest.fixture
def catalogo_tipos(db):
    from apps.parametricas.models import TipoDocumento
    return TipoDocumento.objects.create(codigo='CC', nombre='Cédula')


# ── Convivencia de cortes ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_dos_cortes_pueden_convivir_sin_pisarse():
    """
    Hace falta para validar un corte nuevo antes de reemplazar el anterior: si
    la unicidad fuera solo por id, cargar agosto borraría julio a mitad de
    camino y dejaría el padrón incompleto mientras corre.
    """
    _persona()
    _persona(corte=CORTE_AGO, fecha_corte=datetime.date(2026, 8, 1))

    assert PersonaUniverso.objects.count() == 2
    assert PersonaUniverso.objects.filter(corte=CORTE).count() == 1


@pytest.mark.django_db
def test_la_misma_persona_no_entra_dos_veces_en_el_mismo_corte():
    _persona()
    with pytest.raises(IntegrityError), transaction.atomic():
        _persona()


# ── Los descartes, que si no se registran no se pueden responder ─────────────

@pytest.mark.django_db
def test_los_descartes_quedan_con_motivo_y_corte():
    """
    Una carga que descarta en silencio es indistinguible de una fuente
    incompleta: sin esto, "faltan 55.100 personas" no se puede contestar.
    """
    DescarteUniverso.objects.create(
        corte=CORTE, cons_persona_universo=999,
        numero_documento_hash_sin_tipo=num_hash('99'),
        motivo='SIN_DOCUMENTO', detalle='DOCUMENTO tiene 2 caracteres')
    DescarteUniverso.objects.create(
        corte=CORTE, cons_persona_universo=1000,
        motivo='DOCUMENTO_REPETIDO')

    assert DescarteUniverso.objects.filter(corte=CORTE).count() == 2
    assert DescarteUniverso.objects.filter(motivo='SIN_DOCUMENTO').count() == 1


@pytest.mark.django_db
def test_el_descarte_guarda_el_hash_y_no_el_documento():
    """Para contar y rastrear no hace falta el número en claro."""
    d = DescarteUniverso.objects.create(
        corte=CORTE, motivo='SIN_DOCUMENTO',
        numero_documento_hash_sin_tipo=num_hash('28548486'))

    assert d.numero_documento_hash_sin_tipo == num_hash('28548486')
    assert not hasattr(d, 'numero_documento')


# ── Lo que el universo sí y no aporta ───────────────────────────────────────

@pytest.mark.django_db
def test_num_hechos_es_un_conteo_no_el_detalle():
    """
    La fuente trae cuántos hechos tiene la persona, no cuáles. El detalle —con
    fecha y municipio— sale de RUV.TBSINIESTROS_PERSONA (`hechos_ruv.py`).
    """
    p = _persona(num_hechos=3)

    assert p.num_hechos == 3
    assert not hasattr(p, 'hechos_victimizantes')


@pytest.mark.django_db
def test_el_corte_queda_registrado_para_saber_de_cuando_es_el_dato():
    """
    El antecedente de GIC_REPORTE_HOGAR —congelado desde 2021 sin que nadie lo
    notara— es la razón de guardar de qué corte salió cada fila.
    """
    p = _persona()

    assert p.corte == CORTE
    assert p.fecha_corte == datetime.date(2026, 7, 1)
