"""
Contrato del repositorio de víctimas SRNI.

VictimaRepository define el contrato que cualquier fuente de datos debe implementar.
Los DTOs (HechoResumen, VictimaResumen, ResultadoBusqueda, EstadoHabilitacion)
son la interfaz entre el repositorio y el resto del sistema.

Implementaciones actuales / previstas:
  MockVictimaRepository  — 10 casos de prueba, 100 % ficticios (desarrollo/tests)
  OracleVictimaRepository — consulta los SPs del sistema legado Oracle (producción)

Regla de oro: cambiar la fuente de datos = cambiar la implementación.
Los endpoints, serializers y lógica de negocio NO deben saber qué implementación usan.
"""
from __future__ import annotations

import hashlib
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Normalización canónica del documento → doc_hash del padrón offline
# ---------------------------------------------------------------------------
#
# CONTRATO DE NORMALIZACIÓN (debe ser idéntico en backend y en la APK):
#
#   1. tipo_documento y numero_documento se concatenan con '|' como separador:
#        f"{tipo}|{numero}"
#   2. Antes de concatenar, cada parte se normaliza así:
#        - strip() de espacios al inicio/fin
#        - se eliminan espacios, puntos y guiones internos (separadores de miles)
#        - to lower-case (minúsculas)
#        - se quitan acentos/diacríticos (NFKD → ASCII) por robustez
#   3. doc_hash = sha256(cadena_utf8).hexdigest()  (64 chars hex, minúsculas)
#
# Ejemplo:  ('CC', '99.901.000-01')  → "cc|9990100001" → sha256(...) hex
#
# La APK DEBE replicar EXACTAMENTE estos pasos para que el hash que calcula al
# buscar un documento coincida con el doc_hash almacenado en el padrón.

def normalizar_doc(tipo_documento: str, numero_documento: str) -> str:
    """Devuelve la cadena canónica '<tipo>|<numero>' lista para hashear."""
    def _limpiar(parte: str) -> str:
        s = (parte or '').strip()
        # quitar separadores comunes de miles / formato
        for ch in (' ', '.', '-'):
            s = s.replace(ch, '')
        s = s.lower()
        # quitar acentos/diacríticos
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(c for c in s if not unicodedata.combining(c))
        return s

    return f"{_limpiar(tipo_documento)}|{_limpiar(numero_documento)}"


def doc_hash(tipo_documento: str, numero_documento: str) -> str:
    """
    SHA-256 (hex, minúsculas) de la cadena canónica del documento.

    Es el hash de IDENTIDAD y la única definición válida: la usan el modelo
    (`Victima.save`), la búsqueda, el upsert y el generador del padrón. Si alguien
    necesita hashear un documento, es esta función — no una fórmula propia.
    """
    canon = normalizar_doc(tipo_documento, numero_documento)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()


