"""
Implementación mock del repositorio de víctimas — solo para desarrollo y tests.

TODOS LOS DATOS SON 100 % FICTICIOS.
Ningún nombre, cédula ni fecha corresponde a personas reales.
Los números de documento empiezan con 999 para distinguirlos de cédulas reales.

Casos cubiertos (9990100001–10):
  1. Incluida en RUV, desplazada, con grupo familiar de 2 miembros
  2. Incluida y habilitada (demo — antes: solo Registraduría / no incluida)
  3. Incluida y habilitada (demo — antes: ya caracterizada / no habilitada)
  4. Menor de edad incluida en RUV — flujo tutor (tipo_persona 5002)
  5. Adulto con discapacidad severa — flujo cuidador permanente (tipo_persona 5003)
  6. Incluida con todos los hechos victimizantes HV01-HV13
  7. Incluida y habilitada (demo — antes: no encontrada)
  8. Incluida y habilitada (demo — antes: excluida del RUV)
  9. Con grupo familiar numeroso (5 miembros: adulto, cónyuge, 3 hijos)
 10. Mujer indígena NASA, municipio rural Cauca — flujo instrumento TERRITORIAL

Nota (demo funcional): 9990100001–10 quedan TODAS habilitadas para caracterización
(el 9990100005 conserva su caso de discapacidad/cuidador). Para probar el resultado
"no encontrado" se puede buscar cualquier documento ausente del padrón.
"""
from __future__ import annotations

from datetime import date, datetime

