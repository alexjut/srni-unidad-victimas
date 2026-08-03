"""
El catálogo de encuestadores del legacy (`GIC_USUARIO` → `UsuarioLegacy`).

Lo que se prueba acá es la normalización de una tabla que **no valida casi nada**:
en `GIC_USUARIO` solo hay CHECKs de NOT NULL, así que el correo puede no ser un
correo, los nombres pueden traer espacios de sobra y `USU_DADODEBAJA` es un
NUMBER que en la práctica se usa como bandera. Una fila con basura en un campo no
puede tumbar la importación de los otros ocho mil.
"""
import pytest

from apps.sincronizacion.management.commands.importar_usuarios_legacy import (
    _nombre_completo, _texto,
)
from apps.sincronizacion.models import UsuarioLegacy

pytestmark = pytest.mark.django_db


def test_el_nombre_se_arma_con_las_partes_que_existen():
    assert _nombre_completo("JHONATHAN", None, "GUARIN", "HENAO") == \
        "JHONATHAN GUARIN HENAO"
    assert _nombre_completo("ANA", "MARIA", "PEREZ", "GOMEZ") == \
        "ANA MARIA PEREZ GOMEZ"


def test_los_espacios_de_sobra_no_llegan_al_nombre():
    """Oracle trae padding en las NVARCHAR2; concatenar sin limpiar deja huecos."""
    assert _nombre_completo("  ANA  ", "   ", " PEREZ", None) == "ANA PEREZ"


def test_un_nombre_vacio_no_produce_espacios_sueltos():
    assert _nombre_completo(None, None, None, None) == ""


def test_la_cadena_vacia_de_oracle_es_none_y_se_normaliza_igual():
    """En Oracle '' ES NULL: las dos formas tienen que dar lo mismo."""
    assert _texto(None) == _texto("") == _texto("   ") == ""


def test_el_modelo_conserva_al_usuario_dado_de_baja():
    """
    Un usuario de baja sigue siendo el autor de sus hogares. Filtrarlo al
    importar dejaría sin resolver justamente los casos viejos, que son los que
    llegan como novedad desde el territorio.
    """
    u = UsuarioLegacy.objects.create(
        usu_idusuario=4321, usu_usuario="JGUARINH",
        nombre_completo="JHONATHAN GUARIN HENAO", dado_de_baja=True)
    assert UsuarioLegacy.objects.filter(usu_usuario="JGUARINH").count() == 1
    assert str(u) == "JGUARINH (4321)"


def test_el_enlace_con_sicav_es_opcional():
    """
    La mayoría de los ~8.100 del legacy no tiene cuenta en SICAV. Si el enlace
    fuera obligatorio habría que inventar correspondencias, que es exactamente lo
    que en este proyecto ya salió caro.
    """
    u = UsuarioLegacy.objects.create(usu_idusuario=1, usu_usuario="X")
    assert u.usuario_sicav is None


def test_dos_usuarios_del_legacy_no_pueden_compartir_id():
    """`USU_IDUSUARIO` es la PK acá porque es el valor que viaja en GIC_HOGAR."""
    from django.db import IntegrityError

    UsuarioLegacy.objects.create(usu_idusuario=7, usu_usuario="A")
    with pytest.raises(IntegrityError):
        UsuarioLegacy.objects.create(usu_idusuario=7, usu_usuario="B")
