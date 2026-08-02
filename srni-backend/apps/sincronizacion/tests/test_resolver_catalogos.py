"""
Tests de ResolverCatalogos (Etapa A) — SIN Oracle.

Verifican la resolución contra los CROSSWALKS REALES de `catalogos.py` (valores
leídos de prod RNIENTREVISTA, 2026-07-15): dado un valor SICAV, devuelve el código
Oracle real; ante un valor sin mapeo, LANZA error claro en modo estricto y un
marcador ‹PEND:...› en dry-run. Nunca falla en silencio ni inventa un default.
"""
import pytest

from apps.sincronizacion.oracle import catalogos
from apps.sincronizacion.oracle.mapeo import (
    CampoOrigenFaltante, MapeoDesconocido, MapeoPendienteNegocio, ResolverCatalogos,
)


def _r(estricto=True, **over):
    """Resolver con los crosswalks REALES de catalogos.py (sin inyectar)."""
    return ResolverCatalogos(estricto=estricto, **over)


# ── catálogo 2 — tipo de caracterización (constante HOGAR) ───────────────────
def test_tipo_caracterizacion_es_hogar():
    assert _r().resolver_tipo_caracterizacion("TERRITORIAL") == 2
    assert _r().resolver_tipo_caracterizacion() == catalogos.TIPO_CARACTERIZACION_HOGAR


# ── catálogo 3 — tipo de documento (valores reales GIC_TIPODOC) ──────────────
@pytest.mark.parametrize("codigo,esperado", [
    ("CC", 1), ("TI", 2), ("CE", 3), ("RC", 4), ("PA", 7), ("NIT", 9),
])
def test_tdoc_real(codigo, esperado):
    assert _r().resolver_tdoc(codigo) == esperado


class _TD:
    def __init__(self, codigo): self.codigo = codigo


def test_tdoc_por_instancia():
    assert _r().resolver_tdoc(_TD("CC")) == 1


@pytest.mark.parametrize("codigo,esperado", [("PE", 13), ("NES", 14)])
def test_tdoc_sin_fila_propia_usa_la_opcion_honesta(codigo, esperado):
    """
    3a.3 (resuelto 2026-07-28). Ni el PEP ni el NES tienen fila propia en
    GIC_TIPODOC: el catálogo se creó en 2014 y el PEP es de 2017. Se mapean a la
    opción existente que NO miente — 'Otro' y 'Indocumentado' — en vez de quedar
    sin resolver y abortar la escritura de esa persona.
    """
    assert _r().resolver_tdoc(codigo) == esperado


def test_pep_no_se_hace_pasar_por_cedula_de_extranjeria():
    """
    Regresión de la decisión: 'Cédula de Extranjería' (3) era el candidato
    tentador, pero un permiso migratorio no es una cédula. Mapearlo así
    afirmaría un documento que la persona no tiene.
    """
    assert _r().resolver_tdoc("PE") != _r().resolver_tdoc("CE")


def test_tdoc_sin_documento_lanza():
    with pytest.raises(MapeoDesconocido):
        _r().resolver_tdoc(None)


def test_tdoc_desconocido_dry_run_marcador():
    """Un código que no está en el mapa sigue sin inventarse."""
    assert _r(estricto=False).resolver_tdoc("XX") == "‹PEND:TIPO_DOCUMENTO(XX)›"


# ── catálogo 4 — parentesco (valores reales GIC_PARENTESCOGENEALOGICO) ───────
@pytest.mark.parametrize("codigo,esperado", [
    ("CONYUGE", 4), ("HIJO_A", 3), ("YERNO_NUERA", 8), ("NIETO_A", 5),
    ("PADRE_MADRE", 2), ("HERMANO_A", 7), ("OTRO_PARIENTE", 9), ("NO_PARIENTE", 10),
])
def test_relac_real(codigo, esperado):
    assert _r().resolver_relac(codigo) == esperado


def test_relac_vacio_lanza():
    with pytest.raises(MapeoDesconocido):
        _r().resolver_relac("")


