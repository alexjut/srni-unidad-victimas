"""
"Que al entrar vean lo que han hecho" — las caracterizaciones del legacy.

Dos cosas se protegen acá, y la segunda salió de un caso real:

1. **Que cada quien vea lo suyo y solo lo suyo.** Es un listado de "lo mío": si
   acepta un parámetro que diga de quién, deja de serlo.

2. **Que el cruce sea por la cadena del creador, no por `GIC_USUARIO`.** El
   legacy arma su listado con un INNER JOIN contra ese catálogo, y medido en
   producción **1.077.712 hogares (97,7 %)** tienen un creador que no está ahí.
   `JGUARINH` —el del caso de Pandi— tiene 18 caracterizaciones y ninguna fila de
   usuario: repetir ese JOIN le mostraría cero, que es el problema que este
   listado viene a resolver.
"""
import datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.sincronizacion.management.commands.importar_caracterizaciones_legacy import (
    Command,
)
from apps.sincronizacion.models import CaracterizacionLegacy, UsuarioLegacy

pytestmark = pytest.mark.django_db
Usuario = get_user_model()


def _caracterizacion(creador, hog, **kw):
    base = dict(
        usuario_creador=creador, estado="MIGRADOAHISTORICO",
        creado_en_legacy=datetime.datetime(2026, 4, 24, 10, 0,
                                           tzinfo=datetime.timezone.utc),
        miembros=4, respuestas_definitivas=366, respuestas_trabajo=0,
        capitulos=13, veredicto="COMPLETO", visible_en_reportes=True,
    )
    base.update(kw)
    return CaracterizacionLegacy.objects.create(hog_codigo=hog, **base)


def _cliente(codigo):
    u = Usuario.objects.create_user(
        codigo_usuario=codigo, email=f"{codigo}@x.co",
        nombre_completo=codigo, password="x")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


# ── aislamiento ──────────────────────────────────────────────────────────────

def test_cada_encuestador_ve_solo_lo_suyo():
    _caracterizacion("JGUARINH", "197035-31TUK")
    _caracterizacion("OTRAPERSONA", "111111-ZZZZZ")

    r = _cliente("JGUARINH").get("/api/sincronizacion/mis-caracterizaciones/")
    assert r.status_code == 200
    codigos = [x["hog_codigo"] for x in r.json()["results"]]
    assert codigos == ["197035-31TUK"]


def test_el_cruce_no_distingue_mayusculas():
    """
    El legacy guarda los logins en mayúscula y SICAV no necesariamente. Que el
    trabajo de alguien no aparezca por una diferencia de caja sería exactamente
    la clase de fallo silencioso que este listado viene a evitar.
    """
    _caracterizacion("JGUARINH", "197035-31TUK")
    r = _cliente("jguarinh").get("/api/sincronizacion/mis-caracterizaciones/")
    assert [x["hog_codigo"] for x in r.json()["results"]] == ["197035-31TUK"]


def test_sin_autenticar_no_se_ve_nada():
    _caracterizacion("JGUARINH", "197035-31TUK")
    assert APIClient().get(
        "/api/sincronizacion/mis-caracterizaciones/").status_code in (401, 403)


def test_un_usuario_sin_trabajo_en_el_legacy_recibe_una_lista_vacia():
    """No un error: no haber usado la aplicación vieja es normal."""
    _caracterizacion("OTRO", "111111-AAAAA")
    r = _cliente("NUEVO").get("/api/sincronizacion/mis-caracterizaciones/")
    assert r.status_code == 200
    assert r.json()["results"] == []


# ── lo que hace útil al listado ──────────────────────────────────────────────

