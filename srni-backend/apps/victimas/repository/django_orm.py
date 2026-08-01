"""
Repositorio de víctimas sobre NUESTRA base (PostgreSQL) — la fuente de verdad de SICAV.

Por qué existe
--------------
Hasta ahora `get_repository()` solo sabía devolver el mock. El modelo `Victima` ya
estaba completo —con PII cifrada, `numero_documento_hash` para buscar sin descifrar,
etnia, discapacidad, estado RUV y hechos victimizantes— pero nada lo leía: la API
seguía respondiendo con los ~11 casos ficticios.

Esta clase cierra ese hueco. Es además la que hace coherente la arquitectura de SICAV:

  * **La APK es offline-first.** En campo no hay señal, así que consultar un servicio
    externo en vivo no es una opción: el encuestador consulta el padrón que descargó.
  * **El padrón descargable se arma desde aquí** (`generar_padron` → `iterar_padron`).
  * **La fuente externa —el RUV— sirve para POBLAR esta tabla, no para consultarla
    cada vez.** Un servicio de consulta individual devuelve una persona por llamada;
    con eso no se llena un padrón de millones. Eso es un proceso de carga aparte.

Seguridad
---------
`numero_documento`, nombres y `fecha_nacimiento` son `EncryptedField` (Fernet), así que
**no se puede filtrar por ellos con un `WHERE`**: el cifrado no es determinista. Toda
búsqueda por documento pasa por `numero_documento_hash` (SHA-256 de la forma canónica),
que es exactamente para lo que ese campo existe.
"""
import datetime
import logging

from .base import (
    EstadoHabilitacion,
    HechoResumen,
    ResultadoBusqueda,
    VictimaRepository,
    VictimaResumen,
    doc_hash,
    num_hash,
)

logger = logging.getLogger(__name__)


def _a_fecha(valor):
    """
    `EncryptedField` devuelve texto al descifrar; el contrato pide `date`.

    Se convierte aquí y no en el modelo para no tocar la capa de persistencia. Un
    valor ilegible devuelve None en vez de reventar: en producción hay fechas de
    nacimiento imposibles (medidas: 142.352 anteriores a 1900 o futuras en el Oracle
    legacy), y una búsqueda no puede fallar por eso.
    """
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    try:
        return datetime.date.fromisoformat(str(valor)[:10])
    except (ValueError, TypeError):
        logger.warning("fecha de nacimiento ilegible en el padrón: %r", valor)
        return None


