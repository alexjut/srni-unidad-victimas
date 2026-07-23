"""
Tests del resolver de respuestas (SICAV → GIC_N_RESPUESTAS) — SIN Oracle.

Lo que se protege aquí es lo que costó descubrir:
- el puente correcto es `Pregunta.id_preg == PRE_IDPREGUNTA` (verificado con datos),
- `id_resp_vivanto` NO es `RES_IDRESPUESTA` (refutado, 0/14) — hay test para que no
  vuelva a colarse,
- y ningún id se inventa: si el texto no cruza exacto, es curaduría manual, porque
  el procedure se traga el NO_DATA_FOUND y un id errado no daría error.
"""
import pytest

from apps.sincronizacion.oracle import catalogos
from apps.sincronizacion.oracle.mapeo import (
    CampoOrigenFaltante, MapeoPendienteNegocio, ResolverCatalogos,
)


def _r(estricto=True):
    return ResolverCatalogos(estricto=estricto)


class _Opcion:
    def __init__(self, valor, etiqueta, id_resp_vivanto=None):
        self.valor, self.etiqueta = valor, etiqueta
        self.id_resp_vivanto = id_resp_vivanto


class _Opciones:
    """Stub del related manager: solo necesita .filter(valor=...).first()."""
    def __init__(self, *opciones): self._o = list(opciones)
    def filter(self, valor): return _Opciones(*[o for o in self._o if o.valor == valor])
    def first(self): return self._o[0] if self._o else None


class _Pregunta:
    def __init__(self, id_preg, codigo_externo, *opciones, tipo="RADIO"):
        self.id_preg, self.codigo_externo, self.tipo = id_preg, codigo_externo, tipo
        self.opciones = _Opciones(*opciones)


class _Respuesta:
    def __init__(self, pregunta, valor):
        self.pregunta, self.valor = pregunta, valor


# Filas REALES del volcado: pregunta 5 'Zona de residencia' → 8 Cabecera / 9 Centro
# poblado / 10 Rural; pregunta 24 'Sexo' → 68 Hombre / 69 Mujer.
def _zona(valor="1"):
    p = _Pregunta(5, "Z6",
                  _Opcion("1", "Cabecera municipal (donde está la alcaldía)", 4572),
                  _Opcion("2", "Centro poblado, corregimiento, inspección de policía, caserío", 4573))
    return _Respuesta(p, valor)


def _sexo(valor="2"):
    p = _Pregunta(24, "SEXO", _Opcion("1", "Hombre", 4598), _Opcion("2", "Mujer", 4599))
    return _Respuesta(p, valor)


def _catalogo_parcial(monkeypatch):
    """
    Instala (vía monkeypatch) un catálogo sintético en modo TRUNCADO.

    El archivo real se regeneró a COMPLETO (902 preguntas / `_meta.completo=True`), así
    que ya no dispara el camino de "volcado parcial" del resolver. Ese camino sigue
    siendo código vivo y protector —una ausencia en un volcado incompleto NO prueba que
    la pregunta no exista en Oracle—, de modo que se ejercita aquí con un `_meta` parcial
    reconstruido, sin tocar el JSON real. Devuelve el dict del catálogo instalado.
    """
    cat = dict(catalogos.cargar_respuestas())
    meta = {**cat["_meta"], "completo": False, "truncado": {
        "filas_exportadas": 200, "temas_cubiertos": [1, 2],
        "ultima_pregunta": 1158, "ultimo_ixp_orden": 41,
    }}
    meta["cobertura"] = catalogos._describir_cobertura(meta)  # ejercita también su rama truncada
    cat["_meta"] = meta
    monkeypatch.setattr(catalogos, "cargar_respuestas", lambda: cat)
    return cat


# ── instrumento: constante, ya no es pendiente ──────────────────────────────
def test_ins_idinstrumento_es_constante():
    # Query B: GIC_INSTRUMENTO tiene UNA fila (1='CARACTERIZACION'). Oracle no separa
    # por instrumento como SICAV: no hay crosswalk que resolver.
    assert _r().resolver_ins_idinstrumento() == 1
    assert _r().resolver_ins_idinstrumento(object()) == 1  # el instrumento se ignora


