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
    """SHA-256 (hex, minúsculas) de la cadena canónica del documento."""
    canon = normalizar_doc(tipo_documento, numero_documento)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()


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
    estado_ruv: str                    # INCLUIDO, NO_INCLUIDO, EN_PROCESO, EXCLUIDO
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
    fuente: str                         # MOCK, RUV, ORACLE, REGISTRADURIA
    mensaje: str = ''


@dataclass
class EstadoHabilitacion:
    """Resultado de verificar si una persona puede ser caracterizada."""
    habilitado: bool
    razon: str = ''                     # descripción si no habilitado


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
    ) -> ResultadoBusqueda:
        """
        Busca una víctima por tipo y número de documento.

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
    def listar_todas(self) -> list[VictimaResumen]:
        """
        Devuelve TODAS las víctimas conocidas por la fuente (padrón completo).

        Pensado para la precarga offline: la APK descarga de una sola vez el
        padrón con el que el encuestador trabajará sin conexión.

        En el mock retorna los ~11 casos ficticios. En Oracle/producción esta
        operación debe acotarse (por jornada, punto de atención o territorial)
        antes de exponerse — un padrón nacional completo no debe materializarse.

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
