"""
El viaje COMPLETO del alta desde el universo: buscar → registrar.

Los tests de `test_alta_desde_universo.py` prueban el serializer con un payload
escrito a mano, y pasan. Lo que nadie probaba es lo que la APK hace de verdad:
tomar la respuesta de `consultar-fuente` **tal cual** y reenviarla a
`registrar-desde-fuente`. Ahí es donde el contrato se rompe.

Importa más allá del bug: el camino offline con el filtro de Bloom va a
construirse sobre este mismo contrato. Si sale roto, se replica el defecto.
"""
import datetime

import pytest

from apps.victimas.models import PersonaUniverso
from apps.victimas.repository.base import num_hash
from apps.victimas.serializers import RegistrarDesdeFuenteSerializer

CORTE = "TEMP_UNIV_VICT_PER_MI010726ALL"


@pytest.fixture
def repo(monkeypatch):
    from apps.victimas import vigencia_legacy as VL
    monkeypatch.setattr(VL, "_consultar_legado", lambda doc: (None, None))
    from apps.victimas.repository.django_orm import DjangoVictimaRepository
    return DjangoVictimaRepository()


def _sembrar(documento, cons, **extra):
    return PersonaUniverso.objects.create(
        cons_persona_universo=cons, corte=CORTE,
        fecha_corte=datetime.date(2026, 7, 1),
        numero_documento=documento, tipo_documento="CC",
        numero_documento_hash_sin_tipo=num_hash(documento),
        primer_nombre="ROSA", segundo_nombre="EMILIA",
        primer_apellido="MOSQUERA", segundo_apellido="DIAZ",
        genero="Mujer", num_hechos=4, **extra)


def _payload_como_lo_manda_la_apk(v) -> dict:
    """
    Lo que la APK reenvía: los campos del `VictimaResumen` que devolvió la
    búsqueda, sin retoques. Si el backend produce un valor que su propio
    serializer rechaza, el contrato está roto de un lado al otro.
    """
    return {
        "tipo_documento": v.tipo_documento,
        "numero_documento": v.numero_documento,
        "primer_nombre": v.primer_nombre,
        "segundo_nombre": v.segundo_nombre,
        "primer_apellido": v.primer_apellido,
        "segundo_apellido": v.segundo_apellido,
        "fecha_nacimiento": v.fecha_nacimiento,
        "genero": v.genero,
        "pertenencia_etnica": v.pertenencia_etnica,
        "estado_ruv": v.estado_ruv,
        "fuente_origen": getattr(v, "fuente_origen", None),
        "habilitado_para_caracterizacion": v.habilitado_para_caracterizacion,
    }


@pytest.mark.django_db
def test_lo_que_devuelve_la_busqueda_es_registrable(repo):
    """
    Caso real del 11-ago: 28683981 está en el universo y no en el padrón.

    Si esto falla, en campo el encuestador ve "No se pudo registrar. Revisa la
    conexión e intenta de nuevo." — un error de contrato disfrazado de fallo de
    red, que manda a buscar señal donde no hay nada que buscar.
    """
    _sembrar("28683981", 17309123)

    resultado = repo.buscar_por_documento("CC", "28683981")
    assert resultado.encontrado

    payload = _payload_como_lo_manda_la_apk(resultado.victima)
    payload = {k: v for k, v in payload.items() if v is not None}

    s = RegistrarDesdeFuenteSerializer(data=payload)
    assert s.is_valid(), (
        f"el backend devuelve un payload que él mismo rechaza: {s.errors}"
    )


@pytest.mark.django_db
def test_la_procedencia_del_universo_no_se_pierde(repo):
    """
    `fuente_origen` es la única traza de que la persona vino del universo y no
    del padrón. Homologarla a 'RUV' para que pase la validación borraría
    justamente el dato que el alta desde el Bloom va a necesitar.
    """
    from apps.victimas.models import Victima

    _sembrar("93021801", 142910)
    resultado = repo.buscar_por_documento("CC", "93021801")

    fuente = getattr(resultado.victima, "fuente_origen", None)
    if fuente is None:
        pytest.skip("el DTO de búsqueda no expone fuente_origen")

    assert fuente in dict(Victima.FUENTE_ORIGEN), (
        f"la búsqueda devuelve fuente_origen={fuente!r}, que no es un valor "
        f"válido del modelo: {[c[0] for c in Victima.FUENTE_ORIGEN]}"
    )
