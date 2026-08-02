"""
Lo que se escribe en GIC_PERSONA tiene que ser una persona, no una fila vacía.

De ahí salen los reportes de la Unidad. Si el nombre y el documento van en
blanco, el hogar existe en el legacy pero no sirve para nada.

El defecto: `MiembroHogar.nombre_completo` y `.numero_documento` son —según su
propio `help_text`— "datos básicos cifrados para miembros NO en el RNI". El
miembro que viene del padrón los tiene VACÍOS: su identidad está en `Victima`. El
mapeo leía solo los campos del miembro, así que un hogar real —el caso normal—
escribía personas sin nombre y sin documento.

No se vio en el piloto del 28-jul porque ese hogar se armó con datos sintéticos
dados de alta a mano, que sí llenan los campos del miembro.
"""
import datetime
import itertools

import pytest

from apps.sincronizacion.oracle.mapeo import identidad_de_miembro

pytestmark = pytest.mark.django_db


@pytest.fixture
def catalogo(db):
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    muni = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                    departamento=depto)
    return {'tipo': tipo, 'municipio': muni}


def _victima(catalogo, **extra):
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    campos = dict(
        tipo_documento=catalogo['tipo'], numero_documento='1030547250',
        numero_documento_hash=doc_hash('CC', '1030547250'),
        primer_nombre='MARIA', segundo_nombre='LUISA',
        primer_apellido='GOMEZ', segundo_apellido='RENDON',
        fecha_nacimiento='1985-06-15',
        genero='F', estado_ruv='INCLUIDO', habilitado_para_caracterizacion=True,
        pertenencia_etnica='NINGUNA', discapacidad=False,
        municipio_residencia=catalogo['municipio'],
    )
    campos.update(extra)
    return Victima.objects.create(**campos)


_SECUENCIA = itertools.count(1)


def _miembro(catalogo, victima=None, **extra):
    from apps.autenticacion.models import Perfil, Usuario
    from apps.hogares.models import Hogar, MiembroHogar

    n = next(_SECUENCIA)
    perfil = Perfil.objects.create(codigo=f'P{n}', nombre='Enc',
                                   puede_caracterizar=True, activo=True)
    usuario = Usuario.objects.create_user(
        codigo_usuario=f'U{n}', password='SrniTest2026!',
        nombre_completo='U', email=f'u{n}@srni.dev',
        perfil=perfil, activo=True)
    autorizado = victima or _victima(catalogo)
    hogar = Hogar.objects.create(autorizado=autorizado, creado_por=usuario,
                                 municipio=catalogo['municipio'])
    return MiembroHogar.objects.create(hogar=hogar, victima=victima, **extra)


# ── el caso normal: el miembro viene del padrón ──────────────────────────────

def test_un_miembro_del_padron_lleva_su_nombre_y_documento(catalogo):
    """El caso que se escribía vacío."""
    victima = _victima(catalogo)
    miembro = _miembro(catalogo, victima=victima)

    ident = identidad_de_miembro(miembro)

    assert ident['pnombre'] == 'MARIA'
    assert ident['snombre'] == 'LUISA'
    assert ident['papellido'] == 'GOMEZ'
    assert ident['sapellido'] == 'RENDON'
    assert ident['numero'] == '1030547250'
    assert ident['tipo_documento'] == catalogo['tipo']


def test_la_fecha_de_nacimiento_llega_como_fecha_no_como_texto(catalogo):
    """
    `Victima.fecha_nacimiento` es un campo cifrado: al descifrarlo vuelve como
    TEXTO. Pasarle esa cadena al procedure de Oracle es un error de tipo — o peor,
    una fecha mal interpretada que nadie revisa.
    """
    miembro = _miembro(catalogo, victima=_victima(catalogo))
    assert identidad_de_miembro(miembro)['fecha_nacimiento'] == datetime.date(1985, 6, 15)


def test_una_fecha_ilegible_no_rompe_la_escritura(catalogo):
    miembro = _miembro(catalogo, victima=_victima(catalogo, fecha_nacimiento='sin dato'))
    assert identidad_de_miembro(miembro)['fecha_nacimiento'] is None


# ── el otro caso: alta manual, sin víctima en el padrón ──────────────────────

def test_un_miembro_dado_de_alta_a_mano_usa_sus_propios_datos(catalogo):
    """Lo que ya funcionaba tiene que seguir funcionando."""
    miembro = _miembro(catalogo, victima=None,
                       nombre_completo='PEDRO JOSE PEREZ RAMIREZ',
                       numero_documento='99887766',
                       tipo_documento=catalogo['tipo'],
                       fecha_nacimiento=datetime.date(1990, 3, 2))

    ident = identidad_de_miembro(miembro)
    assert ident['pnombre'] == 'PEDRO'
    assert ident['numero'] == '99887766'
    assert ident['fecha_nacimiento'] == datetime.date(1990, 3, 2)


def test_la_victima_manda_sobre_los_campos_del_miembro(catalogo):
    """
    Si por lo que sea vienen los dos, gana el padrón: es la fuente de verdad de
    identidad, y lo capturado en el miembro puede ser un apunte de campo.
    """
    miembro = _miembro(catalogo, victima=_victima(catalogo),
                       nombre_completo='OTRO NOMBRE DISTINTO',
                       numero_documento='00000000')
    ident = identidad_de_miembro(miembro)
    assert ident['pnombre'] == 'MARIA'
    assert ident['numero'] == '1030547250'


# ── la garantía de fondo ─────────────────────────────────────────────────────

def test_ningun_miembro_con_identidad_conocida_se_escribe_en_blanco(catalogo):
    """
    La afirmación que importa para los reportes: si SICAV sabe quién es la
    persona, GIC_PERSONA no puede recibirla vacía.
    """
    casos = [
        _miembro(catalogo, victima=_victima(catalogo)),
        _miembro(catalogo, victima=None, nombre_completo='ANA DIAZ',
                 numero_documento='555444', tipo_documento=catalogo['tipo']),
    ]
    for miembro in casos:
        ident = identidad_de_miembro(miembro)
        assert ident['pnombre'], 'se habría escrito una persona sin nombre'
        assert ident['numero'], 'se habría escrito una persona sin documento'
