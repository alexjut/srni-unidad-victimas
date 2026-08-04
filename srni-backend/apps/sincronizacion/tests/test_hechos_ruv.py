"""
Lectura de hechos desde el RUV.

Todo con un cursor falso: estos tests no tocan Oracle ni la red. Lo que se
prueba es la traducción y las decisiones de seguridad del lector, que es donde
se pierde el dato en silencio.
"""

import datetime

import pytest

from apps.sincronizacion.oracle import hechos_ruv as H


class _CursorFalso:
    """Devuelve las filas que se le den y recuerda con qué SQL lo llamaron."""

    def __init__(self, filas):
        self._filas = filas
        self.sql = None
        self.params = None

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return self._filas


def _fila(tipo, *, id_ruv=1, fecha=None, dpto=None, mpio=None, persona=777):
    """(ID, PARAM_TIPOHECHO, FECHASINIESTRO, ID_DEPARTAMENTO, ID_MUNICIPIO, ID_PERSONA)"""
    return (id_ruv, tipo, fecha, dpto, mpio, persona)


# ── La traducción, que es lo que importa ─────────────────────────────────────

def test_el_desplazamiento_del_ruv_es_el_5_y_llega_como_HV01():
    """
    El 5 del RUV es 'Desplazamiento Forzado' y en SICAV es HV01. Tomar el número
    tal cual lo convertiría en HV05, que es 'Desaparición forzada' — otro hecho,
    y encima el desplazamiento es el 51,8 % de los registros.
    """
    cur = _CursorFalso([_fila(5)])
    lectura = H.leer_hechos(cur, "1070752540")

    assert [h.codigo_sicav for h in lectura.hechos] == ["HV01"]
    assert lectura.hechos[0].codigo_sicav != "HV05"


def test_el_censo_masivo_no_se_confunde_con_confinamiento():
    """
    El 13 del RUV es 'Censo Masivo' (434.178 registros). El 13 del legacy es
    'Otros' y el HV13 de SICAV es 'Confinamiento'. Mapearlo a HV13 para que
    aterrizara en 'Otros' habría marcado como CONFINADAS a esas 434.178
    personas dentro de SICAV.
    """
    cur = _CursorFalso([_fila(13)])
    lectura = H.leer_hechos(cur, "123")

    assert lectura.hechos[0].codigo_sicav == "HV16"
    assert lectura.hechos[0].codigo_sicav != "HV13"


def test_el_otro_del_ruv_no_es_perdida_de_bienes():
    """El 12 del RUV es 'Otro'; el 12 del legacy es 'Pérdida de bienes'."""
    cur = _CursorFalso([_fila(12)])
    lectura = H.leer_hechos(cur, "123")

    assert lectura.hechos[0].codigo_sicav == "HV15"
    assert lectura.hechos[0].codigo_sicav != "HV12"


def test_los_trece_hechos_del_ruv_se_traducen_sin_perder_ninguno():
    cur = _CursorFalso([_fila(t, id_ruv=t) for t in range(1, 14)])
    lectura = H.leer_hechos(cur, "123")

    assert len(lectura.hechos) == 13
    assert len({h.codigo_sicav for h in lectura.hechos}) == 13


# ── Lo que se niega a adivinar ───────────────────────────────────────────────

def test_un_documento_ambiguo_no_devuelve_hechos_de_nadie():
    """
    Dos personas del RUV con el mismo número: mezclar sus hechos le atribuiría a
    una lo que sufrió la otra. Se informa la ambigüedad y no se elige.
    """
    cur = _CursorFalso([_fila(5, persona=111), _fila(2, persona=222)])
    lectura = H.leer_hechos(cur, "1")

    assert lectura.es_ambigua
    assert lectura.personas_ruv == 2
    assert lectura.hechos == ()


def test_una_sola_persona_no_es_ambigua_aunque_tenga_varios_hechos():
    """Una víctima puede tener varios hechos —y el mismo hecho dos veces—."""
    cur = _CursorFalso([_fila(5, id_ruv=1), _fila(5, id_ruv=2), _fila(2, id_ruv=3)])
    lectura = H.leer_hechos(cur, "123")

    assert not lectura.es_ambigua
    assert len(lectura.hechos) == 3
    assert [h.codigo_sicav for h in lectura.hechos] == ["HV01", "HV01", "HV03"]


def test_un_hecho_fuera_del_catalogo_avisa_en_vez_de_descartarse():
    """
    Si el RUV amplía su catálogo, queremos enterarnos acá y no que la persona
    pierda el hecho sin que nadie lo note.
    """
    cur = _CursorFalso([_fila(99)])
    with pytest.raises(H.HechoRuvDesconocido):
        H.leer_hechos(cur, "123")


def test_sin_estricto_el_hecho_desconocido_se_salta_pero_los_demas_llegan():
    cur = _CursorFalso([_fila(5, id_ruv=1), _fila(99, id_ruv=2)])
    lectura = H.leer_hechos(cur, "123", estricto=False)

    assert [h.codigo_sicav for h in lectura.hechos] == ["HV01"]


def test_un_documento_vacio_no_consulta_la_base():
    cur = _CursorFalso([_fila(5)])
    lectura = H.leer_hechos(cur, "   ")

    assert cur.sql is None          # no se ejecutó nada
    assert not lectura.encontrada
    assert lectura.hechos == ()


# ── Detalles que igual rompen el dato ────────────────────────────────────────

def test_la_fecha_llega_como_date_y_la_ausencia_se_conserva():
    cur = _CursorFalso([
        _fila(5, id_ruv=1, fecha=datetime.datetime(2015, 3, 12, 14, 30)),
        _fila(2, id_ruv=2, fecha=None),
    ])
    lectura = H.leer_hechos(cur, "123")

    assert lectura.hechos[0].fecha == datetime.date(2015, 3, 12)
    assert lectura.hechos[1].fecha is None


def test_el_lugar_se_devuelve_crudo_y_no_se_traduce_a_municipio():
    """
    Los ids del RUV son surrogate, igual que los del legacy (TOLIMA=30,
    ALVARADO=32). Hasta verificar el crosswalk NO se traducen: se devuelven tal
    cual para que nadie los confunda con códigos DANE.
    """
    cur = _CursorFalso([_fila(5, dpto=30, mpio=32)])
    hecho = H.leer_hechos(cur, "123").hechos[0]

    assert (hecho.id_departamento, hecho.id_municipio) == (30, 32)
    assert hecho.tiene_lugar


def test_la_consulta_filtra_los_inactivos_y_va_por_el_dblink():
    """
    Sin `ACTIVO = 1` se recuperan hechos que el propio RUV ya dio de baja, y sin
    el dblink la consulta buscaría las tablas en el esquema local, que no las
    tiene.
    """
    cur = _CursorFalso([])
    H.leer_hechos(cur, "123")

    assert "CONSULTARUV" in cur.sql
    assert cur.sql.count("@CONSULTARUV") == 3      # las tres tablas del cruce
    assert "NVL(r.ACTIVO, 1) = 1" in cur.sql
    assert "NVL(s.ACTIVO, 1) = 1" in cur.sql
    # El documento va como bind, no interpolado: es dato de origen externo.
    assert cur.params == {"documento": "123"}