# ── el puente correcto: id_preg → PRE_IDPREGUNTA, opción por texto ─────────
def test_resuelve_por_id_preg_y_texto_de_opcion():
    # Zona/Cabecera → 8 en Oracle (no 4572, que es el id_resp_vivanto de SICAV).
    assert _r().resolver_res_idrespuesta(_zona("1")) == 8


def test_rxp_tipopregunta_se_copia_de_oracle_no_se_mapea():
    """
    RXP_TIPOPREGUNTA sale del catálogo de Oracle, no del `tipo` de SICAV.

    Dominio confirmado en prod (2026-07-16): `SELECT DISTINCT RXP_TIPOPREGUNTA` → {GE, IN},
    los mismos valores de PRE_TIPOPREGUNTA. Como Oracle ya sabe el nivel de cada
    pregunta, no hay nada que traducir: se copia. Mandar 'RADIO' (el widget de SICAV)
    era el dominio equivocado.
    """
    r = _r()
    # Pregunta 5 (Zona de residencia) es de hogar; 24 (Sexo), de persona.
    assert r.resolver_tipo_pregunta(_zona().pregunta) == "GE"
    assert r.resolver_tipo_pregunta(_sexo().pregunta) == "IN"


def test_rxp_tipopregunta_ignora_el_tipo_de_sicav():
    # El widget de SICAV no influye: aunque la pregunta diga RADIO, manda Oracle.
    p = _Pregunta(24, "SEXO", _Opcion("2", "Mujer"), tipo="RADIO")
    assert _r().resolver_tipo_pregunta(p) == "IN"
    assert _r().resolver_tipo_pregunta(p) != "RADIO"


def test_rxp_tipopregunta_fuera_del_volcado_no_se_inventa(monkeypatch):
    # Con el volcado COMPLETO, una pregunta ausente sí concluye algo: no existe en el
    # instrumento de Oracle ⇒ no tiene nivel que copiar (pendiente de negocio). No se
    # inventa un GE/IN.
    p = _Pregunta(999999, "NO_EXISTE", _Opcion("1", "Sí"))
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_tipo_pregunta(p)
    assert "RXP_TIPOPREGUNTA" in str(exc.value)
    assert "no existe en el instrumento de Oracle" in str(exc.value)

    # El camino de modo-truncado (volcado parcial) sigue vivo y dice lo contrario: una
    # ausencia NO prueba inexistencia. Se ejercita con un catálogo parcial sintético.
    _catalogo_parcial(monkeypatch)
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_tipo_pregunta(p)
    assert "NO quiere decir que no exista" in str(exc.value)


def test_rxp_tipopregunta_fuera_de_dominio_para(monkeypatch):
    # El dominio {GE, IN} se midió en prod un día concreto. Si aparece un tercer valor,
    # el catálogo cambió y la suposición caducó: parar es más barato que escribir mal.
    cat = dict(catalogos.cargar_respuestas())
    preguntas = dict(cat["preguntas"])
    preguntas[5] = {**preguntas[5], "pre_tipopregunta": "XX"}
    cat["preguntas"] = preguntas
    monkeypatch.setattr(catalogos, "cargar_respuestas", lambda: cat)
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_tipo_pregunta(_zona().pregunta)
    assert "fuera del dominio" in str(exc.value)


def test_pre_tipopregunta_es_el_nivel_no_el_tipo():
    """
    PRE_TIPOPREGUNTA vale GE/IN y, pese al nombre, es el NIVEL de la pregunta.

    Evidencia: cruzando las 62 preguntas del volcado contra `Pregunta.nivel` de SICAV
    —que se llenó aparte, leyendo el manual— concuerdan 61 de 63 (GE→HOGAR 18,
    IN→PERSONA 43). Dos fuentes independientes no coinciden así por azar.

    Ojo con lo que este test NO dice: que RXP_TIPOPREGUNTA (el bind del procedure)
    comparta ese dominio. Se parecen en el nombre, y ya nos mordió una vez confiar en
    eso (id_resp_vivanto). Falta un SELECT DISTINCT contra prod para cerrarlo.
    """
    cat = catalogos.cargar_respuestas()
    assert {p["pre_tipopregunta"] for p in cat["preguntas"].values()} == {"GE", "IN"}
    assert cat["preguntas"][5]["pre_tipopregunta"] == "GE"    # Zona de residencia: hogar
    assert cat["preguntas"][24]["pre_tipopregunta"] == "IN"   # Sexo: persona
    assert catalogos.TIPOPREGUNTA_NIVEL == {"GE": "HOGAR", "IN": "PERSONA"}


