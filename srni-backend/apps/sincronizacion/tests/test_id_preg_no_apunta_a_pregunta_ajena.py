"""
Red de seguridad del puente `id_preg` → `PRE_IDPREGUNTA`.

El defecto que evita (detectado 2026-07-28): 75 preguntas de SICAV tenían un
`id_preg` que en el catálogo real de Oracle corresponde a **otra** pregunta. Por
ejemplo "Observaciones a este capítulo" apuntaba a 1438, que en Oracle es "QUÉ
DIAGNÓSTICO DE ENFERMEDAD PRESENTA?". Escribir así guarda la respuesta en la
pregunta equivocada de la base de la UARIV — y como los procedures se tragan las
excepciones, nadie se entera.

Salió de asignar a preguntas nuevas (los sub-campos del barrido V7→V8) un id
correlativo libre **en SICAV**, sin comprobar que ese número ya está ocupado **en
Oracle**.

Este test compara el texto de cada pregunta contra el de la pregunta Oracle del
mismo id. Es una heurística — por eso el umbral es bajo y hay una lista de
excepciones justificadas — pero convierte un fallo silencioso en un test rojo.
"""
import json
import pathlib
import re
import unicodedata

import pytest

from apps.sincronizacion.oracle import catalogos as _catalogos_mod

# Las rutas se derivan del propio módulo de catálogos, no de contar `parents`:
# así siguen valiendo si el árbol se mueve.
CATALOGO = pathlib.Path(_catalogos_mod.__file__).with_name("respuestas_oracle.json")
FIXTURES = pathlib.Path(_catalogos_mod.__file__).parents[2] / "formulario/fixtures"

# Perfiles con el defecto todavía abierto (ver bloqueante_id_preg_subcampos.md).
# Se corrigen en su turno; mientras tanto no deben romper la suite, pero tampoco
# desaparecer del radar: cuando se arreglen, hay que sacarlos de aquí.
PENDIENTES = {"perfil_rural_etnico_v1", "perfil_telefonico_v8"}
# territorial_v7 está desactivado en la BD (comando desactivar_instrumento).
IGNORADOS = {"perfil_territorial_v7"}

VACIAS = {"de", "la", "el", "los", "las", "en", "un", "una", "y", "o", "a", "que",
          "cual", "cuales", "del", "por", "para", "su", "sus", "se", "es", "con",
          "al", "lo", "mas", "no", "si", "usted", "este", "esta"}
UMBRAL = 0.20


def _tokens(texto):
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return {t for t in re.findall(r"[a-z0-9]+", texto) if t not in VACIAS and len(t) > 2}


def _catalogo_oracle():
    datos = json.loads(CATALOGO.read_text(encoding="utf-8"))
    return {int(p["pre_idpregunta"]): (p["pre_pregunta"] or "") for p in datos["preguntas"]}


def _preguntas(perfil):
    datos = json.loads((FIXTURES / f"{perfil}.json").read_text(encoding="utf-8"))
    return datos.get("preguntas", [])


def _perfiles_vigentes():
    return sorted(p.stem for p in FIXTURES.glob("perfil_*.json")
                  if p.stem not in IGNORADOS | PENDIENTES)


@pytest.mark.parametrize("perfil", _perfiles_vigentes())
def test_ningun_id_preg_apunta_a_una_pregunta_ajena(perfil):
    oracle = _catalogo_oracle()
    ajenas = []
    for pregunta in _preguntas(perfil):
        idp = pregunta.get("id_preg")
        if idp in (None, "") or int(idp) not in oracle:
            continue                      # sin puente, o pregunta propia de SICAV
        a, b = _tokens(pregunta.get("texto")), _tokens(oracle[int(idp)])
        if not a or not b:
            continue
        if len(a & b) / min(len(a), len(b)) < UMBRAL:
            ajenas.append(
                f"    {pregunta.get('codigo_externo')} (id_preg={idp})\n"
                f"      SICAV : {(pregunta.get('texto') or '')[:70]!r}\n"
                f"      ORACLE: {oracle[int(idp)][:70]!r}")
    assert not ajenas, (
        f"\n{perfil}: {len(ajenas)} pregunta(s) escribirían en la pregunta equivocada "
        f"de Oracle.\n" + "\n".join(ajenas) +
        "\n\n  Arreglo: si la pregunta NO existe en Oracle (es un sub-campo de SICAV), "
        "pon id_preg = null — el resolver la declara pendiente en vez de escribir mal. "
        "Si SÍ existe con otro id, corrige el id.\n")


def test_la_lista_de_pendientes_no_crece_en_silencio():
    """
    Si alguien corrige rural_etnico o telefonico, que lo saque de PENDIENTES; y si
    aparece un perfil nuevo, que pase por el test en vez de sumarse a la excepción.
    """
    assert PENDIENTES == {"perfil_rural_etnico_v1", "perfil_telefonico_v8"}, (
        "Cambió la lista de perfiles con el defecto abierto: actualiza también "
        "docs/oracle-legacy/bloqueante_id_preg_subcampos.md")
