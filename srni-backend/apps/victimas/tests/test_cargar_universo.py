"""
Carga del universo de víctimas.

Sin Oracle ni red: se prueba la resolución del corte, el desempate y el enlace,
que es donde se pierde el dato en silencio.
"""

import datetime

import pytest

from apps.victimas.management.commands import cargar_universo_victimas as C
from apps.victimas.models import DescarteUniverso, PersonaUniverso, Victima
from apps.victimas.repository.base import num_hash

CORTE = "TEMP_UNIV_VICT_PER_MI010726ALL"


# ── Resolución del corte por fecha ───────────────────────────────────────────

def test_el_nombre_del_corte_se_arma_por_fecha_y_no_esta_embebido():
    assert C.nombre_de_corte(datetime.date(2026, 7, 1)) == CORTE
    assert C.nombre_de_corte(datetime.date(2026, 8, 15)) == \
        "TEMP_UNIV_VICT_PER_MI010826ALL"


def test_del_nombre_se_deduce_la_fecha_para_medir_su_antiguedad():
    assert C.fecha_de_corte(CORTE) == datetime.date(2026, 7, 1)
    assert C.fecha_de_corte("TEMP_UNIV_VICT_PER_MI011225ALL") == datetime.date(2025, 12, 1)


def test_un_nombre_que_no_matchea_no_revienta_devuelve_None():
    """
    Si mañana cambian el patrón, el comando debe avisar que no puede controlar
    la antigüedad — no caerse ni, peor, dar por bueno un corte viejo.
    """
    assert C.fecha_de_corte("OTRA_TABLA") is None
    assert C.fecha_de_corte("") is None
    assert C.fecha_de_corte(None) is None


def test_el_umbral_de_alerta_existe_y_es_mensual():
    """La generación es mensual: 45 días ya es un corte perdido."""
    assert C.DIAS_ALERTA_CORTE == 45


# ── Desempate: determinista, siempre ─────────────────────────────────────────

def _p(cons, **kw):
    datos = dict(cons_persona_universo=cons, corte=CORTE,
                 primer_nombre="", segundo_nombre="", primer_apellido="",
                 segundo_apellido="", genero="", pertenencia_etnica="",
                 ciclo_vital="", tipo_documento="", num_hechos=0)
    datos.update(kw)
    return PersonaUniverso(**datos)


@pytest.mark.parametrize("regla", sorted(C.DESEMPATES))
def test_toda_regla_termina_en_el_id_y_por_eso_es_determinista(regla):
    """
    Sin un criterio final único, dos corridas podrían elegir filas distintas y
    el padrón cambiaría solo, sin que nadie tocara nada.
    """
    orden = C.Command._orden_de(regla)
    iguales = [_p(300), _p(100), _p(200)]
    iguales.sort(key=orden)
    assert [p.cons_persona_universo for p in iguales] == [100, 200, 300]


def test_por_defecto_gana_la_fila_mas_completa():
    orden = C.Command._orden_de("completitud")
    pobre = _p(100)
    rica = _p(999, primer_nombre="ANA", primer_apellido="GOMEZ", genero="Mujer")
    filas = sorted([pobre, rica], key=orden)
    assert filas[0].cons_persona_universo == 999


def test_con_la_regla_hechos_gana_quien_tiene_mas_aunque_este_menos_completa():
    orden = C.Command._orden_de("hechos")
    completa = _p(100, primer_nombre="ANA", primer_apellido="GOMEZ", num_hechos=1)
    con_hechos = _p(999, num_hechos=5)
    filas = sorted([completa, con_hechos], key=orden)
    assert filas[0].cons_persona_universo == 999


def test_num_hechos_nulo_no_rompe_el_orden():
    orden = C.Command._orden_de("hechos")
    filas = sorted([_p(100, num_hechos=None), _p(200, num_hechos=2)], key=orden)
    assert filas[0].cons_persona_universo == 200


# ── Construcción del registro ────────────────────────────────────────────────