def test_la_pregunta_desambigua_el_texto_repetido():
    # 'Cabecera municipal…' existe con id 8 (pregunta 5, Zona de residencia) y 3809
    # (pregunta 1164, Zona de correspondencia). El id_preg decide cuál.
    cat = catalogos.cargar_respuestas()
    en_5 = [x["res_idrespuesta"] for x in cat["preguntas"][5]["respuestas"]
            if x["_texto"] == catalogos.normalizar_nombre("Cabecera municipal (donde está la alcaldía)")]
    en_1164 = [x["res_idrespuesta"] for x in cat["preguntas"][1164]["respuestas"]
               if x["_texto"] == catalogos.normalizar_nombre("Cabecera municipal (donde está la alcaldía)")]
    assert en_5 == [8] and en_1164 == [3809]


def test_no_usa_id_resp_vivanto():
    """
    Regresión del veredicto: `id_resp_vivanto` NO es `RES_IDRESPUESTA` (0/14).

    SICAV dice que Mujer es 4599; Oracle dice 69. Si alguien "optimizara" el resolver
    devolviendo id_resp_vivanto, esto lo caza. Escribir 4599 no daría error —el
    procedure traga el NO_DATA_FOUND— simplemente no escribiría.
    """
    resuelto = _r(estricto=False).resolver_res_idrespuesta(_sexo("2"))
    assert "4599" not in str(resuelto)
    assert "69" in str(resuelto)


@pytest.mark.parametrize("etiqueta_sicav,oracle", [
    ("Mujer", 69), ("Hombre", 68),
])
def test_ids_reales_del_volcado(etiqueta_sicav, oracle):
    cat = catalogos.cargar_respuestas()
    textos = {x["_texto"]: x["res_idrespuesta"] for x in cat["preguntas"][24]["respuestas"]}
    assert textos[catalogos.normalizar_nombre(etiqueta_sicav)] == oracle


# ── lo que no cruza: error claro, nunca aproximación ────────────────────────
def test_texto_que_no_cruza_es_curaduria_no_fuzzy():
    # 'Rural disperso' de SICAV vs 'Parte rural disperso (vereda, campo)' de Oracle:
    # parecidos, no iguales. Elegir "el más parecido" escribiría la opción equivocada
    # en silencio ⇒ debe fallar.
    # OJO: se usa 'Rural disperso' (sin paréntesis) A PROPÓSITO. La variante
    # 'Rural disperso (vereda)' SÍ está hoy en el crosswalk curado (→10), así que ya no
    # sirve para probar el fallo. Que la forma casi idéntica y semánticamente obvia
    # SIGA fallando por no tener clave EXACTA en el crosswalk es justo la disciplina
    # anti-fuzzy que este test protege: el resolver no adivina, solo respeta curaduría.
    p = _Pregunta(5, "Z6", _Opcion("3", "Rural disperso"))
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_Respuesta(p, "3"))
    assert "CURADURÍA MANUAL" in str(exc.value)
    assert "Parte rural disperso" in str(exc.value)  # muestra las candidatas reales


def test_el_desempate_manda_al_manual_antes_que_a_negocio():
    """
    Criterio de Javier: ante cruce inexacto o ambigüedad, primero el MANUAL OFICIAL;
    Oscar solo si el manual no resuelve. Y nunca fuzzy matching.

    Se usa 'Rural disperso' (no curada) y no 'Rural disperso (vereda)' (que sí está en
    el crosswalk → 10): el desempate al manual solo aplica cuando NO hay curaduría.
    """
    p = _Pregunta(5, "Z6", _Opcion("3", "Rural disperso"))
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_Respuesta(p, "3"))
    msg = str(exc.value)
    assert "MANUAL OFICIAL" in msg and "11-MU" in msg
    assert "fuzzy" in msg.lower()          # deja explícito lo que NO se hace
    # El manual va antes que Oscar en el texto del error (es la escalera, no una lista).
    assert msg.index("MANUAL OFICIAL") < msg.index("Oscar")