from .base import (
    EstadoHabilitacion,
    HechoResumen,
    ResultadoBusqueda,
    VictimaRepository,
    VictimaResumen,
    describir_elegibilidad,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _v(
    cons: int,
    tdoc: str,
    ndoc: str,
    p1: str, p2: str, a1: str, a2: str,
    fn: date,
    gen: str,
    estado_ruv: str,
    habilitado: bool,
    etnia: str = 'NINGUNA',
    pueblo: str = '',
    discapacidad: bool = False,
    tipo_disc: str = '',
    hechos: list | None = None,
    mpio_cod: str | None = None,
    mpio_nom: str | None = None,
    fuente: str = 'RUV',
    ult_caract: datetime | None = None,
) -> VictimaResumen:
    return VictimaResumen(
        cons_persona=cons,
        tipo_documento=tdoc,
        numero_documento=ndoc,
        primer_nombre=p1,
        segundo_nombre=p2,
        primer_apellido=a1,
        segundo_apellido=a2,
        fecha_nacimiento=fn,
        genero=gen,
        estado_ruv=estado_ruv,
        habilitado_para_caracterizacion=habilitado,
        fecha_ult_caracterizacion=ult_caract,
        pertenencia_etnica=etnia,
        pueblo_indigena=pueblo,
        discapacidad=discapacidad,
        tipo_discapacidad=tipo_disc,
        hechos_victimizantes=hechos or [],
        municipio_residencia_codigo=mpio_cod,
        municipio_residencia_nombre=mpio_nom,
        fuente_origen=fuente,
        # En producción esto NO sale de `estado_ruv` —ese campo venía del join
        # roto por `CONS_PERONA`— sino de cruzar el documento contra el universo
        # del RUV; ver `iterar_padron` en `django_orm.py`.
        #
        # Acá sí puede derivarse del estado, y no es una excepción a la regla: el
        # mock son datos inventados y consistentes consigo mismos, sin ningún join
        # de por medio del que desconfiar. Sirve para que el padrón de pruebas
        # tenga fichas con el bit encendido y con él apagado.
        en_universo_ruv=(estado_ruv == 'INCLUIDO'),
    )


def _h(codigo: str, nombre: str, fecha: date | None = None, mpio: str | None = None) -> HechoResumen:
    return HechoResumen(codigo=codigo, nombre=nombre, fecha_hecho=fecha, municipio_hecho=mpio)


# ---------------------------------------------------------------------------
# Catálogo mínimo de hechos (nombres ficticios de trabajo, confirmar con UARIV)
# ---------------------------------------------------------------------------

_HECHOS_NOMBRE = {
    'HV01': 'Desplazamiento forzado',
    'HV02': 'Acto terrorista / Atentado / Combate',
    'HV03': 'Amenaza',
    'HV04': 'Delitos contra la libertad e integridad sexual',
    'HV05': 'Desaparición forzada',
    'HV06': 'Homicidio',
    'HV07': 'Minas antipersonal / artefacto explosivo',
    'HV08': 'Secuestro',
    'HV09': 'Tortura',
    'HV10': 'Vinculación de NNA a grupos armados',
    'HV11': 'Abandono o despojo forzado de tierras',
    'HV12': 'Pérdida de bienes muebles o inmuebles',
    'HV13': 'Confinamiento',
}


# ---------------------------------------------------------------------------
# Dataset: índice por (tipo_documento, numero_documento)
# ---------------------------------------------------------------------------

_VICTIMAS: dict[tuple[str, str], VictimaResumen] = {}

# ── Caso 1: Incluida, desplazada, con grupo familiar ────────────────────────
_CASO1 = _v(
    cons=10001,
    tdoc='CC', ndoc='9990100001',
    p1='María', p2='Esperanza', a1='Rojas', a2='Mendoza',
    fn=date(1980, 5, 15), gen='F',
    estado_ruv='INCLUIDO', habilitado=True,
    hechos=[
        _h('HV01', _HECHOS_NOMBRE['HV01'], date(2005, 3, 10), 'Turbo (Antioquia)'),
        _h('HV03', _HECHOS_NOMBRE['HV03'], date(2005, 2, 1), 'Turbo (Antioquia)'),
    ],
    mpio_cod='05001', mpio_nom='Medellín',
)
_VICTIMAS[('CC', '9990100001')] = _CASO1

# ── Caso 2: (demo) INCLUIDA y habilitada — antes solo Registraduría ──────────
_CASO2 = _v(
    cons=10002,
    tdoc='CC', ndoc='9990100002',
    p1='Pedro', p2='Camilo', a1='Torres', a2='Herrera',
    fn=date(1975, 3, 22), gen='M',
    estado_ruv='INCLUIDO', habilitado=True,
    hechos=[_h('HV01', _HECHOS_NOMBRE['HV01'], date(2006, 4, 12), 'Tumaco (Nariño)')],
    mpio_cod='52835', mpio_nom='Tumaco',
)
_VICTIMAS[('CC', '9990100002')] = _CASO2

# ── Caso 3: (demo) habilitada — antes marcada como ya caracterizada ─────────
_CASO3 = _v(
    cons=10003,
    tdoc='CC', ndoc='9990100003',
    p1='Ana', p2='Lucía', a1='Pinto', a2='Salcedo',
    fn=date(1988, 11, 30), gen='F',
    estado_ruv='INCLUIDO', habilitado=True,
    hechos=[_h('HV01', _HECHOS_NOMBRE['HV01'], date(2018, 6, 20), 'Buenaventura')],
    mpio_cod='76001', mpio_nom='Cali',
)
_VICTIMAS[('CC', '9990100003')] = _CASO3

# ── Caso 4: Menor de edad incluida en RUV — flujo tutor ─────────────────────
_CASO4 = _v(
    cons=10004,
    tdoc='RC', ndoc='9990100004',
    p1='Santiago', p2='', a1='de las Flores', a2='Martínez',
    fn=date(2015, 8, 10), gen='M',
    estado_ruv='INCLUIDO', habilitado=True,
    hechos=[_h('HV01', _HECHOS_NOMBRE['HV01'], date(2016, 1, 5), 'El Carmen de Bolívar')],
    mpio_cod='13001', mpio_nom='Cartagena',
)
_VICTIMAS[('RC', '9990100004')] = _CASO4

# ── Caso 5: Adulto con discapacidad severa — flujo cuidador permanente ───────
_CASO5 = _v(
    cons=10005,
    tdoc='CC', ndoc='9990100005',
    p1='Rosario', p2='del Carmen', a1='Valencia', a2='Ríos',
    fn=date(1955, 1, 30), gen='F',
    estado_ruv='INCLUIDO', habilitado=True,
    discapacidad=True,
    tipo_disc='Física — parálisis de miembros inferiores (silla de ruedas)',
    hechos=[
        _h('HV01', _HECHOS_NOMBRE['HV01'], date(2001, 8, 15), 'Tibú (Norte de Santander)'),
        _h('HV09', _HECHOS_NOMBRE['HV09'], date(2001, 8, 15), 'Tibú (Norte de Santander)'),
    ],
    mpio_cod='54001', mpio_nom='Cúcuta',
)
_VICTIMAS[('CC', '9990100005')] = _CASO5

# ── Caso 6: Con todos los hechos victimizantes HV01-HV13 ────────────────────
_CASO6 = _v(
    cons=10006,
    tdoc='CC', ndoc='9990100006',
    p1='Héctor', p2='Fabio', a1='Quintero', a2='Ossa',
    fn=date(1968, 7, 4), gen='M',
    estado_ruv='INCLUIDO', habilitado=True,
    hechos=[
        _h(cod, nom, date(2000 + i, 1, 1))
        for i, (cod, nom) in enumerate(_HECHOS_NOMBRE.items())
    ],
    mpio_cod='05001', mpio_nom='Medellín',
)
_VICTIMAS[('CC', '9990100006')] = _CASO6

# ── Caso 7: (demo) INCLUIDA y habilitada — antes "no encontrada" ─────────────
_CASO7 = _v(
    cons=10007,
    tdoc='CC', ndoc='9990100007',
    p1='Marta', p2='Cecilia', a1='Beltrán', a2='Nieto',
    fn=date(1983, 2, 14), gen='F',
    estado_ruv='INCLUIDO', habilitado=True,
    hechos=[_h('HV01', _HECHOS_NOMBRE['HV01'], date(2009, 7, 8), 'Apartadó (Antioquia)')],
    mpio_cod='05001', mpio_nom='Medellín',
)
_VICTIMAS[('CC', '9990100007')] = _CASO7
# Documento reservado para probar el resultado "no encontrado" (cualquier
# cédula ausente del padrón devuelve encontrado=False; ya no se usa el 007).
_NDOC_NO_ENCONTRADO = ('CC', '9990199999')

# ── Caso 8: (demo) INCLUIDA y habilitada — antes excluida del RUV ────────────
_CASO8 = _v(
    cons=10008,
    tdoc='CC', ndoc='9990100008',
    p1='Bernardo', p2='Augusto', a1='Morales', a2='Peña',
    fn=date(1960, 4, 18), gen='M',
    estado_ruv='INCLUIDO', habilitado=True,
    hechos=[_h('HV06', _HECHOS_NOMBRE['HV06'], date(2003, 10, 2), 'Bogotá D.C.')],
    mpio_cod='11001', mpio_nom='Bogotá D.C.',
)
_VICTIMAS[('CC', '9990100008')] = _CASO8

# ── Caso 9: Grupo familiar numeroso (5 miembros) ────────────────────────────
_CASO9 = _v(
    cons=10009,
    tdoc='CC', ndoc='9990100009',
    p1='Gloria', p2='Isabel', a1='Mosquera', a2='Cerón',
    fn=date(1972, 9, 7), gen='F',
    estado_ruv='INCLUIDO', habilitado=True,
    hechos=[_h('HV01', _HECHOS_NOMBRE['HV01'], date(2010, 5, 3), 'Quibdó')],
    mpio_cod='27001', mpio_nom='Quibdó',
)
_VICTIMAS[('CC', '9990100009')] = _CASO9

# ── Caso 10: Mujer indígena NASA — municipio rural Cauca ────────────────────
_CASO10 = _v(
    cons=10010,
    tdoc='CC', ndoc='9990100010',
    p1='Lucía', p2='Neiza', a1='Yule', a2='Tombé',
    fn=date(1990, 11, 25), gen='F',
    estado_ruv='INCLUIDO', habilitado=True,
    etnia='INDIGENA', pueblo='NASA (Páez)',
    hechos=[
        _h('HV01', _HECHOS_NOMBRE['HV01'], date(2012, 9, 18), 'Toribío (Cauca)'),
        _h('HV11', _HECHOS_NOMBRE['HV11'], date(2012, 9, 18), 'Toribío (Cauca)'),
    ],
    mpio_cod='19001', mpio_nom='Popayán',
)
_VICTIMAS[('CC', '9990100010')] = _CASO10

# ── Caso 11: Usuario de prueba del contratista — CC 1030547250 ───────────────
_CASO11 = _v(
    cons=10011,
    tdoc='CC', ndoc='1030547250',
    p1='JAVIER', p2='ALEXANDER', a1='AGUILAR', a2='CASTRO',
    fn=date(1990, 1, 1), gen='M',
    estado_ruv='INCLUIDO', habilitado=True,
    hechos=[
        _h('HV01', _HECHOS_NOMBRE['HV01'], date(2010, 4, 15), 'Bogotá D.C.'),
    ],
    mpio_cod='11001', mpio_nom='Bogotá D.C.',
)
_VICTIMAS[('CC', '1030547250')] = _CASO11


# ---------------------------------------------------------------------------
# Grupos familiares: cons_persona → miembros adicionales (sin repetir al jefe)
# ---------------------------------------------------------------------------

_GRUPOS: dict[int, list[VictimaResumen]] = {

    # Caso 1: Gloria + esposo + hija menor
    10001: [
        _CASO1,
        _v(
            cons=10001, tdoc='CC', ndoc='9990200001',
            p1='Carlos', p2='Andrés', a1='Rojas', a2='Mendoza',
            fn=date(1978, 2, 11), gen='M',
            estado_ruv='INCLUIDO', habilitado=True,
            hechos=[_h('HV01', _HECHOS_NOMBRE['HV01'], date(2005, 3, 10), 'Turbo')],
            mpio_cod='05001', mpio_nom='Medellín',
        ),
        _v(
            cons=10001, tdoc='RC', ndoc='9990200002',
            p1='Valentina', p2='', a1='Rojas', a2='Mendoza',
            fn=date(2008, 6, 20), gen='F',
            estado_ruv='INCLUIDO', habilitado=True,
            hechos=[_h('HV01', _HECHOS_NOMBRE['HV01'], date(2008, 7, 1))],
            mpio_cod='05001', mpio_nom='Medellín',
        ),
    ],

    # Caso 9: familia numerosa — jefe, cónyuge, 3 hijos
    10009: [
        _CASO9,
        _v(
            cons=10009, tdoc='CC', ndoc='9990200010',
            p1='Freddy', p2='Alonso', a1='Córdoba', a2='Palacios',
            fn=date(1970, 3, 15), gen='M',
            estado_ruv='INCLUIDO', habilitado=True,
            hechos=[_h('HV01', _HECHOS_NOMBRE['HV01'], date(2010, 5, 3))],
            mpio_cod='27001', mpio_nom='Quibdó',
        ),
        _v(
            cons=10009, tdoc='TI', ndoc='9990200011',
            p1='Leidy', p2='Johana', a1='Córdoba', a2='Mosquera',
            fn=date(2007, 7, 22), gen='F',
            estado_ruv='INCLUIDO', habilitado=True,
            hechos=[],
            mpio_cod='27001', mpio_nom='Quibdó',
        ),
        _v(
            cons=10009, tdoc='TI', ndoc='9990200012',
            p1='Duván', p2='', a1='Córdoba', a2='Mosquera',
            fn=date(2010, 1, 9), gen='M',
            estado_ruv='INCLUIDO', habilitado=True,
            hechos=[],
            mpio_cod='27001', mpio_nom='Quibdó',
        ),
        _v(
            cons=10009, tdoc='RC', ndoc='9990200013',
            p1='Dariana', p2='', a1='Córdoba', a2='Mosquera',
            fn=date(2016, 4, 3), gen='F',
            estado_ruv='EN_PROCESO', habilitado=False,
            hechos=[],
            mpio_cod='27001', mpio_nom='Quibdó',
        ),
        _v(
            cons=10009, tdoc='RC', ndoc='9990200014',
            p1='Jesús', p2='David', a1='Córdoba', a2='Mosquera',
            fn=date(2019, 11, 30), gen='M',
            estado_ruv='EN_PROCESO', habilitado=False,
            hechos=[],
            mpio_cod='27001', mpio_nom='Quibdó',
        ),
    ],
}


# ---------------------------------------------------------------------------
# Implementación MockVictimaRepository
# ---------------------------------------------------------------------------

class MockVictimaRepository(VictimaRepository):
    """
    Repositorio mock para desarrollo y tests automatizados.

    Cubre los 10 casos de prueba definidos en el diseño del Paso B.
    Buscar un documento no registrado devuelve encontrado=False limpio
    (equivale al caso 7 para cualquier cédula desconocida).
    """

    FUENTE = 'MOCK'

    def buscar_por_documento(
        self,
        tipo_documento: str,
        numero_documento: str,
        *,
        ruta=None,
    ) -> ResultadoBusqueda:
        clave = (tipo_documento.upper(), numero_documento.strip())
        victima = _VICTIMAS.get(clave)

        # El veredicto sale de `describir_elegibilidad`, igual que en el
        # repositorio real. Antes el mock tenía su propio árbol y decía cosas
        # distintas para la misma situación —"No se encontró registro en RUV ni
        # en Registraduría" contra "No se encontró la persona en el padrón"—, así
        # que las pruebas contra mock validaban textos que producción nunca
        # emitía.
        veredicto = describir_elegibilidad(victima, ruta=ruta)
        return ResultadoBusqueda(
            encontrado=victima is not None,
            victima=victima,
            fuente=self.FUENTE,
            mensaje=veredicto.mensaje,
            motivo=veredicto.motivo,
            disponible_desde=veredicto.disponible_desde,
        )

    def listar_todas(self, limite: int | None = None) -> list[VictimaResumen]:
        # Padrón completo del mock: las víctimas indexadas por documento.
        # No incluye a los miembros de grupo familiar que no tienen entrada
        # propia en _VICTIMAS (esos se obtienen vía obtener_grupo_familiar).
        todas = list(_VICTIMAS.values())
        return todas[:limite] if limite is not None else todas

    def iterar_padron(self, batch_size: int = 1000):
        """
        Itera el padrón del mock en streaming (yield por registro).

        En el mock el dataset es minúsculo, así que iteramos ``_VICTIMAS`` y
        hacemos yield uno por uno — el ``batch_size`` es irrelevante aquí pero
        se respeta la firma.

        EN ORACLE (producción) este método NO debe materializar todo: debe
        ejecutar la consulta del padrón con un **server-side cursor** y un bucle
        ``while True: rows = cursor.fetchmany(batch_size); if not rows: break``,
        haciendo ``yield`` de cada fila convertida a ``VictimaResumen``. Así el
        command ``generar_padron`` escribe el archivo en streaming sin cargar
        10M registros en RAM. Este es el único punto que cambia al enchufar Oracle.
        """
        for victima in _VICTIMAS.values():
            yield victima

    def obtener_grupo_familiar(
        self,
        cons_persona: int,
    ) -> list[VictimaResumen]:
        return list(_GRUPOS.get(cons_persona, []))

    def verificar_habilitacion(
        self,
        tipo_documento: str,
        numero_documento: str,
        *,
        ruta=None,
    ) -> EstadoHabilitacion:
        veredicto = describir_elegibilidad(
            _VICTIMAS.get((tipo_documento.upper(), numero_documento.strip())),
            ruta=ruta,
        )
        return EstadoHabilitacion(
            habilitado=veredicto.elegible,
            razon=veredicto.mensaje,
            motivo=veredicto.motivo,
            disponible_desde=veredicto.disponible_desde,
        )