def num_hash(numero_documento: str) -> str:
    """
    SHA-256 solo del NÚMERO, sin el tipo. Índice de RESPALDO, no de identidad.

    Para qué: en la fuente hay 1.126.615 personas (14,5 %) sin tipo de documento
    registrado. Su hash de identidad se calcula con tipo vacío, así que un encuestador
    que busque "CC + número" no las encontraría nunca. Este índice permite hallarlas
    y advertirle que verifique, en vez de inventarles el tipo o perderlas.

    ⚠️ No sirve para identificar: dos personas distintas pueden compartir número con
    tipos diferentes (una CC y una TI). Un acierto por este índice es un CANDIDATO a
    confirmar por el encuestador, nunca una identificación.
    """
    _, numero = normalizar_doc('', numero_documento).split('|', 1)
    return hashlib.sha256(numero.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# Data Transfer Objects
# ---------------------------------------------------------------------------

@dataclass
class HechoResumen:
    """Hecho victimizante asociado a una víctima."""
    codigo: str                        # HV01 … HV14
    nombre: str
    fecha_hecho: Optional[date] = None
    municipio_hecho: Optional[str] = None   # nombre libre — no FK en este contexto


@dataclass
class VictimaResumen:
    """
    Datos de una víctima retornados por el repositorio.

    Todos los campos son texto plano: el repositorio devuelve el dato ya
    descifrado / consultado desde la fuente. El cifrado es responsabilidad
    de la capa de persistencia Django, no de este contrato.
    """
    # Identificación
    cons_persona: Optional[int]        # consecutivo Oracle — None si no viene del legado
    tipo_documento: str                # 'CC', 'CE', 'PA', 'RC', 'TI', etc.
    numero_documento: str
    primer_nombre: str
    segundo_nombre: str
    primer_apellido: str
    segundo_apellido: str
    fecha_nacimiento: date
    genero: str                        # M, F, NB, ND

    # Estado en el RUV
    estado_ruv: str                    # INCLUIDO, NO_INCLUIDO, EN_PROCESO, EXCLUIDO, NO_VERIFICADO
    habilitado_para_caracterizacion: bool
    fecha_ult_caracterizacion: Optional[datetime]

    # Demografía
    pertenencia_etnica: str            # NINGUNA, INDIGENA, AFROCOLOMBIANO, ROM, RAIZAL, PALENQUERO
    pueblo_indigena: str               # solo si etnia == INDIGENA
    discapacidad: bool
    tipo_discapacidad: str

    # Hechos victimizantes
    hechos_victimizantes: list[HechoResumen] = field(default_factory=list)

    # Municipio de residencia
    municipio_residencia_codigo: Optional[str] = None   # código DIVIPOLA 5 dígitos
    municipio_residencia_nombre: Optional[str] = None

    # Origen del dato
    fuente_origen: str = 'RUV'         # RUV, REGISTRADURIA, SNARIV, MANUAL

    # Cuando varias personas comparten el documento. `None` = documento limpio o
    # sin clasificar; los valores son los de `ColisionDocumento.CLASE`.
    #
    # Existe para que el padrón descargable pueda decir "acá hay que confirmar" sin
    # recalcular nada en el dispositivo: la clasificación es cara (descifra nombres
    # y fechas de millones de filas) y se hace una sola vez, en el servidor.
    clase_colision: Optional[str] = None


@dataclass
class ResultadoBusqueda:
    """
    Resultado de buscar una víctima por documento.

    Si encontrado=False, victima es None y mensaje explica la razón.
    Si encontrado=True pero habilitado_para_caracterizacion=False,
    el campo victima.habilitado_para_caracterizacion lo indica y
    mensaje describe el motivo (ya caracterizada, excluida, etc.).
    """
    encontrado: bool
    victima: Optional[VictimaResumen]
    fuente: str                         # MOCK, RUV, ORACLE, REGISTRADURIA, SICAV
    mensaje: str = ''

    # Otros registros que comparten el documento buscado. Normalmente vacío.
    #
    # Existe porque en la fuente hay 1.552.622 números de documento repetidos, y esos
    # duplicados NO se fusionan al cargar: dos registros con el mismo número pueden
    # ser dos personas distintas (una CC y una TI), y con el 14,5 % sin tipo no
    # siempre se puede distinguir. Fusionar por regla mezclaría dos víctimas en una
    # —una persona desaparecería del padrón—, así que se cargan ambas y **decide el
    # encuestador**, que tiene a la persona enfrente y puede preguntarle el nombre.
    #
    # `victima` trae el candidato más completo; `candidatos` los demás. Si esta lista
    # no está vacía, la UI DEBE pedir confirmación en vez de asumir el primero.
    candidatos: list = field(default_factory=list)

    # El documento buscado es un valor de RELLENO del padrón ('99', '0', '999999'):
    # no identifica a nadie. Va aparte de `encontrado=False` porque no significan lo
    # mismo y la app no debe decir lo mismo: "no está en el padrón" manda al
    # encuestador a dar de alta a alguien que quizá SÍ está —solo que ese número no
    # sirve para hallarlo—. `mensaje` explica; esta bandera permite que la interfaz
    # cambie el título en vez de tener que adivinar leyendo el texto.
    no_identificante: bool = False

    # POR QUÉ, en forma de código y no de prosa. Ver `MotivoNoElegible`.
    #
    # `mensaje` se sigue enviando y sigue siendo lo que se le muestra a la
    # persona, pero la interfaz ya no tiene que leer el texto para saber qué
    # ofrecer: con `motivo` decide el botón, y con `disponible_desde` puede
    # decir "vuelva a intentar el …" sin conocer la regla de vigencia.
    motivo: str = ''
    disponible_desde: Optional[date] = None


@dataclass
class EstadoHabilitacion:
    """Resultado de verificar si una persona puede ser caracterizada."""
    habilitado: bool
    razon: str = ''                     # descripción si no habilitado

    # Mismo motivo enumerado que `ResultadoBusqueda`. Ver `MotivoNoElegible`.
    motivo: str = ''
    disponible_desde: Optional[date] = None


# ---------------------------------------------------------------------------
# Por qué NO se puede caracterizar — un solo lugar
# ---------------------------------------------------------------------------

class MotivoNoElegible:
    """
    Motivo enumerado del veredicto, además del texto para el humano.

    ─── Por qué hace falta ───────────────────────────────────────────────────
    Antes el porqué viajaba **solo** como texto libre en `mensaje`, y eso tenía
    una consecuencia concreta: la app no podía ofrecer la salida correcta porque
    no sabía en qué caso estaba. Solo podía pintar la cadena. Por eso todo
    terminaba en un mensaje sin botón, y en campo un bloqueo previsto **se lee
    como una falla del sistema**.

    Con el motivo, la interfaz decide: `NO_EN_PADRON` → "Dar de alta";
    `FICHA_VIGENTE` → "Registrar ruta de excepción". El texto sigue estando,
    pero ya no es lo único.
    """

    ELEGIBLE = 'ELEGIBLE'
    #: Tenía ficha vigente, pero se entra por una ruta que omite la vigencia
    #: (Manual §5.1.1). **Exige soporte**: es saltarse un control, y sin rastro
    #: la regla de vigencia se vuelve opcional en la práctica.
    ELEGIBLE_POR_EXCEPCION = 'ELEGIBLE_POR_EXCEPCION'
    #: No está en el padrón de SICAV. **No significa "no es víctima"**: el padrón
    #: se armó desde el legacy, así que hay víctimas del RUV que no están acá.
    NO_EN_PADRON = 'NO_EN_PADRON'
    #: El número es un valor de relleno ('99', '0'…) y no identifica a nadie.
    DOCUMENTO_NO_IDENTIFICANTE = 'DOCUMENTO_NO_IDENTIFICANTE'
    #: Excluida del RUV. No hay ruta de excepción que la habilite.
    EXCLUIDA_RUV = 'EXCLUIDA_RUV'
    #: Tiene entrevista vigente (menos de `ANIOS_VIGENCIA_CARACTERIZACION` años).
    #: **Es el caso masivo**: 1.058.971 personas al 4-ago-2026. Se levanta con
    #: una ruta de excepción, no es un callejón.
    FICHA_VIGENTE = 'FICHA_VIGENTE'
    #: Marcada como no habilitada pero sin fecha que lo explique. No debería
    #: pasar (0 casos medidos en producción); si aparece, es un dato roto.
    BLOQUEADA_SIN_MOTIVO = 'BLOQUEADA_SIN_MOTIVO'


@dataclass(frozen=True)
class Elegibilidad:
    """Veredicto sobre una persona: el motivo, el texto y hasta cuándo."""

    motivo: str
    mensaje: str = ''
    disponible_desde: Optional[date] = None

    @property
    def elegible(self) -> bool:
        return self.motivo in (MotivoNoElegible.ELEGIBLE,
                               MotivoNoElegible.ELEGIBLE_POR_EXCEPCION)

    @property
    def exige_soporte(self) -> bool:
        """Entró por una ruta de excepción: hay que adjuntar el soporte."""
        return self.motivo == MotivoNoElegible.ELEGIBLE_POR_EXCEPCION


#: Texto de `NO_EN_PADRON`. Va aparte porque lo usan la búsqueda y la
#: verificación, y porque el anterior —"No se encontró la persona"— se leía como
#: "no es víctima" y mandaba a dar de alta a alguien que quizá ya existe.
MENSAJE_NO_EN_PADRON = (
    'No está en el padrón de SICAV. Puede ser víctima igual: verifique en '
    'Vivanto. Si allí aparece, dele de alta manualmente para continuar.'
)


def describir_elegibilidad(victima, hoy=None, *, ruta=None) -> Elegibilidad:
    """
    Único lugar donde se decide **por qué** alguien no puede caracterizarse.

    Recibe un `victimas.Victima` (el modelo) o cualquier objeto con
    `estado_ruv`, `habilitado_para_caracterizacion` y `fecha_ult_caracterizacion`.
    `None` significa que no está en el padrón.

    `ruta` es la ruta de entrevista (Manual §5.1.1). Tres de las cuatro
    **omiten la regla de vigencia**; ver `RUTAS_QUE_OMITEN_VIGENCIA`. Sin este
    parámetro la ruta no se considera, que es lo correcto para una búsqueda
    normal: primero se ve el estado real, y recién si hay ficha vigente el
    encuestador elige una ruta de excepción.

    Existe porque `buscar_por_documento` y `estado_habilitacion` decidían lo
    mismo por separado —y ya habían empezado a divergir en el texto—. Dos
    respuestas distintas para la misma persona según por dónde entre la app es
    un defecto esperando a ocurrir.
    """
    from ..homologacion import ANIOS_VIGENCIA_CARACTERIZACION, ruta_omite_vigencia

    if victima is None:
        return Elegibilidad(MotivoNoElegible.NO_EN_PADRON, MENSAJE_NO_EN_PADRON)

    if getattr(victima, 'estado_ruv', '') == 'EXCLUIDO':
        return Elegibilidad(
            MotivoNoElegible.EXCLUIDA_RUV,
            'Persona excluida del RUV — no elegible para caracterización. '
            'Ninguna ruta de excepción habilita este caso.',
        )

    if getattr(victima, 'habilitado_para_caracterizacion', False):
        return Elegibilidad(MotivoNoElegible.ELEGIBLE)

    fecha = getattr(victima, 'fecha_ult_caracterizacion', None)
    if not fecha:
        return Elegibilidad(
            MotivoNoElegible.BLOQUEADA_SIN_MOTIVO,
            'No habilitada para caracterización, y no consta la fecha que lo '
            'explique. Repórtelo a soporte: es un dato incompleto, no una regla.',
        )

    if hasattr(fecha, 'date'):
        fecha = fecha.date()
    try:
        disponible = fecha.replace(year=fecha.year + ANIOS_VIGENCIA_CARACTERIZACION)
    except ValueError:
        # 29 de febrero: el año destino no lo tiene. Se corre al 1 de marzo en
        # vez de reventar — un caso al año, pero revienta el día que ocurre.
        disponible = fecha.replace(month=3, day=1,
                                   year=fecha.year + ANIOS_VIGENCIA_CARACTERIZACION)

    # La excepción del manual: tres rutas omiten la vigencia. Se sigue diciendo
    # que la ficha está vigente —el encuestador tiene que saberlo— pero deja de
    # ser un bloqueo y pasa a exigir soporte.
    if ruta_omite_vigencia(ruta):
        return Elegibilidad(
            MotivoNoElegible.ELEGIBLE_POR_EXCEPCION,
            f'Esta persona fue caracterizada el {fecha:%d/%m/%Y} y su entrevista '
            f'estaba vigente hasta el {disponible:%d/%m/%Y}. Puede continuar por '
            f'la ruta seleccionada, que omite la regla de vigencia. '
            f'Adjunte foto del soporte: queda registrado quién autorizó la '
            f'excepción y sobre quién.',
            disponible_desde=disponible,
        )

    # El texto dice las cuatro cosas que el encuestador necesita, en orden:
    # qué pasó, hasta cuándo, que NO es una falla, y cómo continuar. Sin la
    # tercera, en campo un bloqueo previsto se reporta como error del sistema.
    return Elegibilidad(
        MotivoNoElegible.FICHA_VIGENTE,
        f'Esta persona fue caracterizada el {fecha:%d/%m/%Y} y su entrevista '
        f'sigue vigente hasta el {disponible:%d/%m/%Y}. No es una falla del '
        f'sistema. Solo puede caracterizarla por una ruta de excepción '
        f'(acción constitucional, modificación de núcleo familiar o ruta '
        f'especial); si la tiene, tome foto del soporte para continuar.',
        disponible_desde=disponible,
    )


# ---------------------------------------------------------------------------
# Contrato ABC
# ---------------------------------------------------------------------------

class VictimaRepository(ABC):
    """
    Interfaz única de acceso al registro de víctimas.

    Cualquier implementación debe satisfacer este contrato completo.
    Los métodos deben ser llamados con datos ya validados (tipo y número
    de documento no nulos, cons_persona positivo).
    """

    @abstractmethod
    def buscar_por_documento(
        self,
        tipo_documento: str,
        numero_documento: str,
        *,
        ruta: Optional[str] = None,
    ) -> ResultadoBusqueda:
        """
        Busca una víctima por tipo y número de documento.

        `ruta` es la ruta de entrevista, y va acá porque el Manual §5.1.1 la
        pide **en el mismo paso que el documento**: «Diligenciar el número de
        documento con el cual iniciarán la conformación del hogar y establecer
        la ruta respectiva». Tres de las cuatro omiten la regla de vigencia.
        Sin ruta se responde el estado real, que es lo correcto por defecto.

        Retorna ResultadoBusqueda con encontrado=True si la persona existe
        en la fuente de datos, independientemente de su estado en el RUV.
        Jamás lanza excepción por "no encontrado" — eso se modela con encontrado=False.

        Args:
            tipo_documento: código del tipo ('CC', 'CE', 'RC', 'PA', 'TI'…)
            numero_documento: número en texto plano, sin espacios ni puntos

        Returns:
            ResultadoBusqueda
        """

    @abstractmethod
    def obtener_grupo_familiar(
        self,
        cons_persona: int,
    ) -> list[VictimaResumen]:
        """
        Devuelve los integrantes del grupo familiar de la víctima.

        En el sistema Oracle equivale a SP_OBTENER_GRUPO_FAMILIAR.
        El resultado incluye a la víctima principal y sus cohabittantes
        registrados en el RUV/RNI.

        Args:
            cons_persona: consecutivo numérico del sistema Oracle

        Returns:
            Lista de VictimaResumen (puede ser vacía si no hay grupo registrado)
        """

    @abstractmethod
    def listar_todas(self, limite: int | None = None) -> list[VictimaResumen]:
        """
        Devuelve víctimas de la fuente, **hasta ``limite``**.

        Pensado para la precarga offline: lo que la APK baja al login para poder
        trabajar sin conexión en esa jornada.

        ⚠️  ``limite`` no es opcional en la práctica. Con el mock eran 11 casos y
        traer "todas" no costaba nada; con el padrón real son **5,9 millones**, y
        pedirlas sin tope revienta la memoria del proceso y agota el timeout de la
        APK (30 s) sin devolver nada. Pasó: quedó así al activar el padrón real el
        1-ago-2026, y por eso ``PrecargaOfflineView`` ahora siempre pasa un tope.

        El padrón completo **no se sirve por aquí**: va como archivo SQLite
        prearmado por ``padron/download/`` (ver ``generar_padron``), que es
        justamente lo que evita materializar millones de filas en JSON.

        ⚠️  NO usar para construir el padrón descargable a gran escala: materializa
        toda la lista en RAM. Para eso existe ``iterar_padron`` (streaming por lotes).

        Returns:
            Lista de VictimaResumen (puede ser vacía)
        """
        raise NotImplementedError

    def iterar_padron(self, batch_size: int = 1000):
        """
        Itera el padrón completo en LOTES para generación en streaming.

        Es el método que usa el command ``generar_padron`` para construir el
        archivo descargable SIN cargar todo el padrón en memoria. Devuelve un
        generador que entrega ``VictimaResumen`` de a uno (el llamador decide
        cuándo hacer commit por lotes).

        Implementación por fuente:
          - Mock: itera el dict ``_VICTIMAS`` (trivial, cabe en RAM).
          - ORACLE (producción): DEBE abrir un **server-side cursor** (cursor por
            lotes / arraysize) sobre la consulta del padrón y hacer ``fetchmany
            (batch_size)`` en bucle, haciendo ``yield`` de cada registro. Así nunca
            se materializan 10M filas en el proceso Django. Ese es el ÚNICO punto
            donde se enchufa Oracle; ni el command ni los endpoints cambian.

        La implementación por defecto delega en ``listar_todas`` para no romper
        repositorios existentes que aún no la sobrescriban; las fuentes a escala
        DEBEN sobrescribirla con un cursor real.

        Args:
            batch_size: tamaño de lote sugerido para el fetch del cursor.

        Yields:
            VictimaResumen, uno por uno.
        """
        # Fallback genérico (no escalable): solo para fuentes pequeñas.
        for victima in self.listar_todas():
            yield victima

    @abstractmethod
    def verificar_habilitacion(
        self,
        tipo_documento: str,
        numero_documento: str,
        *,
        ruta: Optional[str] = None,
    ) -> EstadoHabilitacion:
        """
        Verifica si la persona puede iniciar una nueva caracterización.

        Es una consulta ligera — no carga el perfil completo ni el grupo
        familiar. Úsala antes de crear el Hogar para fallar rápido si la
        persona ya fue caracterizada, está excluida, etc.

        Args:
            tipo_documento: código del tipo ('CC', 'CE'…)
            numero_documento: número en texto plano

        Returns:
            EstadoHabilitacion
        """