# ── crosswalk CURADO: precedencia sobre el fallo de cruce por texto ──────────
# Estos ejercitan el wireo del crosswalk (catalogos.cargar_crosswalk_opciones +
# los dos puntos de consulta en resolver_res_idrespuesta) contra el catálogo y el
# crosswalk REALES. La disciplina que protegen: el crosswalk es autoridad curada
# con clave EXACTA; resuelve lo que su curador fijó y NADA más (nunca fuzzy).
def test_crosswalk_resuelve_otro_cuando_el_texto_no_cruza():
    """
    (a) pre_id=2, opción SICAV 'Otro' → res_id=5 ('Otro, ¿cuál?' en Oracle).

    SICAV dice 'Otro' y Oracle 'Otro, ¿cuál?': el texto NO cruza y, sin crosswalk,
    esto caía en curaduría manual. La curaduría (autoridad verificada) lo resuelve.
    """
    cat = catalogos.cargar_respuestas()
    objetivo = catalogos.normalizar_nombre("Otro")
    # Premisa: 'Otro' de verdad NO cruza por texto con ninguna opción de la pregunta 2…
    assert not any(o["_texto"] == objetivo for o in cat["preguntas"][2]["respuestas"])
    # …y el crosswalk sí la tiene curada a 5.
    assert catalogos.cargar_crosswalk_opciones()[(2, objetivo)] == 5
    p = _Pregunta(2, "Z3", _Opcion("1", "Otro"))
    assert _r().resolver_res_idrespuesta(_Respuesta(p, "1")) == 5


def test_crosswalk_resuelve_wording_que_sigue_divergiendo():
    """
    (b) pre_id=1164, 'Rural disperso (vereda)' → res_id=3811.

    Caso de crosswalk que SOBREVIVE tras alinear el instrumento al manual (2026-07-23):
    SICAV ya dice 'Rural disperso (vereda)' (redacción del manual), pero Oracle guarda
    'Parte rural disperso (vereda, campo)'. El texto sigue SIN cruzar directo —nada de
    fuzzy— y el crosswalk curado, única autoridad, lo resuelve.

    (Los typos como 'Combares'→'Combates' ya se corrigieron en el fixture; ahora cruzan
    DIRECTO con Oracle y su entrada de crosswalk se quitó por redundante en la
    reconciliación — ver crosswalk_opciones.json `_meta.reconciliado`.)
    """
    objetivo = catalogos.normalizar_nombre("Rural disperso (vereda)")
    cat = catalogos.cargar_respuestas()
    # Premisa: no cruza por texto directo con ninguna opción de la pregunta 1164…
    assert not any(o["_texto"] == objetivo for o in cat["preguntas"][1164]["respuestas"])
    # …y el crosswalk sí la tiene curada a 3811.
    assert catalogos.cargar_crosswalk_opciones()[(1164, objetivo)] == 3811
    p = _Pregunta(1164, "Z16", _Opcion("6", "Rural disperso (vereda)"))
    assert _r().resolver_res_idrespuesta(_Respuesta(p, "6")) == 3811


def test_crosswalk_es_exacto_no_traga_lo_no_curado():
    """
    (c) Regresión del wireo: el crosswalk es un mapa EXACTO, no un colador. Una opción
    que no cruza por texto y NO tiene clave curada sigue fallando IGUAL que antes del
    crosswalk (curaduría manual): no se 'resuelve' por aproximación.
    """
    objetivo = catalogos.normalizar_nombre("Zona rural dispersa")
    assert (5, objetivo) not in catalogos.cargar_crosswalk_opciones()   # premisa explícita
    p = _Pregunta(5, "Z6", _Opcion("9", "Zona rural dispersa"))
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_Respuesta(p, "9"))
    msg = str(exc.value)
    assert "no cruza por texto" in msg and "CURADURÍA MANUAL" in msg


def test_crosswalk_convierte_un_fallo_previo_en_resolucion():
    """
    Documenta el cambio de comportamiento con un caso real: 'Rural disperso (vereda)'
    (SICAV) vs 'Parte rural disperso (vereda, campo)' (Oracle) ANTES fallaba como
    curaduría manual; ahora, por estar curada, resuelve limpio a res_id=10. Es el
    contrapunto exacto de test_texto_que_no_cruza_es_curaduria_no_fuzzy (que usa la
    forma sin paréntesis, NO curada, y por eso sigue fallando).
    """
    objetivo = catalogos.normalizar_nombre("Rural disperso (vereda)")
    assert catalogos.cargar_crosswalk_opciones()[(5, objetivo)] == 10
    p = _Pregunta(5, "Z6", _Opcion("3", "Rural disperso (vereda)"))
    assert _r().resolver_res_idrespuesta(_Respuesta(p, "3")) == 10


