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
    def _a_resumen(self, victima, *, con_hechos: bool = True,
                   clase_colision: str | None = None) -> VictimaResumen:
        return VictimaResumen(
            clase_colision=clase_colision,
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

    @staticmethod
    def _resolver_colision(encontradas: list) -> list:
        """
        Reduce a una sola fila cuando el veredicto dice que son la misma persona.

        Devuelve la lista tal cual —o sea, sigue habiendo que confirmar— si el
        documento es ambiguo, si no identifica a nadie, o si no hay veredicto
        todavía. Nunca descarta a nadie por su cuenta.
        """
        from apps.victimas.models import ColisionDocumento

        veredicto = ColisionDocumento.objects.filter(
            doc_hash=encontradas[0].numero_documento_hash
        ).first()
        if veredicto is None or veredicto.requiere_confirmacion:
            return encontradas

        preferida_id = veredicto.victima_preferida_id
        elegida = next((v for v in encontradas if v.id == preferida_id), None)
        # Si la preferida ya no está entre las encontradas (se borró, o el filtro
        # de respaldo por número trajo otro conjunto), se conserva el orden por
        # completitud y no se descarta nada.
        return [elegida] if elegida is not None else encontradas

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

        # Varios registros con el mismo documento. Antes se avisaba en TODOS los
        # casos; medido sobre el padrón real, el 92 % de esos grupos son una sola
        # persona duplicada por el Oracle de origen —hasta 505 filas de la misma
        # señora— y pedir confirmación ahí es ruido que enseña a ignorar el aviso.
        #
        # `ColisionDocumento` trae el veredicto ya calculado (ver
        # `apps/victimas/identidad.py`). Sin veredicto se avisa igual: el default
        # seguro es preguntar.
        encontradas.sort(key=self._completitud, reverse=True)
        if len(encontradas) > 1:
            encontradas = self._resolver_colision(encontradas)

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

        **Los duplicados de la fuente se dejan pasar una sola vez.** Cuando el
        veredicto dice que las 505 filas de un documento son la misma señora, viaja
        la más completa y las otras 504 no: no aportan nada al dispositivo y
        engordan un archivo que ya pesa de más. Las que sí son personas distintas
        viajan TODAS, marcadas, porque perder una es perder a una víctima —es lo
        que hacía el colapso ciego por documento—.

        La exclusión se hace en SQL (`NOT EXISTS` contra el veredicto) y no en
        Python: sobre 5,9 M de filas, filtrar acá significaría descifrar y armar el
        DTO de un millón de filas para tirarlas.
        """
        from apps.victimas.models import ColisionDocumento

        qs = self._base_qs().extra(  # noqa: S610 — SQL fijo, sin interpolación de usuario
            where=["""
                NOT EXISTS (
                    SELECT 1 FROM victimas_colisiondocumento c
                    WHERE c.doc_hash = victimas_victima.numero_documento_hash
                      AND c.clase IN ('DUPLICADO_FUENTE', 'VARIANTE_NOMBRE')
                      AND c.victima_preferida_id IS DISTINCT FROM victimas_victima.id
                )
            """]
        )

        # Solo los documentos donde hay algo que advertir. Son ~7 % de los
        # repetidos, así que el diccionario es chico y cabe de sobra en memoria.
        clases = dict(
            ColisionDocumento.objects
            .filter(clase__in=('AMBIGUO', 'NO_IDENTIFICANTE'))
            .values_list('doc_hash', 'clase')
        )

        for victima in qs.iterator(chunk_size=batch_size):
            yield self._a_resumen(
                victima, con_hechos=False,
                clase_colision=clases.get(victima.numero_documento_hash),
            )

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
