"""
Que una persona del universo se pueda REGISTRAR para caracterizarla.

Encontrarla en la búsqueda no servía de nada: el alta exigía fecha de
nacimiento, el universo no la trae, y `28548486` —que existe en el RUV y nunca
fue caracterizada— quedaba igual de bloqueada que antes.
"""
import datetime

import pytest

from apps.victimas.serializers import RegistrarDesdeFuenteSerializer

BASE = {
    "tipo_documento": "CC", "numero_documento": "28548486",
    "primer_nombre": "RUBIELA", "primer_apellido": "DIAZ",
    "genero": "F", "estado_ruv": "NO_VERIFICADO",
    "habilitado_para_caracterizacion": True,
}


def test_se_puede_registrar_sin_fecha_de_nacimiento():
    """El caso real: el universo no la trae y el encuestador la captura después."""
    s = RegistrarDesdeFuenteSerializer(data={**BASE, "fecha_nacimiento": None})
    assert s.is_valid(), s.errors


def test_tambien_se_puede_registrar_omitiendo_el_campo():
    s = RegistrarDesdeFuenteSerializer(data=BASE)
    assert s.is_valid(), s.errors


def test_si_la_fecha_viene_se_respeta():
    """No se pierde el dato cuando el legado sí lo tiene."""
    s = RegistrarDesdeFuenteSerializer(
        data={**BASE, "fecha_nacimiento": "1975-03-14"})
    assert s.is_valid(), s.errors
    assert s.validated_data["fecha_nacimiento"] == datetime.date(1975, 3, 14)


@pytest.mark.django_db
def test_la_fecha_de_nacimiento_del_legado_se_guarda_en_el_universo(monkeypatch):
    """
    Se resuelve en el MISMO viaje que la vigencia: son la misma consulta contra
    `GIC_PERSONA`, así que pedirlas por separado sería pagar dos veces.
    """
    from apps.victimas import vigencia_legacy as VL
    from apps.victimas.models import PersonaUniverso
    from apps.victimas.repository.base import num_hash

    monkeypatch.setattr(
        VL, "_consultar_legado",
        lambda doc: (datetime.datetime(1975, 3, 14), datetime.datetime(2026, 7, 28)))

    p = PersonaUniverso.objects.create(
        cons_persona_universo=23664117, corte="C", numero_documento="1115724047",
        numero_documento_hash_sin_tipo=num_hash("1115724047"))

    fecha, verificada = VL.resolver(p)

    assert verificada
    p.refresh_from_db()
    assert p.fecha_nacimiento == datetime.date(1975, 3, 14)
    assert p.fecha_ult_caracterizacion is not None


@pytest.mark.django_db
def test_quien_nunca_paso_por_el_legado_queda_sin_fecha_y_no_se_inventa(monkeypatch):
    """
    `28548486` no está en `GIC_PERSONA`. La fecha queda vacía para que la capture
    el encuestador — jamás derivada del ciclo vital.
    """
    from apps.victimas import vigencia_legacy as VL
    from apps.victimas.models import PersonaUniverso
    from apps.victimas.repository.base import num_hash

    monkeypatch.setattr(VL, "_consultar_legado", lambda doc: (None, None))
    p = PersonaUniverso.objects.create(
        cons_persona_universo=23988216, corte="C", numero_documento="28548486",
        numero_documento_hash_sin_tipo=num_hash("28548486"), ciclo_vital="ADULTEZ")

    VL.resolver(p)

    p.refresh_from_db()
    assert p.fecha_nacimiento is None
    assert p.ciclo_vital == "ADULTEZ"     # el dato que sí hay se conserva
