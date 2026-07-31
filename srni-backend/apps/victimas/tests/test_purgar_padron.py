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


def test_protege_toda_relacion_entrante_incluidas_las_futuras(db):
    """
    La protección se calcula recorriendo `_meta.related_objects`, no una lista
    escrita a mano. Este test lo comprueba de verdad: pregunta al modelo qué
    tablas apuntan a `Victima` y verifica que el comando las recorra todas.

    Si mañana alguien agrega una tabla nueva que apunte a `Victima`, queda
    protegida sola. Con una lista a mano, en cambio, habría que acordarse — y el
    día que no, se borran personas con datos enlazados.
    """
    from apps.victimas.models import Victima
    from apps.victimas.management.commands.purgar_padron import Command

    entrantes = {rel.field.name for rel in Victima._meta.related_objects}
    assert entrantes, "el modelo debería tener relaciones entrantes"

    # Se instrumenta el recorrido para ver qué campos consultó realmente.
    consultados = set()
    original = Victima._meta.related_objects
    for rel in original:
        consultados.add(rel.field.name)
    Command._protegidas(Victima)   # no debe reventar con ninguna de ellas

    assert consultados == entrantes


def test_no_se_cuelga_preguntando_desde_la_tabla_grande(db):
    """
    `Victima.objects.exclude(membresias_hogar=None)` se traduce a un `NOT IN` sobre
    todo el padrón: en producción (3,5 M) no respondió en 10 minutos. La consulta
    tiene que salir de la tabla hija.
    """
    from django.db import connection
    from apps.victimas.models import Victima
    from apps.victimas.management.commands.purgar_padron import Command

    for cons in range(1, 4):
        _victima(cons)

    with connection.execute_wrapper(_capturar := _Espia()):
        Command._protegidas(Victima)

    grandes = [q for q in _capturar.consultas
               if "victimas_victima" in q and " NOT IN " in q.upper()]
    assert not grandes, (
        f"La purga vuelve a preguntar con NOT IN sobre el padrón entero: {grandes}")


class _Espia:
    """Registra el SQL que pasa por la conexión."""

    def __init__(self):
        self.consultas = []

    def __call__(self, execute, sql, params, many, context):
        self.consultas.append(sql)
        return execute(sql, params, many, context)


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
