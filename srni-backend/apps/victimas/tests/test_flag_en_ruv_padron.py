"""
De dónde sale `FLAG_EN_RUV` del padrón descargable.

Lo que protege este archivo no es un campo, es la diferencia entre **preguntarle
al RUV** y **repetir lo que dijo un join roto**.

Hasta el 12-ago-2026 el flag salía de `Victima.estado_ruv`, y ese campo llegaba
del join por `CONS_PERONA` —que resultó ser un contador de filas, no un
identificador de persona—. Consecuencia: el padrón que se descargaban los
celulares marcaba ~5 millones de fichas como incluidas en el RUV copiando el
registro de otra persona, y el encuestador lo leía en pantalla como
"· Incluida en RUV" (`srni-mobile/app/(main)/busqueda.tsx`).

Ahora sale de cruzar el documento contra `PersonaUniverso`, el snapshot real del
RUV. Los dos primeros tests son el defecto viejo y su inverso: si alguien vuelve
a atar el flag a `estado_ruv`, fallan.
"""
import pytest

from apps.parametricas.models import TipoDocumento
from apps.victimas.models import PersonaUniverso, Victima
from apps.victimas.repository import DjangoVictimaRepository
from apps.victimas.repository.base import num_hash


@pytest.fixture
def tipo_cc(db):
    return TipoDocumento.objects.create(codigo='CC', nombre='Cédula', activo=True)


def _victima(tipo_cc, documento, **extra):
    return Victima.objects.create(
        tipo_documento=tipo_cc, numero_documento=documento,
        primer_nombre='ROSA', primer_apellido='BUSTOS',
        fecha_nacimiento='1975-03-14', genero='F', **extra)


def _en_universo(documento, cons=1):
    """Mete el documento en el snapshot del RUV, que es la fuente buena."""
    return PersonaUniverso.objects.create(
        cons_persona_universo=cons,
        numero_documento_hash_sin_tipo=num_hash(documento),
        corte='2026-08',
    )


def _resumen_de(documento_hash_sin_tipo):
    """Saca del padrón la fila de un documento."""
    for v in DjangoVictimaRepository().iterar_padron(batch_size=100):
        if num_hash(v.numero_documento) == documento_hash_sin_tipo:
            return v
    return None


# ── El defecto viejo, en las dos direcciones ────────────────────────────────

@pytest.mark.django_db
def test_un_INCLUIDO_que_no_esta_en_el_universo_NO_se_marca(tipo_cc):
    """
    El caso que rompió: `estado_ruv` decía `INCLUIDO` —heredado de otra persona—
    y el padrón lo repetía. Ahora no basta con que el campo lo diga.
    """
    _victima(tipo_cc, '1000000001', estado_ruv='INCLUIDO')

    resumen = _resumen_de(num_hash('1000000001'))

    assert resumen is not None
    assert not resumen.en_universo_ruv, (
        'el documento no está en el universo del RUV: el padrón no puede '
        'afirmar que la persona está incluida, diga lo que diga estado_ruv'
    )


@pytest.mark.django_db
def test_un_NO_VERIFICADO_que_SI_esta_en_el_universo_se_marca(tipo_cc):
    """
    El inverso, y es el que devuelve utilidad al flag: tras la migración 0021 los
    5,9 M quedaron en `NO_VERIFICADO`. Si el flag siguiera atado a ese campo, el
    padrón no marcaría a nadie. Lo que manda es el universo.
    """
    _victima(tipo_cc, '1000000002', estado_ruv='NO_VERIFICADO')
    _en_universo('1000000002')

    resumen = _resumen_de(num_hash('1000000002'))

    assert resumen is not None
    assert resumen.en_universo_ruv, (
        'el documento está en el universo del RUV: eso es lo que decide, '
        'no el estado_ruv de la fila'
    )


# ── La ruta que la APK usa HOY ──────────────────────────────────────────────

@pytest.mark.django_db
def test_la_precarga_de_jornada_cruza_igual_que_el_padron(tipo_cc):
    """
    La precarga es la ruta VIVA, y por poco se queda sin arreglar.

    El archivo del padrón todavía no se descarga al dispositivo —es la Fase B—,
    así que lo que hoy ve el encuestador en campo sale de
    `GET /api/victimas/precarga/`, que se arma con `listar_todas`. Ahí el
    `en_ruv` también salía de `estado_ruv`.

    Las dos rutas pasan por el mismo helper justo para que no puedan divergir:
    si cada una calculara lo suyo, el celular podría decir una cosa en la
    búsqueda y otra en la ficha de la misma persona.
    """
    _victima(tipo_cc, '1000000005', estado_ruv='INCLUIDO')       # NO está en el universo
    _victima(tipo_cc, '1000000006', estado_ruv='NO_VERIFICADO')  # SÍ está
    _en_universo('1000000006', cons=2)

    por_doc = {v.numero_documento: v
               for v in DjangoVictimaRepository().listar_todas(limite=10)}

    assert not por_doc['1000000005'].en_universo_ruv, (
        'un INCLUIDO heredado del join roto no puede llegar marcado a la jornada'
    )
    assert por_doc['1000000006'].en_universo_ruv, (
        'quien está en el universo del RUV debe llegar marcado, aunque la 0021 '
        'haya dejado su estado_ruv en NO_VERIFICADO'
    )


# ── Los bordes que harían marcar gente al azar ──────────────────────────────

@pytest.mark.django_db
def test_el_hash_vacio_no_cruza_con_nada(tipo_cc):
    """
    Sin el `exclude` del hash vacío, una víctima sin hash coincidiría con
    cualquier fila del universo sin hash y el padrón saldría marcando gente que
    nadie verificó. Es un `''  = ''` que devuelve verdadero.
    """
    v = _victima(tipo_cc, '1000000003', estado_ruv='NO_VERIFICADO')
    Victima.objects.filter(pk=v.pk).update(numero_documento_hash_sin_tipo='')
    PersonaUniverso.objects.create(
        cons_persona_universo=99, numero_documento_hash_sin_tipo='', corte='2026-08')

    resumenes = [r for r in DjangoVictimaRepository().iterar_padron(batch_size=100)]

    assert all(not r.en_universo_ruv for r in resumenes), (
        'un hash vacío no identifica a nadie y no puede cruzar con otro vacío'
    )


@pytest.mark.django_db
def test_por_defecto_el_resumen_no_afirma_nada(tipo_cc):
    """
    `en_universo_ruv` es `False` cuando nadie hizo el cruce. No preguntar no
    autoriza a afirmar: las demás consultas del repositorio no anotan el campo.
    """
    _victima(tipo_cc, '1000000004', estado_ruv='INCLUIDO')
    _en_universo('1000000004')

    # `buscar_por_documento` no cruza contra el universo, y no debe inventarlo.
    resultado = DjangoVictimaRepository().buscar_por_documento('CC', '1000000004')

    assert resultado.encontrado
    assert not resultado.victima.en_universo_ruv
