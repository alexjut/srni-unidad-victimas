"""
Tests de la homologación de la fuente Oracle.

Es la parte de la carga que tiene criterio, así que se prueba sola: que el comando
corra sin errores no dice nada sobre si un `"CONTRASEÑA"` acabó siendo una cédula.

Los casos de entrada NO son inventados — son los 59 valores reales de `PER_TIPODOC`
con más de 100 usos, medidos en producción el 2026-07-29.
"""
import pytest

from apps.victimas.homologacion import (
    homologar_discapacidad,
    homologar_etnia,
    homologar_genero,
    homologar_tipo_documento,
)


# ── tipo de documento: el mismo concepto escrito de siete formas ─────────────
@pytest.mark.parametrize("valor", [
    "Cedula de Ciudadanía / Contraseña",   # 2.937.805 usos
    "CC",                                  # 389.940
    "CÉDULA DE CIUDADANÍA",                # 364.690
    "CEDULA CIUDADANIA",                   # 71.121
    "CÉDULA DE CIUDADANÍA / CONTRASEÑA",   # 59.106
    "CONTRASEÑA",                          # 387
    "CONTRASEÃ‘A",                         # 319 — mojibake real en la base
])
def test_todas_las_formas_de_cedula_dan_CC(valor):
    assert homologar_tipo_documento(valor) == "CC"


@pytest.mark.parametrize("valor,esperado", [
    ("Tarjeta de Identidad", "TI"), ("TI", "TI"), ("TARJETA IDENTIDAD", "TI"),
    ("TI2", "TI"),
    ("Registro Civil", "RC"), ("REGISTRO CIVIL DE NACIMIENTO", "RC"),
    ("RCN", "RC"), ("NUIP", "RC"), ("REGISTRO CIVIL / NUIP", "RC"),
    ("CÉDULA DE EXTRANJERÍA", "CE"), ("CEDULA EXTRANJERIA", "CE"), ("CE2", "CE"),
    ("PASAPORTE", "PA"), ("NIT", "NIT"),
    ("PERMISO POR PROTECCION TEMPORAL", "PE"),
])
def test_los_demas_tipos(valor, esperado):
    assert homologar_tipo_documento(valor) == esperado


def test_la_cedula_de_extranjeria_no_se_confunde_con_la_de_ciudadania():
    """
    Las dos contienen 'cedula'. El orden de los patrones importa: extranjería se
    evalúa antes. Si se invierte, 3.400 extranjeros pasan a ser colombianos.
    """
    assert homologar_tipo_documento("CÉDULA DE EXTRANJERÍA") == "CE"
    assert homologar_tipo_documento("CÉDULA DE CIUDADANÍA") == "CC"


@pytest.mark.parametrize("valor", [
    "", None, "   ",
    "Sin Informacion", "SIN DATO ASIGNADO", "SIN INFORMACION", "SIN DATOS",
    "NINGUNO", "OTRO", "Otro", "OTR",
    "NO RESPONDE", "NO SABE (NS)-(NO RECUERDA EL NÚMERO)",
    "INDOCUMENTADO", "IND", "NI",
])
def test_lo_que_declara_no_saber_va_a_None(valor):
    """
    None es un resultado legítimo: la persona se carga sin tipo y se encuentra por el
    índice de respaldo. Homologar 'OTRO' o 'INDOCUMENTADO' a CC sería afirmar un
    documento que nadie verificó.
    """
    assert homologar_tipo_documento(valor) is None


def test_los_ids_numericos_se_resuelven_contra_el_catalogo_no_a_ojo():
    """
    'PER_TIPODOC' guarda a veces el RES_IDRESPUESTA de Oracle ('93' = 100.983 usos,
    '3854' = 146.537). Se traducen con el catálogo real, no adivinando.
    """
    catalogo = {93: "Cédula de ciudadanía / Contraseña",
                3854: "Cédula de ciudadanía / Contraseña",
                2: "Tarjeta de Identidad"}
    assert homologar_tipo_documento("93", catalogo) == "CC"
    assert homologar_tipo_documento("3854", catalogo) == "CC"
    assert homologar_tipo_documento("2", catalogo) == "TI"


def test_un_id_numerico_sin_catalogo_no_se_adivina():
    assert homologar_tipo_documento("93") is None


# ── etnia ────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("valor,esperado", [
    ("Ninguna", "NINGUNA"),
    ("Negro(a) o Afrocolombiano(a)", "AFROCOLOMBIANO"),
    ("Indigena", "INDIGENA"),
    ("Gitano(a) ROM", "ROM"),
    ("Palenquero", "PALENQUERO"),
    # el valor viene TRUNCADO en el corte — se casa por prefijo
    ("Raizal del Archipielago de San Andres y Prov", "RAIZAL"),
])
def test_etnia(valor, esperado):
    assert homologar_etnia(valor) == esperado


@pytest.mark.parametrize("valor", [None, "", "None"])
def test_sin_dato_de_etnia_no_es_NINGUNA(valor):
    """
    2.133.894 personas vienen con NULL. 'No sabemos su pertenencia étnica' no es lo
    mismo que 'declaró no pertenecer a ningún grupo' (6.877.003): colapsarlas borraría
    de las estadísticas a dos millones de personas sin dato.
    """
    assert homologar_etnia(valor) == ""


# ── género ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("valor,esperado", [
    ("Mujer", "F"), ("Hombre", "M"), ("No Informa", "ND"),
    (None, "ND"), ("None", "ND"), ("", "ND"),
])
def test_genero(valor, esperado):
    assert homologar_genero(valor) == esperado