class DjangoVictimaRepository(VictimaRepository):
    """Lee el padrón desde los modelos Django de SICAV."""

    FUENTE = "SICAV"

    # ── construcción del DTO ──────────────────────────────────────────────────
    def _a_resumen(self, victima, *, con_hechos: bool = True) -> VictimaResumen:
        return VictimaResumen(
            cons_persona=victima.cons_persona,
            tipo_documento=victima.tipo_documento.codigo if victima.tipo_documento_id else "",
            numero_documento=victima.numero_documento or "",
            primer_nombre=victima.primer_nombre or "",
            segundo_nombre=victima.segundo_nombre or "",
            primer_apellido=victima.primer_apellido or "",
            segundo_apellido=victima.segundo_apellido or "",
            fecha_nacimiento=_a_fecha(victima.fecha_nacimiento),
            genero=victima.genero or "",
            estado_ruv=victima.estado_ruv or "",
            habilitado_para_caracterizacion=victima.habilitado_para_caracterizacion,
            fecha_ult_caracterizacion=victima.fecha_ult_caracterizacion,
            pertenencia_etnica=victima.pertenencia_etnica or "",
            pueblo_indigena=victima.pueblo_indigena or "",
            discapacidad=victima.discapacidad,
            tipo_discapacidad=victima.tipo_discapacidad or "",
            hechos_victimizantes=self._hechos(victima) if con_hechos else [],
            municipio_residencia_codigo=(
                victima.municipio_residencia.codigo_dane
                if victima.municipio_residencia_id else None),
            municipio_residencia_nombre=(
                victima.municipio_residencia.nombre
                if victima.municipio_residencia_id else None),
            fuente_origen=victima.fuente_origen or "RUV",
        )

    @staticmethod
    def _hechos(victima) -> list[HechoResumen]:
        return [
            HechoResumen(
                codigo=h.hecho.codigo,
                nombre=h.hecho.nombre,
                fecha_hecho=h.fecha_hecho,
                municipio_hecho=h.lugar_hecho.nombre if h.lugar_hecho_id else None,
            )
            for h in victima.hechos_victimizantes.select_related("hecho", "lugar_hecho")
        ]

    @staticmethod
    def _base_qs():
        """Un solo lugar para el select_related: si se olvida, cada víctima cuesta 3 queries."""
        from apps.victimas.models import Victima
        return Victima.objects.select_related("tipo_documento", "municipio_residencia")

    @staticmethod
    def _completitud(victima) -> int:
        """
        Cuántos campos útiles trae el registro. Ordena los candidatos para ofrecer
        primero el más completo.

        NO decide identidad ni descarta a nadie: solo el orden en que se muestran.
        """
        campos = (victima.primer_nombre, victima.segundo_nombre, victima.primer_apellido,
                  victima.segundo_apellido, victima.fecha_nacimiento, victima.genero,
                  victima.pertenencia_etnica, victima.tipo_discapacidad,
                  victima.municipio_residencia_id, victima.cons_persona,
                  victima.estado_ruv)
        return sum(1 for c in campos if c not in (None, "", 0))

    # ── contrato ──────────────────────────────────────────────────────────────
    def buscar_por_documento(self, tipo_documento, numero_documento) -> ResultadoBusqueda:
        # Por hash, nunca por el campo cifrado: Fernet no es determinista y un
        # `filter(numero_documento=...)` no encontraría jamás nada.
        encontradas = list(self._base_qs().filter(
            numero_documento_hash=doc_hash(tipo_documento, numero_documento)
        ))
        aviso = ""

        if not encontradas:
            # Respaldo: la persona puede estar cargada SIN tipo de documento —14,5 % de
            # la fuente—. Se busca por número solo y se AVISA, en vez de responder "no
            # existe" (que sería falso) o inventarle el tipo.
            encontradas = list(self._base_qs().filter(
                numero_documento_hash_sin_tipo=num_hash(numero_documento)
            ))
            if encontradas:
                aviso = (f"Coincide por número, pero el tipo de documento registrado no "
                         f"es '{tipo_documento}'. VERIFIQUE la identidad. ")

        if not encontradas:
            return ResultadoBusqueda(
                encontrado=False, victima=None, fuente=self.FUENTE,
                mensaje="No se encontró la persona en el padrón cargado en SICAV.",
            )

        # Varios registros con el mismo documento. No se fusionan ni se elige por
        # regla: pueden ser dos personas distintas, y con el 14,5 % sin tipo no
        # siempre se distingue. Se ofrece el más completo primero y los demás van en
        # `candidatos` para que el encuestador confirme.
        encontradas.sort(key=self._completitud, reverse=True)
        victima, otras = encontradas[0], encontradas[1:]
        if otras:
            aviso += (f"Hay {len(otras) + 1} registros con este documento. "
                      f"CONFIRME cuál corresponde antes de caracterizar. ")
        resumen = self._a_resumen(victima)

        # Se devuelve `encontrado=True` aunque no sea elegible: el encuestador
        # necesita ver a quién tiene enfrente y POR QUÉ no puede caracterizarla.
        # Decirle "no existe" cuando en realidad está excluida sería mentirle.
        if victima.estado_ruv == "EXCLUIDO":
            mensaje = "Persona excluida del RUV — no elegible para caracterización."
        elif not victima.habilitado_para_caracterizacion:
            if victima.fecha_ult_caracterizacion:
                mensaje = (f"Ya fue caracterizada el "
                           f"{victima.fecha_ult_caracterizacion:%Y-%m-%d}.")
            else:
                mensaje = "La persona no está habilitada para caracterización."
        else:
            mensaje = ""

        # El aviso va PRIMERO: que haya que verificar la identidad importa más que el
        # estado en el RUV — si es otra persona, lo del RUV ni aplica.
        return ResultadoBusqueda(
            encontrado=True, victima=resumen, fuente=self.FUENTE,
            mensaje=(aviso + mensaje).strip(),
            candidatos=[self._a_resumen(v, con_hechos=False) for v in otras],
        )

    def obtener_grupo_familiar(self, cons_persona) -> list[VictimaResumen]:
        """
        Devuelve [] a propósito, y conviene entender por qué.

        El grupo familiar del RUV es un dato **de la fuente**, no algo que SICAV
        derive: acá los miembros de un hogar se registran durante la caracterización
        (`MiembroHogar`), que es otra cosa —el hogar que el encuestador encuentra hoy,
        no el núcleo declarado en el RUV—. Devolver los miembros del hogar disfrazados
        de grupo familiar mezclaría dos conceptos y daría un dato falso.

        Cuando la carga del padrón traiga el grupo familiar, se implementa aquí.
        """
        return []

    def listar_todas(self, limite: int | None = None) -> list[VictimaResumen]:
        # Sin hechos: `listar_todas` alimenta listados y precargas acotadas, y traer
        # los hechos de cada víctima dispara una query por persona.
        #
        # El `limite` recorta en SQL (`LIMIT`), no en Python: sin él, el queryset
        # materializa el padrón entero —5,9 M— antes de que nadie pueda descartar
        # nada.
        qs = self._base_qs()
        if limite is not None:
            qs = qs[:limite]
        return [self._a_resumen(v, con_hechos=False) for v in qs]

    def iterar_padron(self, batch_size: int = 1000):
        """
        Streaming real por lotes — es lo que permite generar el padrón descargable
        sin materializar millones de filas en el proceso Django.

        `iterator(chunk_size)` usa un cursor del lado del servidor en PostgreSQL, así
        que la memoria no crece con el tamaño del padrón. Sin hechos, por lo mismo que
        `listar_todas`: el padrón descargable es el resumen para identificar a la
        persona, no su historia completa.
        """
        for victima in self._base_qs().iterator(chunk_size=batch_size):
            yield self._a_resumen(victima, con_hechos=False)

    def verificar_habilitacion(self, tipo_documento, numero_documento) -> EstadoHabilitacion:
        """Consulta ligera: solo los tres campos que deciden, sin descifrar el resto."""
        from apps.victimas.models import Victima

        victima = (Victima.objects
                   .filter(numero_documento_hash=doc_hash(tipo_documento, numero_documento))
                   .only("estado_ruv", "habilitado_para_caracterizacion",
                         "fecha_ult_caracterizacion")
                   .first())

        if victima is None:
            return EstadoHabilitacion(
                habilitado=False,
                razon="La persona no está en el padrón cargado en SICAV.")
        if victima.estado_ruv == "EXCLUIDO":
            return EstadoHabilitacion(habilitado=False,
                                      razon="Persona excluida del RUV.")
        if not victima.habilitado_para_caracterizacion:
            if victima.fecha_ult_caracterizacion:
                return EstadoHabilitacion(
                    habilitado=False,
                    razon=(f"Ya fue caracterizada el "
                           f"{victima.fecha_ult_caracterizacion:%Y-%m-%d}."))
            return EstadoHabilitacion(habilitado=False,
                                      razon="No habilitada para caracterización.")
        return EstadoHabilitacion(habilitado=True)
