"""
Tests del reconocimiento de identidad entre filas que comparten documento.

Los casos no son inventados: cada uno es un grupo real del padrón de producción,
medido el 2-ago-2026. Si mañana alguien cambia el criterio de emparejamiento,
estos tests dicen qué se rompe en términos de personas, no de porcentajes.

Referencia de la medición (768.096 documentos repetidos sobre 4.928.725):
  92 %  una sola persona, nombre y fecha idénticos
   5 %  una sola persona, nombre o fecha con error de digitación
   3 %  personas distintas compartiendo documento
  + los valores de relleno: `99` (4.297 filas, 3.780 nombres), `0` (1.194 filas)
"""
import datetime

import pytest

from apps.victimas.identidad import (
    DOCUMENTOS_NO_IDENTIFICANTES,
    clasificar_grupo,
    documento_no_identificante,
    normalizar_nombre,
)


class FilaFalsa:
    """
    Lo mínimo que `clasificar_grupo` mira. Se usa un doble y no el modelo porque
    acá se prueba el criterio de identidad, no el ORM: sin base de datos, los
    casos se leen de un vistazo.
    """
    def __init__(self, nombre='', segundo='', ape1='', ape2='', nacimiento=None,
                 genero='', etnia='', discapacidad='', municipio=None,
                 cons=None, estado='INCLUIDO', ult_caracterizacion=None):
        self.primer_nombre = nombre
        self.segundo_nombre = segundo
        self.primer_apellido = ape1
        self.segundo_apellido = ape2
        self.fecha_nacimiento = nacimiento
        self.genero = genero
        self.pertenencia_etnica = etnia
        self.tipo_discapacidad = discapacidad
        self.municipio_residencia_id = municipio
        self.cons_persona = cons
        self.estado_ruv = estado
        self.fecha_ult_caracterizacion = ult_caracterizacion


NAC = datetime.date(1985, 6, 15)
OTRA = datetime.date(1977, 3, 4)


# ── Normalización ────────────────────────────────────────────────────────────

def test_la_normalizacion_ignora_tildes_mayusculas_y_puntuacion():
    assert normalizar_nombre('José', 'Andrés', 'Muñoz', 'Peña') == 'JOSE ANDRES MUNOZ PENA'
    assert normalizar_nombre('  maria  ', 'del-carmen', '', None) == 'MARIA DEL CARMEN'


def test_la_enie_se_pliega_a_ene():
    """
    Deliberado: la fuente pierde la ñ de forma inconsistente y la misma persona
    aparece MUÑOZ y MUNOZ. Separarlas daría un "ambiguo" falso.
    """
    assert normalizar_nombre('Muñoz') == normalizar_nombre('Munoz') == 'MUNOZ'


# ── Documentos de relleno ────────────────────────────────────────────────────

@pytest.mark.parametrize('numero', ['99', '0', '000', '9999999999', '1', '12345678'])
def test_los_valores_de_relleno_no_identifican(numero):
    assert documento_no_identificante(numero) is True


@pytest.mark.parametrize('numero', ['1030547250', '87552043', '1089290511'])
def test_un_documento_real_si_identifica(numero):
    assert documento_no_identificante(numero) is False


def test_un_numero_de_menos_de_cuatro_digitos_no_es_un_documento():
    """Ni cédula, ni tarjeta de identidad, ni registro civil tienen 3 dígitos."""
    assert documento_no_identificante('123') is True
    assert documento_no_identificante('0007') is True   # 7 tras quitar ceros
    assert documento_no_identificante('1234') is False


def test_la_lista_de_relleno_esta_normalizada():
    """Sin puntos ni guiones: se compara contra el número ya limpio."""
    assert all(v.isalnum() for v in DOCUMENTOS_NO_IDENTIFICANTES)


def test_documento_de_relleno_no_agrupa_a_nadie():
    """
    El caso `99`: 4.297 filas y 3.780 nombres distintos. Devolver a una de esas
    personas porque alguien buscó "99" sería entregar datos de un desconocido.
    """
    filas = [
        FilaFalsa(nombre='MARIA', ape1='GOMEZ', nacimiento=NAC),
        FilaFalsa(nombre='PEDRO', ape1='PEREZ', nacimiento=OTRA),
    ]
    v = clasificar_grupo(filas, numero_documento='99')
    assert v.clase == 'NO_IDENTIFICANTE'
    assert v.preferida is None      # no hay a quién elegir
    assert v.n_personas == 0


def test_muchos_nombres_distintos_delatan_un_comodin_no_declarado():
    """
    Un documento que no está en la lista pero se comporta igual: veinte nombres
    distintos bajo el mismo número no es una persona mal escrita.
    """
    filas = [FilaFalsa(nombre=f'NOMBRE{i}', ape1=f'APELLIDO{i}',
                       nacimiento=datetime.date(1980, 1, 1 + i % 28))
             for i in range(25)]
    v = clasificar_grupo(filas, numero_documento='4444555566')
    assert v.clase == 'NO_IDENTIFICANTE'