def _tipo_doc():
    # Pregunta 30: 'Cédula de ciudadanía / Contraseña' aparece con 4 ids
    # (93, 3852, 3853, 3854) aunque el manual 11-MU (B6) la declara UNA vez.
    p = _Pregunta(30, "TIPO_DOC", _Opcion("CC", "Cédula de ciudadanía / Contraseña"))
    return _Respuesta(p, "CC")


def test_opcion_ambigua_falla_y_no_elige_ninguna():
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_tipo_doc())
    msg = str(exc.value)
    assert "93" in msg and "3852" in msg and "3853" in msg and "3854" in msg
    assert "MANUAL OFICIAL" in msg          # peldaño 3 antes que Oscar
    assert msg.index("MANUAL OFICIAL") < msg.index("Oscar")


def test_los_4_ids_de_cedula_son_todos_escribibles():
    """
    REFUTACIÓN, con el export del 2026-07-16: el filtro de escribibilidad NO
    desambigua la pregunta 30.

    La hipótesis era que las 3 filas de más de 'Cédula de ciudadanía / Contraseña'
    serían huérfanas, y que al descartarlas quedaría 93 sola. La columna ESCRIBIBLE
    dice que no: los 4 ids están marcados SI. Este test fija el dato para que nadie
    (yo el primero) vuelva a "resolver" el caso apoyándose en la teoría bonita.
    Consecuencia: el caso sube al manual (que declara la opción UNA vez ⇒ confirma
    que sobran ids, pero no dice cuál surrogate es el vigente) y de ahí a Oscar.
    """
    cat = catalogos.cargar_respuestas()
    cedula = [r for r in cat["preguntas"][30]["respuestas"]
              if r["_texto"] == catalogos.normalizar_nombre("Cédula de ciudadanía / Contraseña")]
    assert sorted(r["res_idrespuesta"] for r in cedula) == [93, 3852, 3853, 3854]
    assert all(r["escribible"] for r in cedula)
    assert not any(r["res_idrespuesta"] in cat["huerfanas"] for r in cedula)


def test_las_huerfanas_son_opciones_que_el_manual_no_declara():
    """
    Qué es una huérfana, verificado — y NO es lo que parecía a primera vista.

    Iba camino de escalarse como "defecto activo de producción": la pregunta 28
    (parentesco) tiene 7 opciones sin fila en GIC_N_INSTRUMENTOXRESP —Nieto(a),
    Abuelo(a), Sobrino(a)…— y el procedure las tragaría en silencio, así que parecía
    que un hogar extenso no podía registrar el parentesco de sus miembros.

    El manual dice que no. 11-MU pág. 56 lista **exactamente 6 opciones** para esa
    pregunta (Jefe(a), Cónyuge, Hijo(a), Padre/madre, Hermano(a), Otro pariente del
    jefe) — justo las 6 que Oracle sí deja escribir. Y SICAV ofrece esas mismas 6.
    Los tres lados coinciden; las 7 restantes son filas muertas del catálogo de Oracle.
    Comprobado 10/10: SICAV no ofrece NINGUNA de las 10 huérfanas del volcado.

    ⇒ La escribibilidad **implementa el manual**. No hay defecto, no hay pérdida de
    datos y no hay nada que escalar. Este test fija el hecho para que la alarma no
    resucite: si mañana alguien vuelve a leer "7 parentescos huérfanos" y le parece
    grave, aquí está por qué no lo es.
    """
    cat = catalogos.cargar_respuestas()
    p28 = cat["preguntas"][28]["respuestas"]
    escribibles = {r["res_respuesta"] for r in p28 if r["escribible"]}
    huerfanas = {r["res_respuesta"] for r in p28 if not r["escribible"]}
    # Las 6 escribibles == las 6 del manual (11-MU pág. 56).
    assert escribibles == {
        "Jefe(a)", "Cónyuge o Compañera(o) (Personas mayores de 14 años)",
        "Hijo(a) - Hijastro(a)", "Padre o madre - Padrastro o madrastra",
        "Hermano(a) - Hermanastro(a)", "Otro pariente del jefe",
    }
    # Las 7 huérfanas son las que el manual NO declara.
    assert huerfanas == {"Nieto(a)", "Yerno o nuera", "Abuelo(a)", "Suegro(a)",
                         "Tío(a)", "Sobrino(a)", "Otros no parientes"}