def test_el_listado_dice_cuales_no_estan_contando():
    """
    Sin `visible_en_reportes` esto es una lista de códigos. Con ella el
    encuestador ve que un trabajo suyo no cuenta — información que hoy no tiene
    por ningún lado y que solo aparecía cuando el territorio la reclamaba.
    """
    _caracterizacion("JGUARINH", "197035-H7452", estado="ACTIVA",
                     respuestas_definitivas=0, respuestas_trabajo=2, capitulos=0,
                     veredicto="NO_CERRO_POR_CAPITULOS", visible_en_reportes=False)
    _caracterizacion("JGUARINH", "197035-31TUK")

    r = _cliente("JGUARINH").get("/api/sincronizacion/mis-caracterizaciones/resumen/")
    d = r.json()
    assert d["total"] == 2
    assert d["visibles_en_reportes"] == 1
    assert d["invisibles"] == 1
    assert d["por_veredicto"]["NO_CERRO_POR_CAPITULOS"] == 1


def test_el_recibo_no_lleva_datos_personales():
    """
    El listado es el recibo del trabajo, no la encuesta: códigos, fechas,
    estados y conteos. Nada de nombres, documentos ni respuestas.

    Se comprueba con lista blanca y no buscando palabras prohibidas: un campo
    nuevo hace fallar el test aunque se llame de forma inocente, y obliga a
    decidir a conciencia si puede viajar. `respuestas_definitivas` y
    `respuestas_trabajo` están permitidos porque son **cuántas**, no cuáles — y
    el test lo verifica exigiendo que sean enteros.
    """
    _caracterizacion("JGUARINH", "197035-31TUK")
    fila = _cliente("JGUARINH").get(
        "/api/sincronizacion/mis-caracterizaciones/").json()["results"][0]

    permitidos = {
        "hog_codigo", "encuestador", "estado", "creado_en_legacy", "fecha_estado",
        "miembros", "respuestas_definitivas", "respuestas_trabajo", "capitulos",
        "veredicto", "visible_en_reportes",
    }
    assert set(fila) == permitidos, "campo nuevo en el recibo: ¿puede llevar PII?"
    for conteo in ("miembros", "respuestas_definitivas", "respuestas_trabajo",
                   "capitulos"):
        assert isinstance(fila[conteo], int)


# ── la preparación del recibo, sin Oracle ────────────────────────────────────

def test_el_estado_migrado_al_historico_cuenta_como_visible():
    """1.039.334 hogares están así; tratarlos como invisibles sería absurdo."""
    p = Command._preparar("JGUARINH", (
        "197035-31TUK", "JGUARINH", 197035, "MIGRADOAHISTORICO", None, None,
        4, 366, 0, 13))
    assert p["visible_en_reportes"] is True
    assert p["veredicto"] == "COMPLETO"


def test_un_hogar_abierto_con_respuestas_se_marca_invisible_y_recuperable():
    p = Command._preparar("JGUARINH", (
        "197035-H7452", "JGUARINH", 197035, "ACTIVA", None, None, 3, 0, 2, 0))
    assert p["visible_en_reportes"] is False
    assert p["veredicto"] == "NO_CERRO_POR_CAPITULOS"


def test_cerrado_sin_respuestas_no_se_declara_visible():
    """
    El estado dice CERRADA pero la tabla definitiva está vacía: para los reportes
    ese hogar no existe. Mirar solo el estado lo daría por bueno.
    """
    p = Command._preparar("X", ("H", "X", 1, "CERRADA", None, None, 3, 0, 0, 8))
    assert p["visible_en_reportes"] is False
    assert p["veredicto"] == "CERRADO_SIN_ARCHIVAR"


def test_el_catalogo_de_usuarios_es_opcional_y_no_condiciona_nada():
    """
    La caracterización se guarda con o sin fila en `UsuarioLegacy`. Es el punto
    entero del diseño: 97,7 % de los hogares no tienen usuario en el catálogo.
    """
    UsuarioLegacy.objects.create(usu_idusuario=1, usu_usuario="OTRO")
    c = _caracterizacion("JGUARINH", "197035-31TUK")
    assert c.usuario_legacy is None
    assert CaracterizacionLegacy.objects.filter(
        usuario_creador="JGUARINH").count() == 1