# ── RELAC del miembro según rol: el autorizado es el jefe de hogar (Oracle 1) ─
class _MiembroRol:
    def __init__(self, es_autorizado, parentesco):
        self.es_autorizado = es_autorizado
        self.parentesco = parentesco


def test_relac_de_miembro_autorizado_es_jefe_aunque_parentesco_vacio():
    # El autorizado (es_autorizado=True) es el jefe: SICAV le deja parentesco='' y
    # Oracle tiene 1='Jefe de hogar'. Resuelve a 1 en vez de fallar por vacío.
    assert _r().resolver_relac_de_miembro(_MiembroRol(True, "")) == 1


def test_relac_de_miembro_normal_cruza_por_parentesco():
    assert _r().resolver_relac_de_miembro(_MiembroRol(False, "CONYUGE")) == 4
    assert _r().resolver_relac_de_miembro(_MiembroRol(False, "HIJO_A")) == 3


# ── extras decididos CON DATO: escriben NULL / 1, nunca marcador ni inventado ─
def test_extras_persona_escriben_null():
    # ID_DECLAR/ID_PERS_FUENTE/ID_SINIESTRO → NULL: SICAV no origina esos enlaces
    # internos de Oracle y la estructura los confirma nullable.
    for extra in ("id_declar", "id_pers_fuente", "id_siniestro"):
        assert _r().resolver_extra_persona(extra) is None
        assert _r(estricto=False).resolver_extra_persona(extra) is None


def test_idpermi_ya_no_va_en_null():
    """
    IDPERMI (PER_IDMODELOINT) SÍ se escribe, y es un cambio deliberado del 2-ago:
    es el puente de la persona con el Modelo Integrado. En NULL quedaba fuera del
    cruce con el RUV para siempre, porque el job que lo resuelve busca `= 0` y el
    DEFAULT 0 de la columna no aplica (el INSERT del procedure es posicional).

    Ver `test_dominios_oracle.py` para el detalle y el caso del padrón.
    """
    assert _r().resolver_extra_persona("idpermi") == 0
    assert _r(estricto=False).resolver_extra_persona("idpermi") == 0


def test_pregunta_padre_null_y_pbandera_uno():
    assert _r().resolver_pregunta_padre() is None
    assert _r().resolver_pbandera() == 1


# ── catálogo 4b — tipo de víctima → NULL (campo en desuso en Oracle) ─────────
class _MiembroSinCampo:
    """Como el MiembroHogar REAL: no define `tipo_victima`."""
    parentesco = "HIJO_A"


def test_t_victima_es_null_por_desuso_en_oracle():
    # Medido en prod (2026-07-24): PER_TIPOVICTIMA es NULL en 7.755.818 de ~7,76 M
    # personas (26 con valor). Campo en DESUSO ⇒ SICAV escribe NULL (decisión Javier,
    # delegada por Oscar). No falla ni marca pendiente: NULL es el valor correcto, tal
    # cual el 99,9997 % de Oracle. Antes fallaba porque el modelo SICAV no traía el campo.
    assert _r().resolver_t_victima(_MiembroSinCampo()) is None
    assert _r(estricto=False).resolver_t_victima(_MiembroSinCampo()) is None
    assert _r().resolver_t_victima(object()) is None   # ni siquiera mira el miembro


def test_campo_faltante_es_mapeo_desconocido():
    # Subclase: los `except MapeoDesconocido` existentes lo siguen atrapando.
    assert issubclass(CampoOrigenFaltante, MapeoDesconocido)


# ── catálogo 1 — usuario/perfil de servicio (pendiente de negocio) ───────────
def test_usuario_servicio_pendiente_lanza():
    with pytest.raises(MapeoPendienteNegocio):
        _r().id_usuario_servicio()


def test_usuario_servicio_configurado_ok():
    assert _r(usuario_servicio_id=9001).id_usuario_servicio() == 9001