def test_una_huerfana_acusa_a_sicav_no_a_oracle():
    """
    El guard sigue fallando ruidosamente, pero apuntando a donde toca.

    Como SICAV no ofrece las huérfanas, esto "no puede pasar". Si pasa, el hallazgo
    no es "Oracle no sabe guardarlo": es que **el instrumento de SICAV se desvió del
    manual** y ofrece una opción que oficialmente no existe. El mensaje debe mandar a
    revisar SICAV, no a abrirle un pendiente a Oscar sobre Oracle.
    """
    p = _Pregunta(28, "PARENTESCO", _Opcion("N", "Nieto(a)"))
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_Respuesta(p, "N"))
    msg = str(exc.value)
    assert "HUÉRFANAS" in msg and "83" in msg     # nombra el id
    assert "NO_DATA_FOUND" in msg                 # y por qué fallaría en silencio
    assert "SICAV se desvió del manual" in msg    # el dedo apunta a SICAV
    assert "no en Oracle" in msg


def test_si_todas_las_candidatas_son_huerfanas_falla_claro(monkeypatch):
    cat = dict(catalogos.cargar_respuestas())
    cat["_meta"] = {**cat["_meta"], "escribibilidad_verificada": True}
    cat["huerfanas"] = frozenset({93, 3852, 3853, 3854})
    monkeypatch.setattr(catalogos, "cargar_respuestas", lambda: cat)
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_tipo_doc())
    assert "huérfanas" in str(exc.value).lower()


def test_pregunta_sin_id_preg_falla_claro():
    p = _Pregunta(None, "SIN_PUENTE", _Opcion("1", "Sí"))
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_Respuesta(p, "1"))
    assert "id_preg" in str(exc.value)


def test_pregunta_sin_campo_id_preg_es_campo_faltante():
    # Distinto de "id_preg=None": aquí el modelo no define el campo (defecto de código).
    class _SinCampo:
        codigo_externo = "X"
        opciones = _Opciones(_Opcion("1", "Sí"))
    with pytest.raises(CampoOrigenFaltante):
        _r().resolver_res_idrespuesta(_Respuesta(_SinCampo(), "1"))


# ── el volcado está truncado: el código no puede concluir desde una ausencia ──
def test_pregunta_fuera_del_volcado_no_se_declara_inexistente(monkeypatch):
    """
    El resolver tiene DOS lecturas de una pregunta ausente, según `_meta.completo`.

    Con el volcado COMPLETO (el archivo real de hoy), la ausencia SÍ es evidencia:
    SICAV pregunta algo que Oracle no guarda ⇒ hallazgo real, pendiente de negocio.

    Pero el camino protector sigue vivo para un volcado PARCIAL: ahí una ausencia NO
    es evidencia de que Oracle no la tenga —solo de que no la exportamos—, y el error
    debe decir eso y nada más; si dijera "no existe en Oracle" mandaría a alguien a
    decidir sobre un dato inventado. Se ejercita con un catálogo parcial sintético.
    """
    p = _Pregunta(999999, "NO_EXISTE", _Opcion("1", "Sí"))
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_Respuesta(p, "1"))
    assert "no existe en el instrumento de Oracle" in str(exc.value)

    _catalogo_parcial(monkeypatch)
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_Respuesta(p, "1"))
    msg = str(exc.value)
    assert "NO quiere decir que no exista" in msg
    assert "TRUNCADO" in msg                       # dice por qué falta
    assert "no se puede afirmar ni que existe ni que no" in msg


def test_con_el_volcado_completo_la_ausencia_si_significa_algo(monkeypatch):
    # El día que llegue el export completo, el mismo caso cambia de lectura: ahí sí
    # es un hallazgo real (SICAV pregunta algo que Oracle no guarda) ⇒ negocio.
    cat = dict(catalogos.cargar_respuestas())
    cat["_meta"] = {**cat["_meta"], "completo": True}
    monkeypatch.setattr(catalogos, "cargar_respuestas", lambda: cat)
    p = _Pregunta(999999, "NO_EXISTE", _Opcion("1", "Sí"))
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_Respuesta(p, "1"))
    assert "no existe en el instrumento de Oracle" in str(exc.value)


