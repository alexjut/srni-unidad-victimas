"""
Lectura de los hechos victimizantes desde el RUV.

─── De dónde salen ──────────────────────────────────────────────────────────
Ubicados el 4-ago-2026. Viven en el esquema `RUV`, alcanzable desde
`ENTREVISTARN` por el dblink **`CONSULTARUV`** que ya existía: no hizo falta
pedir accesos nuevos. La ruta hasta el documento está declarada con foreign
keys, no es convención nuestra:

    RUV.TBPERSONAS                (ID, NUMERODOCUMENTO, PARAM_TIPODOCUMENTO)
        ↑ FK_TBPER_REGPERSONAS
    RUV.TBREGISTROS_PERSONAS      (ID, ID_PERSONA, ACTIVO)          8.661.657
        ↑ FK_REGPER_SINIESTRO
    RUV.TBSINIESTROS_PERSONA      (ID_REGPERSONA, PARAM_TIPOHECHO,  4.033.355
                                   FECHASINIESTRO, ID_DEPARTAMENTO,
                                   ID_MUNICIPIO, ACTIVO)

Se lee `TBSINIESTROS_PERSONA` y no `TBREG_PERSONA_HECHOS` (9.331.396 filas)
porque es la única de las dos que trae **fecha y lugar** del hecho. La otra solo
tiene el par (persona, hecho), así que llenaría la columna pero no el *cuándo* ni
el *dónde*.

─── Lo que este módulo NO hace ──────────────────────────────────────────────
**No resuelve `lugar_hecho`.** `ID_DEPARTAMENTO`/`ID_MUNICIPIO` del RUV son ids
*surrogate*, igual que los del legacy —donde ya está medido que TOLIMA=30 y
ALVARADO=32, o sea que no son DANE—. Suponer que las dos numeraciones coinciden
metería el municipio equivocado en silencio, que es exactamente el modo de fallo
que este proyecto viene evitando en los catálogos de hechos. Hasta verificar el
crosswalk del RUV, los ids crudos se devuelven aparte y `lugar_hecho` queda
`NULL`.

─── Ambigüedad de documento: no se adivina ──────────────────────────────────
El cruce natural sería por número de documento, pero está medido que el padrón
tiene 1,2 M de documentos de un solo carácter y que hay números repetidos. Si un
número resuelve a **más de una** persona del RUV, este módulo **no elige**:
devuelve la ambigüedad para que el llamador decida, igual que se hizo con la
identidad de los encuestadores. Un hecho atribuido a la persona equivocada es
peor que un hecho ausente.
"""

from __future__ import annotations

import dataclasses
import datetime

from .catalogos import HECHO_RUV_A_SICAV

#: Nombre del dblink desde `ENTREVISTARN` hacia el RUV.
DBLINK = "CONSULTARUV"

#: Hechos leídos que el catálogo del RUV no debería producir. Si aparece uno,
#: es que el catálogo cambió y hay que revisarlo antes de escribir nada.
class HechoRuvDesconocido(ValueError):
    """El RUV devolvió un `PARAM_TIPOHECHO` que no está en el catálogo."""


@dataclasses.dataclass(frozen=True)
class HechoLeido:
    """Un hecho del RUV, ya traducido al código de SICAV."""

    id_ruv: int
    codigo_sicav: str
    fecha: datetime.date | None
    #: Ids *surrogate* del RUV, sin traducir. Ver el encabezado del módulo.
    id_departamento: int | None
    id_municipio: int | None

    @property
    def tiene_lugar(self) -> bool:
        return self.id_departamento is not None or self.id_municipio is not None


@dataclasses.dataclass(frozen=True)
class LecturaHechos:
    """
    Resultado de consultar por un documento.

    `personas_ruv` es cuántas personas del RUV respondieron a ese número. Si es
    mayor que 1 la lectura es **ambigua** y `hechos` viene vacío a propósito:
    mezclar los hechos de dos personas distintas sería peor que no traer nada.
    """

    documento: str
    personas_ruv: int
    hechos: tuple[HechoLeido, ...]

    @property
    def es_ambigua(self) -> bool:
        return self.personas_ruv > 1

    @property
    def encontrada(self) -> bool:
        return self.personas_ruv >= 1


# El `ACTIVO = 1` va en las dos tablas: un registro de persona inactivo no
# aporta hechos vigentes, y un siniestro inactivo fue dado de baja. Sin ese
# filtro se recuperan hechos que el propio RUV ya no cuenta.
SQL_HECHOS_POR_DOCUMENTO = f"""
    SELECT s.ID,
           s.PARAM_TIPOHECHO,
           s.FECHASINIESTRO,
           s.ID_DEPARTAMENTO,
           s.ID_MUNICIPIO,
           r.ID_PERSONA
      FROM RUV.TBPERSONAS@{DBLINK} p
      JOIN RUV.TBREGISTROS_PERSONAS@{DBLINK} r ON r.ID_PERSONA = p.ID
      JOIN RUV.TBSINIESTROS_PERSONA@{DBLINK} s ON s.ID_REGPERSONA = r.ID
     WHERE p.NUMERODOCUMENTO = :documento
       AND NVL(r.ACTIVO, 1) = 1
       AND NVL(s.ACTIVO, 1) = 1
     ORDER BY s.FECHASINIESTRO NULLS LAST, s.ID
"""


def _a_fecha(valor) -> datetime.date | None:
    """Oracle devuelve `DATE` como datetime; acá solo interesa el día."""
    if valor is None:
        return None
    if isinstance(valor, datetime.datetime):
        return valor.date()
    return valor


