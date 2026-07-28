"""
Tests de la carga del catálogo REAL de puntos de atención (pendiente 3a.11).

Lo que se protege: el cruce a Oracle es POR NOMBRE (`mapeo.resolver_territorio`).
Un punto cuyo nombre Oracle no conoce —como los del placeholder, 'Centro Regional
Medellín'— deja `GIC_N_RELACION_DT_PUNTO` incompleto y el hogar desaparece de los
reportes territoriales, sin error. Por eso el nombre se copia LITERAL del catálogo
y los placeholder se desactivan.
"""
import pytest
from django.core.management import call_command

from apps.parametricas.models import (
    Departamento, DireccionTerritorial, Municipio, PuntoAtencion,
)
from apps.sincronizacion.oracle import catalogos

pytestmark = pytest.mark.django_db


@pytest.fixture
def territorio():
    """DT + departamento + municipios que existen en el crosswalk real de Oracle."""
    dt = DireccionTerritorial.objects.create(
        codigo="DT_CENTRAL", nombre="DIRECCION TERRITORIAL CENTRAL")
    tolima = Departamento.objects.create(codigo_dane="73", nombre="Tolima")
    Municipio.objects.create(codigo_dane="73001", nombre="Ibagué", departamento=tolima)
    Municipio.objects.create(codigo_dane="73026", nombre="Alvarado", departamento=tolima)
    return dt


def test_carga_los_puntos_con_el_nombre_literal_de_oracle(territorio):
    call_command("cargar_puntos_atencion_oracle", verbosity=0)
    nombres_oracle = {f["punto"] for f in _filas_crudas()}
    cargados = set(PuntoAtencion.objects.values_list("nombre", flat=True))
    assert cargados                      # se cargó algo
    assert cargados <= nombres_oracle    # y NADA que Oracle no conozca


def test_desactiva_el_placeholder_que_oracle_no_conoce(territorio):
    """El punto inventado deja de ofrecerse, pero NO se borra (la FK es PROTECT)."""
    muni = Municipio.objects.get(codigo_dane="73001")
    viejo = PuntoAtencion.objects.create(
        codigo="DT_CENTRAL__CR", nombre="Centro Regional Bogotá",
        direccion_territorial=territorio, municipio=muni, activo=True)

    call_command("cargar_puntos_atencion_oracle", verbosity=0)

    viejo.refresh_from_db()
    assert viejo.activo is False
    assert PuntoAtencion.objects.filter(pk=viejo.pk).exists()


def test_el_dry_run_no_escribe(territorio):
    call_command("cargar_puntos_atencion_oracle", "--dry-run", verbosity=0)
    assert PuntoAtencion.objects.count() == 0


def test_es_idempotente(territorio):
    call_command("cargar_puntos_atencion_oracle", verbosity=0)
    primera = PuntoAtencion.objects.count()
    call_command("cargar_puntos_atencion_oracle", verbosity=0)
    assert PuntoAtencion.objects.count() == primera


def test_la_sede_respeta_el_departamento(territorio):
    """
    Hay municipios homónimos en departamentos distintos (La Unión, Albania). Si el
    cruce fuera solo por nombre, un punto del Tolima podría acabar con sede en otro
    departamento. Todos los puntos cargados deben tener sede dentro de su DT.
    """
    call_command("cargar_puntos_atencion_oracle", verbosity=0)
    for punto in PuntoAtencion.objects.select_related("municipio__departamento"):
        assert punto.municipio.departamento.nombre == "Tolima"


def test_el_punto_del_escenario_de_oracle_queda_cargado(territorio):
    """
    'JORNADAS DE ATENCION Y/O FERIAS DE SERVICIO' (idpuntoatencion=13) es el punto con
    el que el Escalón 1/2 escribe de verdad contra Oracle. Si dejara de cargarse, el
    escenario reproducible se rompe.
    """
    call_command("cargar_puntos_atencion_oracle", verbosity=0)
    punto = PuntoAtencion.objects.filter(codigo="ORACLE_PA_13").first()
    assert punto is not None
    assert punto.activo is True
    # y su nombre cruza contra el crosswalk, que es lo que Oracle va a comparar
    objetivo = catalogos.normalizar_nombre(punto.nombre)
    assert any(f["_punto"] == objetivo for f in catalogos.cargar_dt_puntos())


def _filas_crudas():
    import json
    import pathlib
    ruta = (pathlib.Path(catalogos.__file__).with_name("catalogos_oracle.json"))
    return json.loads(ruta.read_text(encoding="utf-8"))["dt_puntos"]