# ── El 92 %: una persona repetida por la fuente ──────────────────────────────

def test_la_misma_persona_repetida_es_una_sola_persona():
    """
    El caso real de `1089290511`: 505 filas, siempre ALBA TAPIA RODRIGUEZ, con
    504 `cons_persona` distintos. Es duplicación del Oracle de origen, no 505
    personas.
    """
    filas = [FilaFalsa(nombre='ALBA', ape1='TAPIA', ape2='RODRIGUEZ',
                       nacimiento=NAC, cons=1000 + i) for i in range(505)]
    v = clasificar_grupo(filas, numero_documento='1089290511')
    assert v.clase == 'DUPLICADO_FUENTE'
    assert v.n_personas == 1
    assert v.preferida is not None


def test_entre_duplicados_gana_la_fila_mas_completa():
    """Survivorship: la que más información trae, no la primera que salga."""
    pobre = FilaFalsa(nombre='ALBA', ape1='TAPIA', nacimiento=NAC)
    rica = FilaFalsa(nombre='ALBA', ape1='TAPIA', nacimiento=NAC,
                     genero='F', etnia='NINGUNA', municipio=5001, cons=7,
                     ult_caracterizacion=datetime.date(2026, 4, 1))
    for orden in ([pobre, rica], [rica, pobre]):
        v = clasificar_grupo(orden, numero_documento='1089290511')
        assert v.preferida is rica


# ── El 5 %: la misma persona con el nombre mal escrito ───────────────────────

def test_variante_ortografica_del_nombre_es_la_misma_persona():
    """ERIKA/ERICA con los mismos apellidos y la misma fecha: una persona."""
    filas = [
        FilaFalsa(nombre='ERIKA', ape1='JIMENEZ', ape2='CANO', nacimiento=NAC),
        FilaFalsa(nombre='ERICA', ape1='JIMENEZ', ape2='CANO', nacimiento=NAC, cons=9),
    ]
    v = clasificar_grupo(filas, numero_documento='1030547250')
    assert v.clase == 'VARIANTE_NOMBRE'
    assert v.n_personas == 1
    # Queda rastro de que hubo una decisión: no es DUPLICADO_FUENTE.
    assert v.preferida.cons_persona == 9      # la más completa


def test_el_apellido_mal_escrito_tambien_une():
    """SUESCUN ECHEVERRY / SUESCUN ECHEVERY: el apellido difiere, no une."""
    filas = [
        FilaFalsa(nombre='ANGEL', ape1='SUESCUN', ape2='ECHEVERRY', nacimiento=NAC),
        FilaFalsa(nombre='ANGEL', ape1='SUESCUN', ape2='ECHEVERY', nacimiento=NAC),
    ]
    v = clasificar_grupo(filas, numero_documento='1222135924')
    # Con apellidos distintos NO se unen: preferimos preguntar a fabricar una
    # persona. Queda como ambiguo y decide el encuestador.
    assert v.clase == 'AMBIGUO'
    assert v.n_personas == 2


# ── El 3 %: personas distintas ───────────────────────────────────────────────

def test_dos_personas_distintas_no_se_fusionan_y_no_se_elige_por_ellas():
    """
    Lo que el sistema NO puede hacer: mostrar una y callar la otra. Sin
    `preferida`, quien llama está obligado a preguntar.
    """
    filas = [
        FilaFalsa(nombre='CARLOS', ape1='HURTADO', ape2='RODRIGUEZ',
                  nacimiento=datetime.date(1990, 8, 28)),
        FilaFalsa(nombre='LUISA', ape1='GOMEZ', ape2='PEREZ',
                  nacimiento=datetime.date(1975, 4, 28)),
    ]
    v = clasificar_grupo(filas, numero_documento='1030547250')
    assert v.clase == 'AMBIGUO'
    assert v.n_personas == 2
    assert v.preferida is None


def test_dos_hermanos_con_el_mismo_documento_no_se_unen():
    """
    Mismos apellidos y distinta fecha de nacimiento. Unirlos por apellido sería
    fabricar una persona que no existe: la fecha tiene que coincidir también.
    """
    filas = [
        FilaFalsa(nombre='JUAN', ape1='TAICUS', ape2='TAPIA', nacimiento=NAC),
        FilaFalsa(nombre='KEYI', ape1='TAICUS', ape2='TAPIA', nacimiento=OTRA),
    ]
    v = clasificar_grupo(filas, numero_documento='1134529672')
    assert v.clase == 'AMBIGUO'
    assert v.n_personas == 2
    assert v.preferida is None


# ── Datos incompletos: donde el criterio se rompía ───────────────────────────
#
# `cargar_padron_oracle` escribe '' cuando Oracle trae NULL, así que apellidos y
# fechas vacíos son el caso corriente, no el raro.