def leer_hechos(cursor, documento: str, *, estricto: bool = True) -> LecturaHechos:
    """
    Lee los hechos de un documento. `cursor` se inyecta para poder probar esto
    sin Oracle y sin red.

    Con `estricto=True` un `PARAM_TIPOHECHO` fuera del catálogo levanta
    `HechoRuvDesconocido` en vez de descartarse en silencio: si el RUV amplía su
    catálogo queremos enterarnos acá y no que la persona pierda el hecho.
    """
    documento = (documento or "").strip()
    if not documento:
        return LecturaHechos(documento="", personas_ruv=0, hechos=())

    cursor.execute(SQL_HECHOS_POR_DOCUMENTO, {"documento": documento})
    filas = cursor.fetchall()

    personas = {fila[5] for fila in filas}
    if len(personas) > 1:
        # Ambiguo: el número resuelve a más de una persona del RUV. No se elige.
        return LecturaHechos(
            documento=documento, personas_ruv=len(personas), hechos=()
        )

    hechos = []
    for id_ruv, tipo, fecha, id_dpto, id_mpio, _ in filas:
        codigo = HECHO_RUV_A_SICAV.get(tipo)
        if codigo is None:
            if estricto:
                raise HechoRuvDesconocido(
                    f"PARAM_TIPOHECHO={tipo!r} no está en el catálogo del RUV "
                    f"(documento {documento}). El catálogo pudo haber cambiado: "
                    f"revisar RUV.TBHECHOS_VICTIMIZANTES antes de escribir."
                )
            continue
        hechos.append(
            HechoLeido(
                id_ruv=int(id_ruv),
                codigo_sicav=codigo,
                fecha=_a_fecha(fecha),
                id_departamento=int(id_dpto) if id_dpto is not None else None,
                id_municipio=int(id_mpio) if id_mpio is not None else None,
            )
        )

    return LecturaHechos(
        documento=documento,
        personas_ruv=len(personas),
        hechos=tuple(hechos),
    )


# ── Persistencia ─────────────────────────────────────────────────────────────
# Lo de arriba solo lee. Esto es lo único que toca el ORM, y va acá y no en un
# módulo aparte porque separarlo obligaría a leer dos archivos para entender un
# solo asunto.

@dataclasses.dataclass
class ResultadoSync:
    """Qué pasó al sincronizar los hechos de UNA víctima."""

    documento: str
    personas_ruv: int = 0
    leidos: int = 0
    creados: int = 0
    ya_estaban: int = 0
    #: Códigos que el RUV trajo pero que no existen en `CatalogoHechoVictimizante`.
    sin_catalogo: tuple[str, ...] = ()

    @property
    def es_ambigua(self) -> bool:
        return self.personas_ruv > 1

    def __str__(self) -> str:
        if self.es_ambigua:
            return (f"documento {self.documento}: AMBIGUO "
                    f"({self.personas_ruv} personas en el RUV), no se escribió nada")
        return (f"documento {self.documento}: {self.leidos} leído(s), "
                f"{self.creados} nuevo(s), {self.ya_estaban} ya estaba(n)")


def sincronizar_hechos(victima, cursor, *, estricto: bool = True,
                       guardar: bool = True) -> ResultadoSync:
    """
    Trae del RUV los hechos de `victima` y los deja en `HechoVictima`.

    Es **idempotente**: la unicidad por `(fuente, id_origen)` hace que volver a
    correrlo no duplique nada, así que se puede repetir sin miedo.

    Con `guardar=False` hace todo el trabajo menos escribir — el DRY-RUN que usa
    el resto de esta capa.

    Una lectura ambigua **no escribe nada**: ver el encabezado del módulo.
    """
    # Import diferido: mantiene este módulo importable sin Django cargado, igual
    # que el import de `oracledb` en `conexion.py`.
    from apps.victimas.models import CatalogoHechoVictimizante, HechoVictima

    documento = getattr(victima, "numero_documento", "") or ""
    lectura = leer_hechos(cursor, documento, estricto=estricto)

    res = ResultadoSync(
        documento=lectura.documento,
        personas_ruv=lectura.personas_ruv,
        leidos=len(lectura.hechos),
    )
    if lectura.es_ambigua or not lectura.hechos:
        return res

    catalogo = {c.codigo: c for c in CatalogoHechoVictimizante.objects.all()}
    ya = set(
        HechoVictima.objects
        .filter(victima=victima, fuente="RUV")
        .exclude(id_origen="")
        .values_list("id_origen", flat=True)
    )

    sin_catalogo, nuevos = [], []
    for h in lectura.hechos:
        if str(h.id_ruv) in ya:
            res.ya_estaban += 1
            continue
        entrada = catalogo.get(h.codigo_sicav)
        if entrada is None:
            # El catálogo de SICAV no está cargado o le falta el código. No se
            # inventa la fila: se reporta para que alguien cargue el fixture.
            sin_catalogo.append(h.codigo_sicav)
            continue
        nuevos.append(HechoVictima(
            victima=victima,
            hecho=entrada,
            fecha_hecho=h.fecha,
            # `lugar_hecho` queda NULL a propósito: los ids del RUV son
            # surrogate. Se conservan en texto para no perderlos.
            lugar_hecho=None,
            fuente="RUV",
            id_origen=str(h.id_ruv),
            observaciones=(
                f"RUV TBSINIESTROS_PERSONA.ID={h.id_ruv}"
                + (f" · dpto={h.id_departamento} mpio={h.id_municipio}"
                   if h.tiene_lugar else "")
            ),
        ))

    res.sin_catalogo = tuple(dict.fromkeys(sin_catalogo))
    res.creados = len(nuevos)
    if guardar and nuevos:
        HechoVictima.objects.bulk_create(nuevos, ignore_conflicts=True)
    return res
