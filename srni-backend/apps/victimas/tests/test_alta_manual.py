"""
El alta manual en campo NO puede declarar "no incluido en el RUV".

De las 5.927.713 víctimas incluidas del corte, 1.884.872 (24 %) quedaron fuera del
padrón por falta de identidad en la .9 — no por su condición. Cuando el encuestador
da de alta a una de ellas, lo único verificado es que **no está en el padrón**.

Estos tests fijan esa distinción y el saneamiento del dominio que la acompañaba:
`fuente_origen` aceptaba cualquier cadena y en producción se estaban grabando
valores que no existen en el modelo.
"""
import pytest

from apps.victimas.models import Victima
from apps.victimas.serializers import RegistrarDesdeFuenteSerializer


PAYLOAD_BASE = {
    'tipo_documento': 'cc',
    'numero_documento': '1032456789',
    'primer_nombre': 'MARIA',
    'primer_apellido': 'PEREZ',
    'fecha_nacimiento': '1985-03-12',
    'genero': 'F',
}


def _validado(**extra):
    ser = RegistrarDesdeFuenteSerializer(data={**PAYLOAD_BASE, **extra})
    assert ser.is_valid(), ser.errors
    return ser.validated_data


# ---------------------------------------------------------------------------
# El estado nuevo existe en los dos dominios que recorre el dato
# ---------------------------------------------------------------------------

def test_no_verificado_es_un_estado_valido_de_victima():
    assert 'NO_VERIFICADO' in dict(Victima.ESTADO_RUV)


def test_no_verificado_tambien_existe_en_el_miembro_del_hogar():
    # El estado viaja de la víctima al hogar y de ahí a los reportes: si el
    # miembro no lo tiene, se degrada a NO_INCLUIDO al conformar el hogar.
    from apps.hogares.models import MiembroHogar

    assert 'NO_VERIFICADO' in dict(MiembroHogar.ESTADO_INCLUSION)


# ---------------------------------------------------------------------------
# Lo que manda la APK
# ---------------------------------------------------------------------------

def test_el_alta_manual_no_afirma_que_la_persona_este_fuera_del_ruv():
    datos = _validado(estado_ruv='NO_VERIFICADO', fuente_origen='MANUAL')
    assert datos['estado_ruv'] == 'NO_VERIFICADO'
    assert datos['fuente_origen'] == 'MANUAL'


def test_sin_estado_explicito_el_default_es_no_verificado():
    # Antes el default era NO_INCLUIDO: quien no mandaba el campo quedaba
    # declarado fuera del RUV sin que nadie lo hubiera comprobado.
    assert _validado()['estado_ruv'] == 'NO_VERIFICADO'


# ---------------------------------------------------------------------------
# Dominio: antes entraba cualquier cadena
# ---------------------------------------------------------------------------

def test_rechaza_un_estado_ruv_que_no_existe():
    ser = RegistrarDesdeFuenteSerializer(data={**PAYLOAD_BASE, 'estado_ruv': 'INVENTADO'})
    assert not ser.is_valid()
    assert 'estado_ruv' in ser.errors


def test_rechaza_una_fuente_de_origen_que_no_existe():
    ser = RegistrarDesdeFuenteSerializer(data={**PAYLOAD_BASE, 'fuente_origen': 'INVENTADA'})
    assert not ser.is_valid()
    assert 'fuente_origen' in ser.errors


@pytest.mark.parametrize('legacy, esperado', [
    # 'NO_INCLUIDA' nunca fue un choice del modelo y aun así se guardaba.
    ('NO_INCLUIDA', 'MANUAL'),
    # 'OFFLINE' era el canal, no el origen: ese dato salió del padrón.
    ('OFFLINE', 'RUV'),
    ('ENCUESTADOR', 'MANUAL'),
])
def test_traduce_las_fuentes_de_apks_ya_desplegadas_en_vez_de_rechazarlas(legacy, esperado):
    # Un 400 aquí le rompe el alta manual a los dispositivos que están en campo
    # con la versión anterior, así que se acepta y se traduce.
    assert _validado(fuente_origen=legacy)['fuente_origen'] == esperado


def test_las_fuentes_traducidas_caen_dentro_del_dominio_del_modelo():
    validas = {c for c, _ in Victima.FUENTE_ORIGEN}
    for destino in RegistrarDesdeFuenteSerializer._FUENTE_ORIGEN_LEGACY.values():
        assert destino in validas