def test_dos_personas_sin_apellidos_no_se_pisan():
    """
    El defecto más grave que tuvo este módulo: con apellidos vacíos las dos
    entraban al paso 3 bajo la misma llave ('', fecha) y la segunda
    **sobrescribía** a la primera. El grupo salía como "una sola persona" y el
    padrón offline borraba las filas de la otra.
    """
    filas = [
        FilaFalsa(nombre='MARIA', ape1='', ape2='', nacimiento=None),
        FilaFalsa(nombre='PEDRO', ape1='', ape2='', nacimiento=None),
    ]
    v = clasificar_grupo(filas, numero_documento='1030547250')
    assert v.clase == 'AMBIGUO'
    assert v.n_personas == 2
    assert v.preferida is None
    # y ninguna fila se perdió por el camino
    assert sum(len(p.filas) for p in v.personas) == 2


def test_apellidos_que_normalizan_a_vacio_tampoco_se_pisan():
    """'...' y '---' quedan en '' tras normalizar: mismo caso que el anterior."""
    filas = [
        FilaFalsa(nombre='MARIA', ape1='...', nacimiento=NAC),
        FilaFalsa(nombre='PEDRO', ape1='---', nacimiento=NAC),
    ]
    v = clasificar_grupo(filas, numero_documento='1030547250')
    assert v.clase == 'AMBIGUO'
    assert v.n_personas == 2


def test_tres_personas_sin_apellidos_sobreviven_las_tres():
    filas = [FilaFalsa(nombre=n, ape1='', nacimiento=None)
             for n in ('MARIA', 'PEDRO', 'JUAN')]
    v = clasificar_grupo(filas, numero_documento='1030547250')
    assert v.n_personas == 3


def test_sin_fecha_de_nacimiento_los_hermanos_no_se_unen():
    """
    La salvaguarda del paso 3 es "los apellidos Y la fecha coinciden". Con la
    fecha vacía en las dos filas, '' == '' la daba por cumplida y unía a dos
    hermanos: el padrón se quedaba con uno y la búsqueda no avisaba.
    """
    filas = [
        FilaFalsa(nombre='JUAN', ape1='TAICUS', ape2='TAPIA', nacimiento=''),
        FilaFalsa(nombre='KEYI', ape1='TAICUS', ape2='TAPIA', nacimiento=''),
    ]
    v = clasificar_grupo(filas, numero_documento='1134529672')
    assert v.clase == 'AMBIGUO'
    assert v.n_personas == 2


def test_dos_filas_sin_nombre_no_se_declaran_la_misma_persona():
    """Sin nombre no hay con qué afirmar identidad; se separan y se pregunta."""
    filas = [
        FilaFalsa(nombre='', ape1='', nacimiento=None, cons=1),
        FilaFalsa(nombre='', ape1='', nacimiento=None, cons=2),
    ]
    v = clasificar_grupo(filas, numero_documento='1030547250')
    assert v.clase == 'AMBIGUO'
    assert v.n_personas == 2


# ── Determinismo ─────────────────────────────────────────────────────────────

def test_el_veredicto_no_depende_del_orden_en_que_lleguen_las_filas():
    """
    El orden lo decide el plan de ejecución de PostgreSQL y puede cambiar entre
    corridas. Si el veredicto dependiera de él, dos generaciones del padrón
    darían resultados distintos sin que nadie tocara nada.
    """
    a = FilaFalsa(nombre='ERIKA', ape1='JIMENEZ', ape2='CANO', nacimiento=NAC, cons=1)
    b = FilaFalsa(nombre='ERICA', ape1='JIMENEZ', ape2='CANO', nacimiento=NAC, cons=2)
    c = FilaFalsa(nombre='ROSA', ape1='PEREZ', nacimiento=OTRA, cons=3)

    veredictos = [
        clasificar_grupo(list(orden), numero_documento='1030547250')
        for orden in ([a, b, c], [c, b, a], [b, c, a], [c, a, b])
    ]
    assert len({v.clase for v in veredictos}) == 1
    assert len({v.n_personas for v in veredictos}) == 1


def test_el_desempate_de_survivorship_es_estable_y_prefiere_lo_reciente():
    """
    A igual completitud gana la caracterizada más recientemente — que es lo que
    el docstring promete—, y a igualdad total decide el id, no la posición en la
    lista.
    """
    vieja = FilaFalsa(nombre='ALBA', ape1='TAPIA', nacimiento=NAC, cons=1,
                      ult_caracterizacion=datetime.date(2020, 1, 1))
    nueva = FilaFalsa(nombre='ALBA', ape1='TAPIA', nacimiento=NAC, cons=2,
                      ult_caracterizacion=datetime.date(2026, 4, 1))
    for orden in ([vieja, nueva], [nueva, vieja]):
        v = clasificar_grupo(orden, numero_documento='1089290511')
        assert v.preferida is nueva


def test_una_sola_fila_no_es_colision():
    v = clasificar_grupo([FilaFalsa(nombre='ANA', ape1='DIAZ', nacimiento=NAC)],
                         numero_documento='9990100001')
    assert v.clase == 'DUPLICADO_FUENTE'
    assert v.n_personas == 1


def test_grupo_vacio_no_revienta():
    v = clasificar_grupo([], numero_documento='1030547250')
    assert v.n_personas == 0
    assert v.preferida is None
