"""
El diagnóstico de "se caracterizó y la encuesta no aparece".

Nace de un caso real (2-jul-2026, Pandi/Cundinamarca): el enlace de víctimas
reporta que una ciudadana fue caracterizada y la consulta no muestra nada, y pide
recuperar la encuesta porque la persona vive en zona rural de difícil acceso y
volver cuesta una jornada entera.

Lo que estos tests protegen es **la distinción**, no el conteo: "no aparece"
tiene seis causas y solo UNA significa que el dato se perdió. Confundirlas manda a
alguien a la vereda otra vez, o —peor— da por perdida una encuesta que estaba
escrita.

`dictaminar` es pura a propósito: se prueba sin Oracle, que es justo lo que hace
falta cuando la base no responde (que fue el caso el día que se escribió esto).
"""
from apps.sincronizacion.management.commands.diagnosticar_encuesta_legacy import (
    dictaminar,
)


def _medido(**kw):
    """Un hogar medido, completo y sano; cada test cambia lo suyo."""
    base = dict(
        hog_codigo="999999-ABCDE", donde="GIC_HOGAR", estado="CERRADA",
        creado_por="ENC001", id_usuario=999999,
        miembros=3, encuestados=1, sin_espejo=0,
        en_trabajo=0, definitivas=120, capitulos=8,
        con_estado_ruv=3, con_hechos=3, territorio="completo",
        usuario_en_catalogo=True, id_usuario_en_catalogo=True,
    )
    base.update(kw)
    return dictaminar(base)


def test_un_hogar_completo_es_visible_para_los_reportes():
    d = _medido()
    assert d["veredicto"] == "COMPLETO"
    assert d["carencias"] == []


def test_el_caso_tipico_el_cierre_no_pudo_funcionar_por_capitulos():
    """
    La causa más común y la más engañosa: `SP_ACTUALIZAR_ESTADO_ENCUESTA` exige
    MÁS de 3 capítulos; con 3 o menos cae en un `ELSE NULL` y devuelve éxito sin
    cerrar. El aplicativo mostró "guardado" y el reporte no muestra nada.

    Lo que el veredicto tiene que decir alto y claro: **el dato está**.
    """
    d = _medido(estado="ACTIVA", en_trabajo=87, definitivas=0, capitulos=3)
    assert d["veredicto"] == "NO_CERRO_POR_CAPITULOS"
    assert "EL DATO ESTÁ" in d["explicacion"]
    assert "87" in d["explicacion"]


def test_con_capitulos_de_sobra_pero_sin_cerrar_es_otro_veredicto():
    """
    Mismo síntoma, causa distinta: acá el cierre PODÍA funcionar y no se ejecutó.
    Distinguirlo importa porque la reparación es otra —este se puede cerrar tal
    como está; el de arriba necesita capítulos primero—.
    """
    d = _medido(estado="ACTIVA", en_trabajo=87, definitivas=0, capitulos=9)
    assert d["veredicto"] == "ABIERTO_CON_DATOS"
    assert "EL DATO ESTÁ" in d["explicacion"]


def test_cerrado_sin_archivar_es_el_peor_estado():
    """
    Es lo que deja `CERRAR_ENCUESTA`: marca CERRADA sin mover las respuestas. El
    hogar figura terminado y para los reportes no existe. No se puede confundir
    con COMPLETO.
    """
    d = _medido(estado="CERRADA", en_trabajo=0, definitivas=0)
    assert d["veredicto"] == "CERRADO_SIN_ARCHIVAR"


def test_el_hogar_en_historico_no_esta_perdido():
    d = _medido(donde="GIC_HOGAR_HISTORICO", estado=None)
    assert d["veredicto"] == "EN_HISTORICO"
    assert "el dato está" in d["explicacion"].lower()


