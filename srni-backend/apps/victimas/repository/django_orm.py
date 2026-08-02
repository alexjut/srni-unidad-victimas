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
    def _solo_una_fila_por_persona(qs):
        """
        Quita las filas que el veredicto declara duplicados de la misma persona,
        dejando la preferida. Las ambiguas y las sin veredicto pasan enteras.

        Va en SQL y no en Python porque sobre 5,9 M de filas filtrar después
        significaría descifrar y armar el DTO de un millón de filas para tirarlas.

        Las dos condiciones que parecen de más son las que impiden borrar gente:

        * `victima_preferida_id IS NOT NULL` — la FK es `on_delete=SET_NULL`, así
          que si la fila preferida se borra, el veredicto queda apuntando a nada.
          Sin esta guarda, `NULL <> id` es verdadero para TODAS las filas del
          documento y el grupo entero desaparecía del padrón.
        * `created_at <= actualizado_en` — el veredicto es una foto del momento en
          que se clasificó. Una víctima creada DESPUÉS (un alta manual, un
          `registrar-desde-fuente`) no estuvo en esa foto, y sin esta condición
          nacía descartada: no aparecería en el padrón hasta la próxima
          clasificación, sin que nada lo avisara.
        """
        return qs.extra(  # noqa: S610 — SQL fijo, sin interpolación de usuario
            where=["""
                NOT EXISTS (
                    SELECT 1 FROM victimas_colisiondocumento c
                    WHERE c.doc_hash = victimas_victima.numero_documento_hash
                      AND c.clase IN ('DUPLICADO_FUENTE', 'VARIANTE_NOMBRE')
                      AND c.victima_preferida_id IS NOT NULL
                      AND c.victima_preferida_id <> victimas_victima.id
                      AND victimas_victima.created_at <= c.actualizado_en
                )
            """]
        )

    @staticmethod
    def _clases_de_colision(filas: list) -> dict:
        """Clase de colisión de las filas dadas, solo para las que exigen aviso."""
        from apps.victimas.models import ColisionDocumento

        if not filas:
            return {}
        return dict(
            ColisionDocumento.objects
            .filter(doc_hash__in={v.numero_documento_hash for v in filas},
                    clase__in=('AMBIGUO', 'NO_IDENTIFICANTE'))
            .values_list('doc_hash', 'clase')
        )

    @staticmethod
    def _veredictos_de(encontradas: list) -> dict:
        """Los veredictos de todos los documentos presentes en el resultado."""
        from apps.victimas.models import ColisionDocumento

        hashes = {v.numero_documento_hash for v in encontradas}
        return {c.doc_hash: c for c in
                ColisionDocumento.objects.filter(doc_hash__in=hashes)}

    @classmethod
    def _resolver_colision(cls, encontradas: list) -> list:
        """
        Reduce a una sola fila **por documento** cuando el veredicto dice que esas
        filas son la misma persona. Conserva el orden recibido.

        ⚠️ Agrupa por `doc_hash` y no trata la lista como un solo documento, y eso
        no es una sutileza: cuando la búsqueda cae al respaldo por número —el
        14,5 % del padrón está cargado sin tipo de documento— el resultado mezcla
        filas de documentos DISTINTOS (la misma cédula registrada como CC, como TI
        y sin tipo). Resolver el conjunto entero con el veredicto de la primera
        fila descartaría a las personas de los otros documentos: exactamente el
        borrado silencioso que este código existe para impedir.

        Devuelve el grupo entero —o sea, sigue habiendo que confirmar— cuando el
        documento es ambiguo, no identifica a nadie, o no tiene veredicto todavía.
        """
        veredictos = cls._veredictos_de(encontradas)

        # Qué fila sobrevive en cada documento; None = sobreviven todas.
        preferidas: dict[str, object] = {}
        for h, veredicto in veredictos.items():
            if veredicto.requiere_confirmacion or veredicto.victima_preferida_id is None:
                continue
            preferidas[h] = veredicto.victima_preferida_id

        def sobrevive(v) -> bool:
            preferida_id = preferidas.get(v.numero_documento_hash)
            return preferida_id is None or v.id == preferida_id

        resultado = [v for v in encontradas if sobrevive(v)]

        # Red de seguridad: si la preferida de algún documento no está en el
        # resultado —se borró la fila, o el respaldo trajo otro conjunto—, todas
        # las filas de ESE documento habrían desaparecido. Se devuelven.
        presentes = {v.numero_documento_hash for v in resultado}
        faltantes = [v for v in encontradas if v.numero_documento_hash not in presentes]
        if faltantes:
            resultado = [v for v in encontradas
                         if sobrevive(v) or v.numero_documento_hash not in presentes]
        return resultado

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

        # Documento de relleno: no identifica a nadie y no puede devolver a nadie.
        # `99` lo comparten 3.780 personas distintas; entregar una es entregar los
        # datos de un desconocido. Se responde NO ENCONTRADA a propósito: es lo que
        # lleva a la APK al alta manual, que es justo lo que corresponde hacer.
        veredictos = self._veredictos_de(encontradas)
        if any(v.clase == 'NO_IDENTIFICANTE' for v in veredictos.values()):
            return ResultadoBusqueda(
                encontrado=False, victima=None, fuente=self.FUENTE,
                no_identificante=True,
                mensaje=("Este número no identifica a una persona: en el padrón figura "
                         "como valor de relleno, compartido por muchos registros. "
                         "Verifique el documento o regístrela por alta manual."),
            )

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
        # Mismo criterio que `iterar_padron`: las filas que el veredicto declara
        # duplicados de la fuente no viajan, y las que exigen confirmar van
        # marcadas. Si no, la precarga con la que arranca la jornada llenaría el
        # dispositivo con la misma persona repetida y sin avisar de las ambiguas.
        qs = self._solo_una_fila_por_persona(self._base_qs())
        if limite is not None:
            qs = qs[:limite]
        filas = list(qs)
        clases = self._clases_de_colision(filas)
        return [
            self._a_resumen(v, con_hechos=False,
                            clase_colision=clases.get(v.numero_documento_hash))
            for v in filas
        ]

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

        qs = self._solo_una_fila_por_persona(self._base_qs())

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
