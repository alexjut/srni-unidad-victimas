"""
La búsqueda encuentra a quien está en el UNIVERSO y no en el padrón.

Los dos casos son reales, reportados desde el territorio: en Vivanto se podían
caracterizar y en SICAV "no existían".
"""
import datetime

import pytest

from apps.victimas.models import PersonaUniverso, Victima
from apps.victimas.repository.base import MotivoNoElegible, num_hash
from apps.victimas.repository.django_orm import DjangoVictimaRepository

CORTE = "TEMP_UNIV_VICT_PER_MI010726ALL"


def _sembrar(documento, cons, **extra):
    return PersonaUniverso.objects.create(
        cons_persona_universo=cons, corte=CORTE,
        fecha_corte=datetime.date(2026, 7, 1),
        numero_documento=documento, tipo_documento="CC",
        numero_documento_hash_sin_tipo=num_hash(documento),
        primer_nombre="RUBIELA", primer_apellido="DIAZ",
        genero="Mujer", num_hechos=3, **extra)


@pytest.fixture
def repo(monkeypatch):
    # La vigencia se resuelve contra Oracle; en pruebas se controla la respuesta.
    from apps.victimas import vigencia_legacy as VL
    monkeypatch.setattr(VL, "_consultar_legado", lambda doc: (None, None))
    return DjangoVictimaRepository()


@pytest.mark.django_db
def test_28548486_nunca_caracterizada_sale_lista_para_caracterizar(repo):
    """Caso real: no está en GIC_PERSONA, sí en el universo, 3 hechos."""
    _sembrar("28548486", 23988216)

    r = repo.buscar_por_documento("CC", "28548486")

    assert r.encontrado, "sigue sin aparecer: la búsqueda no consultó el universo"
    assert r.motivo == MotivoNoElegible.ELEGIBLE
    assert r.victima.numero_documento == "28548486"
    assert r.victima.primer_nombre == "RUBIELA"
    assert r.fuente == "UNIVERSO_RUV"


@pytest.mark.django_db
def test_el_id_del_universo_NUNCA_viaja_como_cons_persona(repo):
    """
    `cons_persona` es lo que se escribe al legado. El id del universo es otra
    numeración: ponerlo ahí mandaría identificadores de otro sistema sin fallar.
    """
    _sembrar("28548486", 23988216)

    r = repo.buscar_por_documento("CC", "28548486")

    assert r.victima.cons_persona is None
    assert r.victima.cons_persona_universo == 23988216


@pytest.mark.django_db
def test_con_ficha_vigente_avisa_y_no_la_da_por_elegible(monkeypatch):
    """Caso real 1115724047: caracterizada el 28-jul-2026."""
    from apps.victimas import vigencia_legacy as VL
    monkeypatch.setattr(VL, "_consultar_legado",
                        lambda doc: (None, datetime.datetime(2026, 7, 28)))
    _sembrar("1115724047", 23664117)

    r = DjangoVictimaRepository().buscar_por_documento("CC", "1115724047")

    assert r.encontrado, "debe aparecer igual: existe y es víctima"
    assert r.motivo == MotivoNoElegible.FICHA_VIGENTE
    assert r.disponible_desde == datetime.date(2028, 7, 28)


@pytest.mark.django_db
def test_la_ruta_de_excepcion_sola_ya_NO_la_habilita(monkeypatch):
    """
    Cambio del 14-ago-2026. Elegir una ruta que omite la vigencia dejó de
    habilitar por sí solo: hace falta que la excepción esté autorizada desde el
    front. Antes bastaba con elegirla en el celular y adjuntar una foto, y la
    operación indicó que el caracterizador no debe tener ese documento.

    El mensaje tiene que decir a dónde ir, no solo que no se puede: sin eso, en
    campo esto se reporta como falla del sistema.
    """
    from apps.victimas import vigencia_legacy as VL
    monkeypatch.setattr(VL, "_consultar_legado",
                        lambda doc: (None, datetime.datetime(2026, 7, 28)))
    _sembrar("1115724047", 23664117)

    r = DjangoVictimaRepository().buscar_por_documento(
        "CC", "1115724047", ruta="ACCIONES_CONSTITUCIONALES")

    assert r.motivo == MotivoNoElegible.FICHA_VIGENTE
    assert "plataforma web" in r.mensaje


@pytest.mark.django_db
def test_si_no_se_puede_verificar_la_vigencia_se_dice(monkeypatch):
    """
    Callarlo sería afirmar que no tiene ficha vigente, que es justo lo que no se
    pudo comprobar. Se entrega igual —una falla nuestra no le cierra la puerta a
    una víctima— pero avisando.
    """
    from apps.victimas import vigencia_legacy as VL

    def cae(doc):
        raise VL.VigenciaNoVerificable("Oracle no responde")

    monkeypatch.setattr(VL, "_consultar_legado", cae)
    _sembrar("28548486", 23988216)

    r = DjangoVictimaRepository().buscar_por_documento("CC", "28548486")

    assert r.encontrado
    assert "no se pudo verificar" in r.mensaje.lower()


@pytest.mark.django_db
def test_el_padron_manda_sobre_el_universo(repo):
    """
    Si la persona SÍ está en el padrón operativo, se responde con esa —tiene
    `cons_persona`, hechos y colisiones resueltas—. El universo es el respaldo.
    """
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
    Victima.objects.create(
        tipo_documento=tipo, numero_documento="28548486",
        numero_documento_hash=doc_hash("CC", "28548486"),
        numero_documento_hash_sin_tipo=num_hash("28548486"),
        primer_nombre="DEL PADRON", primer_apellido="DIAZ",
        fecha_nacimiento="1975-01-01", genero="F", cons_persona=958858,
        habilitado_para_caracterizacion=True)
    _sembrar("28548486", 23988216)

    r = repo.buscar_por_documento("CC", "28548486")

    assert r.victima.primer_nombre == "DEL PADRON"
    assert r.victima.cons_persona == 958858