def test_usuario_servicio_dry_run_marcador():
    assert _r(estricto=False).id_usuario_servicio() == "‹PEND:USUARIO_SERVICIO_ID(negocio)›"


# ── catálogo 5 — territorio (cruce por nombre contra el crosswalk REAL) ──────
class _Nombrado:
    def __init__(self, nombre): self.nombre = nombre


def _sesion(dt="DIRECCION TERRITORIAL CENTRAL", depto="TOLIMA",
            punto="JORNADAS DE ATENCION Y/O FERIAS DE SERVICIO", municipio="ALVARADO"):
    """Sesión mínima con solo lo que mira resolver_territorio (los 4 nombres)."""
    class _S:
        direccion_territorial = _Nombrado(dt) if dt is not None else None
        departamento_atencion = _Nombrado(depto) if depto is not None else None
        punto_atencion = _Nombrado(punto) if punto is not None else None
        municipio_atencion = _Nombrado(municipio) if municipio is not None else None
    return _S()


def test_territorio_resuelve_los_cuatro_ids_reales():
    # Fila real del volcado: DT CENTRAL / TOLIMA / JORNADAS / ALVARADO.
    t = _r().resolver_territorio(_sesion())
    assert t == {"id_dt": 7, "id_depto": 30, "id_pt": 13, "id_ma": 32}


def test_territorio_devuelve_cuatro_claves_no_tres():
    # IDDEPTOATEN es columna propia de GIC_N_RELACION_DT_PUNTO: si falta, el
    # territorio queda incompleto y los reportes se rompen (bug histórico).
    assert set(_r().resolver_territorio(_sesion())) == {"id_dt", "id_depto", "id_pt", "id_ma"}


def test_territorio_ids_son_surrogate_no_dane():
    # TOLIMA=30 (DANE 73) y ALVARADO=32 (DANE 73026): confirma que NO son DANE.
    t = _r().resolver_territorio(_sesion())
    assert (t["id_depto"], t["id_ma"]) == (30, 32)


def test_territorio_normaliza_acentos_y_espacios():
    # SICAV acentúa ('ATENCIÓN') y Oracle no; Oracle además trae espacios de sobra.
    t = _r().resolver_territorio(
        _sesion(dt="  dirección territorial central ",
                punto="Jornadas de Atención y/o Ferias de Servicio")
    )
    assert t["id_dt"] == 7


def test_territorio_cruza_enie():
    # NARIÑO existe con Ñ en ambos lados; el plegado de diacríticos es simétrico.
    # Fila real del volcado: DT NARIÑO(15) / NARIÑO(23) / IPIALES(220) / IPIALES(446).
    t = _r().resolver_territorio(
        _sesion(dt="DIRECCION TERRITORIAL NARIÑO", depto="NARIÑO",
                punto="IPIALES", municipio="IPIALES")
    )
    assert t == {"id_dt": 15, "id_depto": 23, "id_pt": 220, "id_ma": 446}


def test_territorio_desambigua_municipio_repetido():
    # BUENAVISTA existe con 4 ids distintos; el contexto (DT+depto+punto) decide.
    # Si el cruce fuera por columna suelta, esto devolvería un id al azar.
    t = _r().resolver_territorio(
        _sesion(dt="DIRECCION TERRITORIAL SUCRE", depto="SUCRE",
                punto="JORNADAS DE ATENCION Y/O FERIAS DE SERVICIO",
                municipio="BUENAVISTA")
    )
    otro = _r().resolver_territorio(
        _sesion(dt="DIRECCION TERRITORIAL CORDOBA", depto="CORDOBA",
                punto="JORNADAS DE ATENCION Y/O FERIAS DE SERVICIO",
                municipio="BUENAVISTA")
    )
    assert t["id_ma"] != otro["id_ma"]