def test_el_catalogo_cargado_es_completo_y_el_modo_truncado_sigue_cubierto(monkeypatch):
    # El JSON real se regeneró al export COMPLETO (902 preguntas): antes aquí se
    # afirmaba que estaba truncado a 200 filas, y eso ya no vale para el archivo. Se
    # fija el hecho nuevo (el catálogo real se declara completo) y, para no perder
    # cobertura, se ejercita el camino de truncado con un catálogo parcial sintético.
    meta = catalogos.cargar_respuestas()["_meta"]
    assert meta["completo"] is True
    assert meta.get("truncado") is None
    assert "completo" in meta["cobertura"]
    assert "TRUNCADO" not in meta["cobertura"]

    # Modo truncado (volcado parcial): la cobertura declara el corte, lista para el error.
    cobertura = _catalogo_parcial(monkeypatch)["_meta"]["cobertura"]
    assert "TRUNCADO" in cobertura
    assert "200 filas" in cobertura
    assert "temas 1, 2" in cobertura


# ── escribibilidad: ya verificada para las filas exportadas ─────────────────
def test_la_escribibilidad_ya_esta_verificada():
    # La Query A v2 trae la columna ESCRIBIBLE por fila ⇒ de lo que está en el volcado
    # se SABE si se puede escribir. (De lo que no está, se sigue sin saber nada.)
    assert catalogos.cargar_respuestas()["_meta"]["escribibilidad_verificada"] is True


def test_zona_cabecera_resuelve_limpio_al_id_real():
    # El caso que antes devolvía ‹PEND:ESCRIBIBLE›: ahora cruza y se confirma.
    assert _r().resolver_res_idrespuesta(_zona("1")) == 8


def test_sexo_mujer_resuelve_limpio_al_id_real():
    assert _r().resolver_res_idrespuesta(_sexo("2")) == 69


def test_sin_marca_de_escribibilidad_no_se_da_por_buena(monkeypatch):
    # Guarda para un volcado futuro sin la columna: mejor pendiente que suponer.
    cat = dict(catalogos.cargar_respuestas())
    cat["_meta"] = {**cat["_meta"], "escribibilidad_verificada": False}
    monkeypatch.setattr(catalogos, "cargar_respuestas", lambda: cat)
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_zona("1"))
    assert "no trae la marca de escribibilidad" in str(exc.value)


def test_huerfana_declarada_nunca_es_escribible(monkeypatch):
    # Con la lista cargada, una huérfana debe fallar aunque el cruce resuelva bien.
    cat = dict(catalogos.cargar_respuestas())
    cat["_meta"] = {**cat["_meta"], "escribibilidad_verificada": True}
    cat["huerfanas"] = frozenset({8})
    monkeypatch.setattr(catalogos, "cargar_respuestas", lambda: cat)
    with pytest.raises(MapeoPendienteNegocio) as exc:
        _r().resolver_res_idrespuesta(_zona("1"))
    msg = str(exc.value).lower()
    assert "huérfan" in msg
    assert "no escribiría nada" in msg  # explica el fallo silencioso del procedure


def test_con_escribibilidad_verificada_resuelve_el_id_limpio(monkeypatch):
    # El estado al que llegaremos cuando llegue el export con la marca.
    cat = dict(catalogos.cargar_respuestas())
    cat["_meta"] = {**cat["_meta"], "escribibilidad_verificada": True}
    cat["huerfanas"] = frozenset()
    monkeypatch.setattr(catalogos, "cargar_respuestas", lambda: cat)
    assert _r().resolver_res_idrespuesta(_zona("1")) == 8
    assert _r().resolver_res_idrespuesta(_sexo("2")) == 69


# ── el catálogo cargado refleja el volcado real ────────────────────────────
def test_meta_del_catalogo_declara_lo_que_sabemos_y_lo_que_no():
    meta = catalogos.cargar_respuestas()["_meta"]
    assert meta["instrumento"]["ins_idinstrumento"] == 1
    assert meta["instrumento"]["nombre"] == "CARACTERIZACION"
    assert meta["completo"] is True             # volcado regenerado al export completo
    assert "completo" in meta["cobertura"]      # la cobertura lo dice en una frase
    assert meta["riesgo_too_many_rows"] is False  # Query C3: 0 y 0