def test_LGBTI_no_se_convierte_en_no_binario():
    """
    1.684 personas. LGBTI describe orientación o identidad de forma agregada; asumir
    que son no binarias les atribuiría una identidad que no declararon. ND dice la
    verdad: el dato que tenemos no responde a esta pregunta.
    """
    assert homologar_genero("LGBTI") == "ND"


# ── discapacidad ─────────────────────────────────────────────────────────────
def test_discapacidad():
    assert homologar_discapacidad("1") is True
    assert homologar_discapacidad(1) is True
    assert homologar_discapacidad(None) is False
    assert homologar_discapacidad("") is False


# ── el catálogo REAL, sin mock ───────────────────────────────────────────────
@pytest.mark.django_db
def test_el_catalogo_de_tipos_de_oracle_se_lee_de_verdad():
    """
    Este test existe por un fallo real: la función iteraba `cat["preguntas"]` como si
    fuera una lista cuando es un DICT indexado, así que reventaba con
    `'int' object is not subscriptable`. **Los tests no lo detectaron porque la
    mockeaban**, y solo apareció al correr la carga contra Oracle.

    Moraleja incorporada: si una función lee un archivo del repo, hay que ejercerla
    de verdad al menos una vez — mockearla siempre es no probarla nunca.
    """
    from apps.victimas.homologacion import cargar_catalogo_tipodoc_oracle

    catalogo = cargar_catalogo_tipodoc_oracle()
    assert catalogo, "la pregunta 30 debe existir en el catálogo volcado de Oracle"
    # 93 es la cédula canónica (29.338 usos medidos; ver el caso 3a.13)
    assert homologar_tipo_documento("93", catalogo) == "CC"
    assert homologar_tipo_documento("95", catalogo) == "TI"
    assert homologar_tipo_documento("94", catalogo) == "CE"
    assert homologar_tipo_documento("96", catalogo) == "RC"


# ── estado en el RUV — catálogo RUV.TBESTADO_VAL, confirmado 31-jul ──────────
@pytest.mark.parametrize("codigo,esperado", [
    (1, "INCLUIDO"),
    (2, "NO_INCLUIDO"),
    (3, "EN_PROCESO"),      # "En Valoración"
    (4, "EXCLUIDO"),
    (5, "EN_PROCESO"),      # "No Valorado - Devuelto"
    (6, "EN_PROCESO"),      # "Afectado - No Valorado"
    (7, "NO_INCLUIDO"),     # "No Afectado - No Valorado"
    ("1", "INCLUIDO"),
])
def test_estado_ruv_segun_el_catalogo_oficial(codigo, esperado):
    from apps.victimas.homologacion import homologar_estado_ruv
    assert homologar_estado_ruv(codigo) == esperado


def test_el_3_es_en_valoracion_y_no_excluido():
    """
    Regresión de una confusión real: circularon dos versiones verbales opuestas
    —3=en valoración vs 3=excluido—. El catálogo `RUV.TBESTADO_VAL` zanjó que el 3 es
    'En Valoración' y el 4 'Excluido'. Invertirlos marcaría como EXCLUIDAS a 430.518
    personas que solo están esperando su valoración.
    """
    from apps.victimas.homologacion import homologar_estado_ruv
    assert homologar_estado_ruv(3) == "EN_PROCESO"
    assert homologar_estado_ruv(4) == "EXCLUIDO"


@pytest.mark.parametrize("valor", [None, "", "x", 99, 0])
def test_un_estado_desconocido_no_se_inventa(valor):
    from apps.victimas.homologacion import homologar_estado_ruv
    assert homologar_estado_ruv(valor) == ""


# ── quién va al padrón ───────────────────────────────────────────────────────
def test_solo_las_incluidas_van_al_padron():
    """
    MI_PERSONAS tiene 49.529.433 personas: el registro completo del modelo integrado,
    no solo víctimas. El padrón descargable no puede llevarlas todas.
    """
    from apps.victimas.homologacion import es_victima
    assert es_victima(1) is True
    for otro in (2, 3, 4, 5, 6, 7, None, ""):
        assert es_victima(otro) is False


# ── vigencia: la norma de recaracterizar cada 2 años ─────────────────────────
def test_una_caracterizacion_de_hace_mas_de_dos_anios_esta_vencida():
    import datetime
    from apps.victimas.homologacion import debe_recaracterizarse
    hoy = datetime.date(2026, 7, 31)
    assert debe_recaracterizarse(datetime.date(2024, 7, 30), hoy) is True    # 2 años y 1 día
    assert debe_recaracterizarse(datetime.date(2022, 5, 1), hoy) is True     # 4 años


def test_una_caracterizacion_reciente_sigue_vigente():
    import datetime
    from apps.victimas.homologacion import debe_recaracterizarse
    hoy = datetime.date(2026, 7, 31)
    assert debe_recaracterizarse(datetime.date(2026, 1, 15), hoy) is False
    assert debe_recaracterizarse(datetime.date(2024, 8, 1), hoy) is False    # falta 1 día


def test_sin_fecha_hay_que_caracterizar():
    """
    Nunca caracterizada —o sin registro— es justamente a quien hay que caracterizar.
    Devolver False dejaría fuera a quien más lo necesita.
    """
    from apps.victimas.homologacion import debe_recaracterizarse
    assert debe_recaracterizarse(None) is True
    assert debe_recaracterizarse("") is True


def test_acepta_datetime_ademas_de_date():
    import datetime
    from apps.victimas.homologacion import debe_recaracterizarse
    hoy = datetime.date(2026, 7, 31)
    assert debe_recaracterizarse(datetime.datetime(2020, 1, 1, 10, 30), hoy) is True