def test_territorio_punto_ambiguo_se_desambigua_por_dt():
    # 'JORNADAS...' tiene 39 ids en Oracle (uno por DT): el id depende de la DT.
    central = _r().resolver_territorio(_sesion())
    antioquia = _r().resolver_territorio(
        _sesion(dt="DIRECCION TERRITORIAL ANTIOQUIA", depto="ANTIOQUIA",
                municipio="MEDELLIN")
    )
    assert central["id_pt"] != antioquia["id_pt"]


@pytest.mark.parametrize("kwargs,fragmento", [
    ({"dt": "DIRECCION TERRITORIAL INEXISTENTE"}, "Dirección Territorial"),
    ({"depto": "ATLANTICO"}, "Departamento de atención"),   # no cuelga de DT CENTRAL
    ({"punto": "PUNTO QUE NO EXISTE"}, "Punto de atención"),
    ({"municipio": "MUNICIPIO QUE NO EXISTE"}, "Municipio de atención"),
])
def test_territorio_error_dice_en_que_nivel_fallo(kwargs, fragmento):
    with pytest.raises(MapeoDesconocido) as exc:
        _r().resolver_territorio(_sesion(**kwargs))
    assert fragmento in str(exc.value)
    assert "Opciones Oracle" in str(exc.value)  # el error es accionable


def test_territorio_sesion_sin_punto_lanza_claro():
    with pytest.raises(MapeoDesconocido) as exc:
        _r().resolver_territorio(_sesion(punto=None))
    assert "punto_atencion" in str(exc.value)


def test_territorio_placeholder_sicav_sin_equivalente_lanza():
    # El catálogo de puntos de SICAV es placeholder: 'Centro Regional Medellín' no
    # existe en Oracle. Debe fallar claro, no aproximar.
    with pytest.raises(MapeoDesconocido):
        _r().resolver_territorio(
            _sesion(dt="DIRECCION TERRITORIAL ANTIOQUIA", depto="ANTIOQUIA",
                    punto="Centro Regional Medellín", municipio="MEDELLIN")
        )


def test_territorio_dry_run_marca_los_cuatro():
    t = _r(estricto=False).resolver_territorio(_sesion(dt="NO EXISTE"))
    assert set(t) == {"id_dt", "id_depto", "id_pt", "id_ma"}
    assert all(str(v).startswith("‹PEND:TERRITORIO") for v in t.values())


# ── catálogo 6 — instrumento/respuestas (sin dato Oracle → pendiente) ────────
class _Instrumento:
    codigo = "TERRITORIAL"


def test_ins_idinstrumento_resuelto_es_constante():
    # Ya NO es pendiente: Query B mostró que GIC_INSTRUMENTO tiene una sola fila
    # (1='CARACTERIZACION'). Oracle no separa por instrumento como SICAV (8) ⇒ no hay
    # crosswalk, es constante. Los tests detallados están en test_resolver_respuestas.
    assert _r().resolver_ins_idinstrumento(_Instrumento()) == 1
    assert _r(estricto=False).resolver_ins_idinstrumento(_Instrumento()) == 1


def test_tipo_pregunta_se_copia_del_catalogo_de_oracle():
    # Antes esto era pendiente de negocio "sin dominio conocido". Ya no: el DISTINCT
    # en prod (2026-07-16) dio {GE, IN} — el mismo dominio que PRE_TIPOPREGUNTA. No es
    # el tipo de widget, es el NIVEL, y Oracle ya lo tiene ⇒ se copia, no se mapea.
    class _P:
        tipo = "RADIO"          # el widget de SICAV ya no pinta nada aquí
        id_preg = 5             # 'Zona de residencia' → GE (hogar) en el volcado real
        codigo_externo = "Z6"
    assert _r().resolver_tipo_pregunta(_P()) == "GE"


def test_tipo_pregunta_sin_id_preg_no_se_inventa():
    # Sin el puente a Oracle no se sabe el nivel. Falla en vez de suponer.
    class _P:
        tipo = "RADIO"
        id_preg = None
        codigo_externo = "SIN_PUENTE"
    with pytest.raises(MapeoPendienteNegocio):
        _r().resolver_tipo_pregunta(_P())