def _fila(cons=23988216, doc="28548486", tipo="CC"):
    return (cons, tipo, doc, "RUBIELA", "", "DIAZ", "TRIANA",
            "Mujer", "Ninguna", 0, "", "entre 29 y 59", 3)


def test_el_id_del_universo_va_a_su_campo_y_no_a_cons_persona():
    """
    Cero coincidencias en 243.610 pares medidos: son numeraciones distintas, y
    `cons_persona` es lo que se escribe al legacy.
    """
    r = C.Command()._a_registro(_fila(), CORTE, datetime.date(2026, 7, 1))

    assert r.cons_persona_universo == 23988216
    assert not hasattr(r, "cons_persona")


def test_un_documento_corto_no_genera_hash_de_busqueda():
    """
    Menos de 5 caracteres no identifica a nadie — hay 1,2 M de documentos de un
    solo carácter en la fuente. Sin hash, esa fila no se devuelve por búsqueda.
    """
    r = C.Command()._a_registro(_fila(doc="99"), CORTE, None)

    assert r.numero_documento_hash_sin_tipo == ""
    assert r.numero_documento_hash == ""


def test_un_documento_usable_genera_los_dos_hashes():
    r = C.Command()._a_registro(_fila(), CORTE, None)

    assert r.numero_documento_hash_sin_tipo == num_hash("28548486")
    assert r.numero_documento_hash != ""


def test_sin_tipo_de_documento_igual_queda_el_hash_de_respaldo():
    """El 14,5 % de la fuente no trae tipo; sin este hash serían inencontrables."""
    r = C.Command()._a_registro(_fila(tipo=""), CORTE, None)

    assert r.numero_documento_hash_sin_tipo == num_hash("28548486")
    assert r.numero_documento_hash == ""


def test_una_fila_sin_id_de_fuente_se_descarta_en_vez_de_inventarlo():
    assert C.Command()._a_registro(_fila(cons=None), CORTE, None) is None


# ── Enlace con el padrón, por documento ──────────────────────────────────────

@pytest.mark.django_db
def test_el_enlace_encuentra_a_la_victima_por_documento_no_por_id():
    from apps.parametricas.models import TipoDocumento

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento="28548486",
        numero_documento_hash_sin_tipo=num_hash("28548486"),
        primer_nombre="RUBIELA", primer_apellido="DIAZ",
        fecha_nacimiento="1975-01-01", genero="F",
        cons_persona=958858,          # id del LEGACY: distinto del universo
    )
    PersonaUniverso.objects.create(
        cons_persona_universo=23988216, corte=CORTE,
        numero_documento="28548486",
        numero_documento_hash_sin_tipo=num_hash("28548486"),
    )

    C.Command()._enlazar_con_padron(CORTE, confirmar=True)

    p = PersonaUniverso.objects.get(cons_persona_universo=23988216)
    assert p.victima_id == victima.id
    # Y el id del legacy quedó intacto: es lo que se escribe a Oracle.
    victima.refresh_from_db()
    assert victima.cons_persona == 958858


@pytest.mark.django_db
def test_quien_esta_solo_en_el_universo_queda_sin_enlazar_y_eso_esta_bien():
    """
    Es el hueco que esta tabla viene a cubrir: 28548486 no estaba en SICAV. Que
    quede sin `victima` es el resultado correcto, no un fallo del cruce.
    """
    PersonaUniverso.objects.create(
        cons_persona_universo=23988216, corte=CORTE,
        numero_documento="28548486",
        numero_documento_hash_sin_tipo=num_hash("28548486"),
    )

    C.Command()._enlazar_con_padron(CORTE, confirmar=True)

    assert PersonaUniverso.objects.get(cons_persona_universo=23988216).victima_id is None


# ── Resolución de duplicados: no se borra nada ──────────────────────────────

