"""
Vigencia de caracterización para quien está en el UNIVERSO pero no en el padrón.

─── Por qué existe ──────────────────────────────────────────────────────────
El universo (`PersonaUniverso`, 12 M) responde **existencia e identidad**, y eso
fue lo que resolvió el caso que originó todo: `28548486` está en el RUV, nunca
fue caracterizada, y en SICAV "no existía" porque el padrón se armó desde el
registro de quién ya había sido caracterizado.

Pero el universo **no dice si la persona tiene ficha vigente**. Verificado sobre
las 12.496.965 filas del corte: `IDENTIFICADO` viene en 0 en todas y `ESTADO_RUV`
ni siquiera existe como columna. Si la búsqueda se conectara al universo sin
resolver esto, **toda persona ausente del padrón aparecería como caracterizable**,
incluida `1115724047`, que fue caracterizada el 28-jul-2026. La regla de los dos
años se perdería sin que nada fallara.

─── De dónde sale la fecha ──────────────────────────────────────────────────
Del mismo lugar que para el padrón: `GIC_HOGAR.USU_FECHACREACION`, la fecha del
hogar en el que la persona participó. El puente es el **documento**, porque el
id del universo y el del legado son espacios distintos (medido: 0 coincidencias
en 243.610 pares).

⚠️ Esto es un **sustituto**, no la fuente. La autoritativa es
`TEMP_UNIV_VICT_CONTING` (`ENTRE_FICHA_VIGENTE`), a la que hoy no tenemos
acceso. Cuando llegue, la fecha sale de ahí y esto pasa a ser el respaldo.

─── Por qué se guarda ───────────────────────────────────────────────────────
Se consulta **una vez por persona** y se persiste en `PersonaUniverso`. Preguntarle
a Oracle en cada búsqueda pondría una dependencia de red en el camino más caliente
de la aplicación: en territorio, con la VPN intermitente, eso convierte una
búsqueda en una espera.
"""

import logging

from django.utils import timezone

log = logging.getLogger(__name__)

#: La fecha se busca por documento. `GIC_PERSONA` tiene índice sobre el documento
#: (15 índices, ninguno sobre `PER_IDPERSONA`), así que esta consulta es barata;
#: la del padrón completo, que agrupaba por persona, no lo era.
CONSULTA_FECHA = """
    SELECT MAX(h.usu_fechacreacion)
      FROM gic_persona p
      JOIN gic_miembros_hogar m ON m.per_idpersona = p.per_idpersona
      JOIN gic_hogar h          ON h.hog_codigo    = m.hog_codigo
     WHERE TRIM(p.per_numerodoc) = :doc
       AND h.usu_fechacreacion IS NOT NULL
"""


class VigenciaNoVerificable(Exception):
    """No se pudo preguntar al legado. NO significa que la persona no tenga ficha."""


def _consultar_legado(numero_documento: str):
    """Devuelve la fecha (o None si el legado no tiene ninguna). Puede fallar."""
    from apps.sincronizacion.oracle import conexion as cx

    try:
        con = cx.abrir_conexion(cx.DESTINO_PRODUCCION)
    except Exception as exc:                       # red, credenciales, Oracle caído
        raise VigenciaNoVerificable(str(exc)) from exc

    try:
        cur = con.cursor()
        cur.execute(CONSULTA_FECHA, {"doc": (numero_documento or "").strip()})
        fila = cur.fetchone()
        return fila[0] if fila else None
    except Exception as exc:
        raise VigenciaNoVerificable(str(exc)) from exc
    finally:
        try:
            con.close()
        except Exception:
            pass


def resolver(persona, *, forzar: bool = False):
    """
    Deja `persona.fecha_ult_caracterizacion` resuelta y la persiste.

    Devuelve `(fecha, verificada)`:
      · `verificada=True`  → se preguntó al legado (ahora o antes) y la respuesta
        es confiable. `fecha=None` significa **nunca caracterizada**.
      · `verificada=False` → no se pudo preguntar. `fecha` es lo que hubiera, y
        quien llame **debe decirlo**: tratar "no sé" como "no tiene ficha" es
        exactamente el error que abre la puerta a recaracterizar sin control.
    """
    if persona.vigencia_verificada_en and not forzar:
        return persona.fecha_ult_caracterizacion, True

    try:
        fecha = _consultar_legado(persona.numero_documento)
    except VigenciaNoVerificable as exc:
        log.warning("vigencia no verificable para persona del universo %s: %s",
                    persona.cons_persona_universo, exc)
        return persona.fecha_ult_caracterizacion, False

    # Oracle devuelve la fecha sin zona horaria. Guardarla así deja que Django la
    # interprete por su cuenta —con un warning que nadie lee— y ese desfase se
    # arrastra al cálculo de los dos años. Se fija explícitamente.
    if fecha is not None and timezone.is_naive(fecha):
        fecha = timezone.make_aware(fecha, timezone.get_default_timezone())

    persona.fecha_ult_caracterizacion = fecha
    persona.vigencia_verificada_en = timezone.now()
    persona.save(update_fields=["fecha_ult_caracterizacion", "vigencia_verificada_en"])
    return fecha, True


class PersonaParaElegibilidad:
    """
    Adaptador mínimo para `describir_elegibilidad`, que acepta cualquier objeto
    con estos tres atributos. Se usa un adaptador y no una copia de la lógica
    porque el árbol de decisión —vigencia, rutas de excepción, excluidos del
    RUV— **debe ser uno solo**: ya costó una divergencia de textos entre
    `buscar_por_documento` y `estado_habilitacion`.
    """

    def __init__(self, fecha_ult_caracterizacion, *, verificada: bool):
        self.fecha_ult_caracterizacion = fecha_ult_caracterizacion
        #: El universo no trae estado en el RUV. `NO_VERIFICADO` es lo honesto:
        #: no es 'EXCLUIDO' (que bloquearía a alguien sin fundamento) ni
        #: 'INCLUIDO' (que afirmaría algo que no medimos).
        self.estado_ruv = 'NO_VERIFICADO'
        #: Sin fecha de caracterización, la persona es elegible. Con fecha, el
        #: árbol de decisión evalúa la vigencia y las rutas de excepción.
        #:
        #: Si NO se pudo verificar, se deja habilitada a propósito: negarle la
        #: caracterización a una víctima por una falla de conectividad nuestra
        #: es peor que el riesgo de una ficha repetida, y el aviso viaja en el
        #: mensaje para que el encuestador lo sepa.
        self.habilitado_para_caracterizacion = (
            fecha_ult_caracterizacion is None or not verificada)