def test_sin_respuestas_en_ninguna_de_las_dos_tablas():
    d = _medido(estado="ACTIVA", en_trabajo=0, definitivas=0, capitulos=0)
    assert d["veredicto"] == "SIN_RESPUESTAS"


def test_migradoahistorico_cuenta_como_visible():
    """
    `GIC_VALIDAR_PERSONA_ENCUESTAD1` muestra ese estado como 'CERRADA'. Tratarlo
    como invisible marcaría como problema a hogares que están bien.
    """
    d = _medido(estado="MIGRADOAHISTORICO", en_trabajo=0, definitivas=120)
    assert d["veredicto"] == "COMPLETO"


# ── las carencias, que son ortogonales al veredicto ──────────────────────────

def test_un_hogar_completo_puede_tener_columnas_vacias_igual():
    """
    Cerrado y archivado —o sea, visible— pero sin validadores: sale en el reporte
    con ESTADO_RUV y los catorce hechos en blanco. Es exactamente lo que escribía
    SICAV antes del 3-ago, y es un problema distinto de "no aparece".
    """
    d = _medido(con_estado_ruv=0, con_hechos=0)
    assert d["veredicto"] == "COMPLETO"
    assert any("ESTADO_RUV" in c for c in d["carencias"])
    assert any("HECHO_VICTIMIZANTE" in c for c in d["carencias"])


def test_la_persona_sin_columna_espejo_se_reporta_como_invisible():
    """
    Los reportes y la consulta cruzan por `R_NUMERODOC`, no por `PER_NUMERODOC`.
    Una fila con el espejo vacío existe y no la encuentra nadie — el dato está y
    la consulta miente.
    """
    d = _medido(sin_espejo=2, miembros=3)
    assert any("R_NUMERODOC" in c and "2 de 3" in c for c in d["carencias"])


def test_sin_encuestado_el_reporte_no_muestra_jefe_de_hogar():
    d = _medido(encuestados=0)
    assert any("JEFE_HOGAR" in c for c in d["carencias"])


def test_el_territorio_incompleto_se_distingue_del_ausente():
    assert any("incompleto" in c for c in _medido(territorio="incompleto")["carencias"])
    assert any("sin fila" in c for c in _medido(territorio="sin fila")["carencias"])


def test_un_hogar_perfecto_es_invisible_si_su_encuestador_no_esta_en_el_catalogo():
    """
    La séptima causa, y la más traicionera: `SP_REPORTE_MIEMBROSXCODIGO` arma
    "mis encuestas" con un **INNER JOIN** contra GIC_USUARIO. Sin fila del
    usuario, el hogar no sale del listado por más que esté cerrado y archivado —
    el veredicto sigue siendo COMPLETO, y por eso la carencia tiene que verse.

    No es marginal: 1.077.712 hogares (97,7 %) están en esa situación.
    """
    d = _medido(usuario_en_catalogo=False, creado_por="JGUARINH")
    assert d["veredicto"] == "COMPLETO"
    assert any("JGUARINH" in c and "INNER JOIN" in c for c in d["carencias"])


def test_el_id_de_usuario_que_no_cruza_se_reporta_aparte():
    """
    Son dos comprobaciones distintas: la cadena la usa 'mis encuestas', el id lo
    usan los reportes de productividad. Un hogar puede fallar una y no la otra.
    """
    d = _medido(id_usuario_en_catalogo=False, id_usuario=999999)
    assert any("999999" in c and "productividad" in c for c in d["carencias"])
    assert not any("INNER JOIN" in c for c in d["carencias"])


def test_un_dict_parcial_no_revienta():
    """
    La herramienta se usa cuando algo ya salió mal. Que ella misma lance un
    KeyError en ese momento es el peor comportamiento posible.
    """
    d = dictaminar({"hog_codigo": "X", "donde": "GIC_HOGAR", "estado": "ACTIVA"})
    assert d["veredicto"] == "SIN_RESPUESTAS"
    assert isinstance(d["carencias"], list)