@pytest.mark.django_db
def test_el_duplicado_pierde_la_preferencia_pero_NO_se_borra():
    """
    Una fila que pierde el desempate sigue siendo un dato real de la fuente.
    Borrarla haría imposible responder después por qué esa persona no aparece.
    """
    h = num_hash("28548486")
    PersonaUniverso.objects.create(
        cons_persona_universo=100, corte=CORTE, numero_documento="28548486",
        numero_documento_hash_sin_tipo=h, primer_nombre="RUBIELA",
        primer_apellido="DIAZ", genero="Mujer")
    PersonaUniverso.objects.create(
        cons_persona_universo=200, corte=CORTE, numero_documento="28548486",
        numero_documento_hash_sin_tipo=h)

    C.Command()._resolver_duplicados(CORTE, "completitud", confirmar=True)

    assert PersonaUniverso.objects.filter(corte=CORTE).count() == 2   # ninguna borrada
    assert PersonaUniverso.objects.get(cons_persona_universo=100).es_preferida is True
    assert PersonaUniverso.objects.get(cons_persona_universo=200).es_preferida is False

    descarte = DescarteUniverso.objects.get(cons_persona_universo=200)
    assert descarte.motivo == "DOCUMENTO_REPETIDO"
    assert "100" in descarte.detalle          # dice quién ganó


@pytest.mark.django_db
def test_sin_documento_no_entra_al_desempate():
    """Las filas sin hash no compiten entre sí: no comparten identidad."""
    PersonaUniverso.objects.create(cons_persona_universo=100, corte=CORTE,
                                   numero_documento="99")
    PersonaUniverso.objects.create(cons_persona_universo=200, corte=CORTE,
                                   numero_documento="0")

    C.Command()._resolver_duplicados(CORTE, "completitud", confirmar=True)

    assert PersonaUniverso.objects.filter(es_preferida=False).count() == 0


# ── Defectos que encontró la revisión adversarial (5-ago) ───────────────────
#
# Los cuatro pasaban los tests anteriores. Cada uno de estos falla con el código
# de antes del arreglo.

@pytest.mark.django_db
def test_el_acumulador_se_vacia_tambien_en_DRY_RUN():
    """
    Antes `_volcar` solo se llamaba con `--confirmar`, así que un ensayo SIN
    `--limite` acumulaba los 12,5 M de objetos en memoria y moría por OOM.
    Justo la corrida que se hace para NO arriesgar nada.
    """
    acumulador = [PersonaUniverso(cons_persona_universo=1, corte=CORTE),
                  PersonaUniverso(cons_persona_universo=2, corte=CORTE)]
    C.Command._volcar(PersonaUniverso, acumulador, confirmar=False)

    assert acumulador == []                        # se vació: no crece sin límite
    assert PersonaUniverso.objects.count() == 0    # y no escribió nada


@pytest.mark.django_db
def test_volcar_con_confirmar_si_escribe():
    acumulador = [PersonaUniverso(cons_persona_universo=1, corte=CORTE)]
    C.Command._volcar(PersonaUniverso, acumulador, confirmar=True)

    assert acumulador == []
    assert PersonaUniverso.objects.count() == 1


@pytest.mark.django_db
def test_re_resolver_con_otra_regla_no_deja_al_grupo_sin_preferida():
    """
    La fase 2 es TOTAL, no incremental. Antes solo marcaba `False` a las
    perdedoras y nunca reseteaba: al re-resolver con otra regla se acumulaban
    los `False` y el grupo quedaba SIN NINGUNA preferida — esa persona
    desaparecía del enlace y de toda derivación, que es el caso que este módulo
    vino a arreglar.
    """
    h = num_hash("28548486")
    PersonaUniverso.objects.create(
        cons_persona_universo=100, corte=CORTE, numero_documento="28548486",
        numero_documento_hash_sin_tipo=h, primer_nombre="RUBIELA",
        primer_apellido="DIAZ", genero="Mujer", num_hechos=0)
    PersonaUniverso.objects.create(
        cons_persona_universo=200, corte=CORTE, numero_documento="28548486",
        numero_documento_hash_sin_tipo=h, num_hechos=9)

    cmd = C.Command()
    cmd._resolver_duplicados(CORTE, "completitud", confirmar=True)   # gana 100
    cmd._resolver_duplicados(CORTE, "hechos", confirmar=True)        # gana 200

    preferidas = PersonaUniverso.objects.filter(corte=CORTE, es_preferida=True)
    assert preferidas.count() == 1, "el grupo quedó sin preferida"
    assert preferidas.first().cons_persona_universo == 200


