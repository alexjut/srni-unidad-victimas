"""
Tests de `purgar_padron`.

Lo único que importa de este comando es lo que **no** borra. Borrar de más aquí
significa perder trabajo de campo: una persona que un encuestador dio de alta
porque no estaba en el padrón, o una que ya está enlazada a una caracterización.
"""
import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def _victima(cons, **extra):
    from apps.victimas.models import Victima
    return Victima.objects.create(
        cons_persona=cons, numero_documento=f"{cons}0000",
        primer_nombre="X", primer_apellido="Y", genero="M", **extra)


@pytest.fixture
def usuario(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(
        codigo_usuario="ENC001", email="enc001@uariv.gov.co",
        nombre_completo="Encuestador Uno", password="x")


def test_el_dry_run_no_borra_nada(db):
    from apps.victimas.models import Victima
    for cons in (1, 2, 3):
        _victima(cons)
    call_command("purgar_padron", verbosity=0)
    assert Victima.objects.count() == 3


def test_borra_las_de_carga_masiva(db):
    from apps.victimas.models import Victima
    for cons in range(1, 6):
        _victima(cons)
    call_command("purgar_padron", "--confirmar", verbosity=0)
    assert Victima.objects.count() == 0


def test_preserva_las_altas_manuales(db, usuario):
    """Un encuestador la creó en campo porque no estaba en el padrón — que es el
    caso de 1 de cada 4 víctimas incluidas. Borrarla sería perder ese trabajo."""
    from apps.victimas.models import Victima
    _victima(1)
    _victima(2)
    manual = _victima(99, creado_por=usuario)

    call_command("purgar_padron", "--confirmar", verbosity=0)

    assert Victima.objects.count() == 1
    assert Victima.objects.get().id == manual.id


def test_preserva_las_enlazadas_a_un_hogar(db):
    """Están en un hogar caracterizado: borrarlas dejaría la caracterización
    huérfana. Cubre las dos vías —ser miembro y ser el autorizado del hogar—
    porque son dos relaciones distintas hacia `Victima`."""
    from apps.hogares.models import Hogar, MiembroHogar
    from apps.victimas.models import Victima

    suelta = _victima(1)
    autorizado = _victima(2)
    miembro = _victima(3)
    hogar = Hogar.objects.create(codigo_hogar="999999-TEST", autorizado=autorizado)
    MiembroHogar.objects.create(hogar=hogar, victima=miembro)

    call_command("purgar_padron", "--confirmar", verbosity=0)

    assert Victima.objects.filter(id=autorizado.id).exists(), "el titular del hogar"
    assert Victima.objects.filter(id=miembro.id).exists(), "el miembro del hogar"
    assert not Victima.objects.filter(id=suelta.id).exists()


def test_no_queda_ninguna_relacion_sin_proteger(db):
    """
    Red de seguridad: si alguien agrega una tabla que apunte a `Victima` y no la
    suma a `_protegidas`, la purga borraría filas con datos enlazados (o reventaría
    por una FK). Este test falla el día que eso pase, no en producción.
    """
    from apps.victimas.models import Victima
    from apps.victimas.management.commands.purgar_padron import Command

    entrantes = {
        rel.get_accessor_name()
        for rel in Victima._meta.related_objects
        # las que apuntan a Victima como dato propio, no como autoría
        if rel.field.name not in ("creado_por",)
    }
    protegidas_por_el_comando = set(Command._protegidas.__doc__ and
                                    ["membresias_hogar", "hogares_como_autorizado",
                                     "hechos_victimizantes"])
    faltantes = entrantes - protegidas_por_el_comando
    assert not faltantes, (
        f"Relaciones hacia Victima que la purga NO protege: {sorted(faltantes)}. "
        f"Agregalas a purgar_padron._protegidas o confirmá que se pueden borrar.")


def test_deja_registro_en_la_bitacora(db):
    from apps.victimas.models import CargaPadron
    for cons in (1, 2, 3):
        _victima(cons)
    call_command("purgar_padron", "--confirmar", verbosity=0)

    registro = CargaPadron.objects.filter(origen__icontains="purga").get()
    assert registro.estado == "COMPLETADA"
    assert registro.descartadas == 3
    assert registro.terminada_en is not None


def test_sobre_padron_vacio_no_falla(db):
    call_command("purgar_padron", "--confirmar", verbosity=0)