@pytest.mark.django_db
def test_el_reset_a_preferida_no_reescribe_las_filas_que_ya_estaban_en_True():
    """
    El reset debe tocar SOLO las que están en `False`.

    Sin el filtro, el UPDATE alcanza a las 12 M de filas del corte. Como
    `es_preferida` está indexada, Postgres no puede hacer HOT update y reescribe
    el heap entero más los 12 índices: ~19 GB medidos sobre la carga del 5-ago,
    con 6 GB libres en un disco compartido con otros servicios de la entidad.
    """
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    h = num_hash("28548486")
    for cons in (100, 200):
        PersonaUniverso.objects.create(
            cons_persona_universo=cons, corte=CORTE, numero_documento="28548486",
            numero_documento_hash_sin_tipo=h)

    with CaptureQueriesContext(connection) as capturadas:
        C.Command()._resolver_duplicados(CORTE, "completitud", confirmar=True)

    resets = [q["sql"] for q in capturadas.captured_queries
              if "UPDATE" in q["sql"].upper() and "es_preferida" in q["sql"]
              and "IN (" not in q["sql"].upper()]
    assert resets, "no se encontró el UPDATE de reset"
    for sql in resets:
        assert "es_preferida" in sql.split("WHERE", 1)[1], (
            "el reset no filtra por es_preferida: reescribiría el corte entero")


@pytest.mark.django_db
def test_re_resolver_no_duplica_los_descartes():
    """
    `DescarteUniverso` existe para responder "cuántas personas faltan". Sin
    reemplazar los de la fase, después de dos corridas respondía el doble.
    """
    h = num_hash("28548486")
    for cons in (100, 200):
        PersonaUniverso.objects.create(
            cons_persona_universo=cons, corte=CORTE, numero_documento="28548486",
            numero_documento_hash_sin_tipo=h)

    cmd = C.Command()
    cmd._resolver_duplicados(CORTE, "completitud", confirmar=True)
    cmd._resolver_duplicados(CORTE, "completitud", confirmar=True)

    assert DescarteUniverso.objects.filter(motivo="DOCUMENTO_REPETIDO").count() == 1


@pytest.mark.django_db
def test_un_documento_que_resuelve_a_dos_victimas_NO_se_enlaza_a_ninguna():
    """
    El hash está indexado pero no es único, y en el padrón hay documentos
    compartidos por cientos de filas. Antes ganaba "la última que devolviera
    Postgres": no determinista, y en los grupos que son personas DISTINTAS
    enlazaba con otra. Elegir una es inventar una correspondencia.
    """
    from apps.parametricas.models import TipoDocumento

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
    h = num_hash("28548486")
    for nombre in ("RUBIELA", "MARIA"):
        Victima.objects.create(
            tipo_documento=tipo, numero_documento="28548486",
            numero_documento_hash_sin_tipo=h,
            primer_nombre=nombre, primer_apellido="DIAZ",
            fecha_nacimiento="1975-01-01", genero="F")
    PersonaUniverso.objects.create(
        cons_persona_universo=23988216, corte=CORTE,
        numero_documento="28548486", numero_documento_hash_sin_tipo=h)

    C.Command()._enlazar_con_padron(CORTE, confirmar=True)

    p = PersonaUniverso.objects.get(cons_persona_universo=23988216)
    assert p.victima_id is None, "eligió una víctima arbitraria entre dos"
    assert DescarteUniverso.objects.filter(motivo="ENLACE_AMBIGUO").count() == 1


def test_el_umbral_de_5_se_mide_sobre_el_documento_normalizado():
    """
    `1.2.3` tiene cinco caracteres crudos pero normaliza a `123`, que no
    identifica a nadie. Medir sobre el crudo lo dejaba pasar.
    """
    r = C.Command()._a_registro(_fila(doc="1.2.3"), CORTE, None)
    assert r.numero_documento_hash_sin_tipo == ""

    r = C.Command()._a_registro(_fila(doc="28.548.486"), CORTE, None)
    assert r.numero_documento_hash_sin_tipo != ""


def test_la_discapacidad_usa_la_homologacion_canonica():
    """
    Había dos homologaciones de lo mismo en el repo: `bool()` acá y
    `homologar_discapacidad` allá. Tener dos es el defecto que ya costó una
    tarde con los hechos victimizantes.
    """
    assert C.Command()._a_registro(_fila(), CORTE, None).discapacidad is False

    fila = list(_fila())
    fila[9] = 1
    assert C.Command()._a_registro(tuple(fila), CORTE, None).discapacidad is True

    # NULL es "no consta", no "no tiene": la canónica lo trata como False.
    fila[9] = None
    assert C.Command()._a_registro(tuple(fila), CORTE, None).discapacidad is False


# ── Homologación de género: los cinco valores REALES del universo ───────────
#
# Medidos el 5-ago sobre 1.172.594 filas ya cargadas del corte de julio:
#   Hombre 50,010 % · Mujer 49,890 % · LGBTI 0,068 % ·
#   No Informa 0,026 % · Intersexual 0,006 %
# Los que no son Hombre/Mujer proyectan a ~12.448 personas sobre los 12,5 M.

from apps.victimas import homologacion as H   # noqa: E402


@pytest.mark.parametrize("crudo,esperado", [
    ("Hombre", "M"),
    ("Mujer", "F"),
    ("No Informa", "ND"),
    ("LGBTI", "ND"),         # no es un género: ver GENERO_APROXIMADO
    ("Intersexual", "ND"),   # condición biológica, no identidad declarada
])
def test_los_cinco_valores_del_universo_se_homologan(crudo, esperado):
    assert H.homologar_genero(crudo) == esperado


def test_ninguno_de_los_cinco_cae_al_default_por_accidente():
    """
    Que LGBTI e Intersexual den ND es una DECISIÓN, no un descuido. Si estuvieran
    solo por el default, un valor nuevo de la fuente sería indistinguible de
    ellos y nadie se enteraría.
    """
    for valor in ("Hombre", "Mujer", "No Informa", "LGBTI", "Intersexual"):
        assert H.genero_es_conocido(valor), f"{valor} caería al default"


def test_un_valor_nuevo_de_la_fuente_se_detecta():
    """
    `homologar_genero` seguirá devolviendo ND —nunca inventa un género— pero la
    carga tiene que poder avisar que apareció algo que no contemplamos.
    """
    assert not H.genero_es_conocido("Género fluido")
    assert H.homologar_genero("Género fluido") == "ND"   # sin inventar


def test_las_perdidas_de_precision_estan_declaradas_con_su_razon():
    """Una pérdida que solo vive en un comentario es una que nadie vuelve a mirar."""
    assert set(H.GENERO_APROXIMADO) == {"lgbti", "intersexual"}
    for razon in H.GENERO_APROXIMADO.values():
        assert len(razon) > 40


def test_el_universo_guarda_el_genero_CRUDO_no_el_homologado():
    """
    `PersonaUniverso` es un snapshot fiel de la fuente: guarda 'Mujer', no 'F'.
    La homologación ocurre al usarlo, y así el valor real de las ~12.448
    personas que no son Hombre/Mujer no se pierde.
    """
    r = C.Command()._a_registro(_fila(), CORTE, None)
    assert r.genero == "Mujer"
    assert H.homologar_genero(r.genero) == "F"
