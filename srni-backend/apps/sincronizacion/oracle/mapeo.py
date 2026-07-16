"""
Mapeo de entidades SICAV (modelos Django) → argumentos de los procedures Oracle.

`ResolverCatalogos` traduce valores SICAV → códigos Oracle. Dos modos:
- `estricto=True` (ruta CONFIRMADA): si un valor no tiene mapeo conocido, LANZA
  `MapeoDesconocido` / `MapeoPendienteNegocio`. Nunca escribe con un valor inventado.
- `estricto=False` (DRY-RUN): en vez de lanzar, devuelve un marcador legible
  `‹PEND:...(valor)›` para que el bloque PL/SQL muestre qué falta resolver.

Fuentes de los códigos:
- Catálogos de ID surrogate (tipo caracterización, tipo doc, parentesco, tipo
  víctima): dicts en `catalogos.py`, que se llenan con los valores REALES de prod
  (los del Oracle local están vacíos: import metadata-only). Ver ese módulo.
- Territorio: NO hay pass-through DANE. Los cuatro ids que consume la cascada
  (IDDT, IDDEPARTAMENTO, IDPUNTOATENCION, IDMUNICIPIO) son SURROGATE de Oracle
  —verificado: TOLIMA=30, ALVARADO=32, que no son DANE—, así que el único puente
  con SICAV es el NOMBRE. Se cruza la fila completa contra el volcado real de
  GIC_N_DT_PUNTOS_ATENCION (`catalogos.cargar_dt_puntos`). Ver resolver_territorio.
- Instrumento y respuestas (INS_IDINSTRUMENTO, RES_IDRESPUESTA, RXP_TIPOPREGUNTA):
  SIN mapeo disponible — SICAV no guarda el id de instrumento de Oracle y no
  tenemos volcado de GIC_N_RESPUESTAS. Todos marcan pendiente; no se inventan.
- Usuario/perfil de servicio: `settings.ORACLE_LEGACY['USUARIO_SERVICIO_ID' / ...]`
  — PENDIENTE de confirmación de negocio (Oscar/UARIV). Sin él, no se confirma.

Cero PII expuesta a logs: los binds con PII van marcados en procedimientos.py y se
redactan en auditoría; este módulo solo arma los valores.
"""
from . import catalogos
from . import procedimientos as P


class MapeoDesconocido(ValueError):
    """Un valor SICAV no tiene equivalente en el catálogo Oracle (no se inventa)."""


class MapeoPendienteNegocio(ValueError):
    """Un valor depende de una decisión de negocio aún no confirmada."""


class CampoOrigenFaltante(MapeoDesconocido):
    """
    El modelo SICAV no define el campo del que un bind debería salir.

    Es una categoría distinta de "este valor no tiene equivalente en Oracle": eso es
    un hueco de datos/negocio, esto es un defecto de código o de esquema (el escritor
    lee un campo que no existe). Se separa porque el remedio es otro: no lo desbloquea
    Oscar con un catálogo, lo desbloquea añadir el campo o cambiar el origen.

    Hereda de MapeoDesconocido para no romper los `except` ya existentes.
    """


_SIN_CAMPO = object()


def _campo_origen(entidad, campo):
    """
    Lee `entidad.campo` sin default silencioso.

    `getattr(x, campo, None)` es una trampa en este módulo: si el modelo NO tiene el
    campo, el default lo disfraza de "valor None" y el error acaba saliendo como
    "sin mapeo Oracle para None" — que señala al catálogo de Oracle cuando el
    problema está en SICAV. Aquí se distingue "no hay campo" de "hay campo y vale
    None", que son diagnósticos distintos.
    """
    valor = getattr(entidad, campo, _SIN_CAMPO)
    if valor is _SIN_CAMPO:
        raise CampoOrigenFaltante(
            f"{type(entidad).__name__} no define el campo {campo!r}, y el escritor lo "
            f"necesita para armar el bind. NO es un mapeo pendiente: es un campo "
            f"inexistente en el modelo SICAV. Hay que añadirlo o cambiar el origen "
            f"del dato."
        )
    return valor


class ResolverCatalogos:
    """Punto único de traducción SICAV → catálogos Oracle."""

    def __init__(self, *, usuario_servicio_id=None, perfil_servicio_id=None,
                 tipo_caracterizacion_id=None, tipo_documento=None, parentesco=None,
                 tipo_victima=None, estricto=True):
        self.usuario_servicio_id = usuario_servicio_id
        self.perfil_servicio_id = perfil_servicio_id
        # Oracle solo distingue INDIVIDUO(1)/HOGAR(2); SICAV crea hogar ⇒ HOGAR(2).
        self._tipo_caracterizacion_id = (
            tipo_caracterizacion_id if tipo_caracterizacion_id is not None
            else catalogos.TIPO_CARACTERIZACION_HOGAR
        )
        self._tipo_documento = tipo_documento if tipo_documento is not None else catalogos.TIPO_DOCUMENTO
        self._parentesco = parentesco if parentesco is not None else catalogos.PARENTESCO
        self._tipo_victima = tipo_victima if tipo_victima is not None else catalogos.TIPO_VICTIMA
        self.estricto = estricto

    @classmethod
    def desde_settings(cls, *, estricto=True):
        """Construye el resolver desde settings.ORACLE_LEGACY + catalogos.py."""
        from django.conf import settings
        cfg = getattr(settings, "ORACLE_LEGACY", {}) or {}
        return cls(
            usuario_servicio_id=cfg.get("USUARIO_SERVICIO_ID"),
            perfil_servicio_id=cfg.get("PERFIL_SERVICIO_ID"),
            estricto=estricto,
        )

    # ── helpers ───────────────────────────────────────────────────────────────
    def _pendiente(self, etiqueta, clave):
        return f"‹PEND:{etiqueta}({clave})›"

    def _resolver(self, mapa, clave, cat_key):
        """Busca `clave` en `mapa`; si falta: lanza (estricto) o marcador (dry-run)."""
        etiqueta = catalogos.NOMBRES.get(cat_key, cat_key)
        if clave in mapa:
            return mapa[clave]
        if self.estricto:
            raise MapeoDesconocido(f"{etiqueta}: sin mapeo Oracle para {clave!r}.")
        return self._pendiente(cat_key.upper(), clave)

    def _servicio(self, valor, etiqueta):
        if valor is not None:
            return valor
        if self.estricto:
            raise MapeoPendienteNegocio(
                f"{etiqueta} sin definir (settings.ORACLE_LEGACY) — PENDIENTE de negocio."
            )
        return self._pendiente(etiqueta, "negocio")

    # ── catálogo 1 — usuario/perfil de servicio (PENDIENTE negocio) ────────────
    def id_usuario_servicio(self):
        return self._servicio(self.usuario_servicio_id, "USUARIO_SERVICIO_ID")

    def id_perfil_servicio(self):
        return self._servicio(self.perfil_servicio_id, "PERFIL_SERVICIO_ID")

    # ── catálogo 2 — tipo de caracterización ───────────────────────────────────
    def resolver_tipo_caracterizacion(self, instrumento_codigo=None):
        """Oracle = INDIVIDUO(1)/HOGAR(2). SICAV crea hogar ⇒ HOGAR (constante).

        `instrumento_codigo` se ignora hoy (no cambia el nivel); se mantiene en la
        firma por si algún flujo futuro debe registrarse como INDIVIDUO.
        """
        return self._tipo_caracterizacion_id

    # ── catálogo 3 — tipo de documento ─────────────────────────────────────────
    def resolver_tdoc(self, tipo_documento):
        """`tipo_documento` puede ser una instancia TipoDocumento o su `codigo`."""
        codigo = getattr(tipo_documento, "codigo", tipo_documento)
        if not codigo:
            if self.estricto:
                raise MapeoDesconocido("TDOC: miembro sin tipo de documento.")
            return self._pendiente("TIPO_DOCUMENTO", "None")
        return self._resolver(self._tipo_documento, codigo, "tipo_documento")

    # ── catálogo 4 — parentesco (RELAC) y tipo de víctima ──────────────────────
    def resolver_relac(self, parentesco):
        if not parentesco:
            if self.estricto:
                raise MapeoDesconocido("RELAC: miembro sin parentesco.")
            return self._pendiente("PARENTESCO", "None")
        return self._resolver(self._parentesco, parentesco, "parentesco")

    def resolver_t_victima(self, miembro):
        """
        T_VICTIMA (GIC_PERSONA.PER_TIPOVICTIMA) a partir del miembro SICAV.

        Hoy falla SIEMPRE, y es correcto que lo haga: `MiembroHogar` **no define**
        `tipo_victima` (solo figura en docs/base-datos/MODELOS.md como campo planeado
        que nunca se implementó). Antes se leía con `getattr(miembro, "tipo_victima",
        None)` y ese default silencioso hacía que el fallo se reportara como "sin
        mapeo Oracle para None" — un diagnóstico falso, que manda a buscar en el
        catálogo de Oracle un problema que está en el modelo SICAV.

        Son dos pendientes encadenados y conviene no confundirlos:
        1. **campo origen inexistente** (esto) → lo arregla el modelo SICAV.
        2. **mapeo de negocio de T_VICTIMA** (P8, pendiente de Oscar) → aunque el
           campo existiera, `catalogos.TIPO_VICTIMA` sigue vacío a propósito.
        """
        try:
            valor = _campo_origen(miembro, "tipo_victima")
        except CampoOrigenFaltante:
            if self.estricto:
                raise  # ruta confirmada: no se escribe con un origen inventado
            # DRY-RUN: marcador que dice la causa REAL, no un ‹PEND:...(None)› que
            # aparentaría un simple hueco de catálogo.
            return self._pendiente("T_VICTIMA", "MiembroHogar SIN campo tipo_victima")
        return self._resolver(self._tipo_victima, valor, "tipo_victima")

    # ── catálogo 5 — territorio (cascada) ──────────────────────────────────────
    def resolver_territorio(self, sesion) -> dict:
        """
        Resuelve los CUATRO ids surrogate que consume la cascada territorial, a
        partir del territorio de ATENCIÓN de la sesión SICAV.

        Devuelve {'id_dt', 'id_depto', 'id_pt', 'id_ma'} — ojo, son CUATRO, no tres:
        GIC_N_RELACION_DT_PUNTO tiene columnas separadas IDDT / IDDEPTOATEN /
        IDPUNTOATEN / IDMUNATEN, y los reportes las cruzan las cuatro contra
        GIC_N_DT_PUNTOS_ATENCION (ver ruta_escritura.md §2.5). Faltar una deja el
        territorio incompleto: ese fue el bug histórico.

        El cruce es por NOMBRE y sobre la FILA COMPLETA del crosswalk (ver
        catalogos.cargar_dt_puntos): los ids son surrogate y los nombres sueltos se
        repiten, pero la tupla (dt, depto, punto, municipio) es única (1370/1370).

        Filtra nivel por nivel para poder decir EN CUÁL falló y con qué opciones
        contaba, en vez de un "no hubo match" ciego.
        """
        niveles = (
            # (clave_crosswalk, campo_sesion, atributo_nombre, etiqueta)
            ("_dt", "direccion_territorial", "nombre", "Dirección Territorial"),
            ("_departamento", "departamento_atencion", "nombre", "Departamento de atención"),
            ("_punto", "punto_atencion", "nombre", "Punto de atención"),
            ("_municipio", "municipio_atencion", "nombre", "Municipio de atención"),
        )
        filas = catalogos.cargar_dt_puntos()
        contexto = []  # niveles ya casados, para el mensaje de error

        for clave, campo, atributo, etiqueta in niveles:
            entidad = getattr(sesion, campo, None)
            if entidad is None:
                return self._territorio_falta(
                    f"{etiqueta}: la sesión SICAV no lo tiene definido "
                    f"(SesionEncuesta.{campo} es NULL) — sin él la cascada dejaría "
                    f"GIC_N_RELACION_DT_PUNTO incompleto.",
                    campo,
                )
            nombre = getattr(entidad, atributo, None)
            objetivo = catalogos.normalizar_nombre(nombre)
            candidatas = [f for f in filas if f[clave] == objetivo]
            if not candidatas:
                return self._territorio_falta(
                    f"{etiqueta} {nombre!r} sin equivalente en "
                    f"{catalogos.NOMBRES['territorio']}"
                    + (f" para {', '.join(contexto)}" if contexto else "")
                    + f". Opciones Oracle en ese ámbito: {self._muestra(filas, clave)}.",
                    campo,
                )
            filas = candidatas
            contexto.append(f"{etiqueta}={nombre!r}")

        # La tupla completa es única en el crosswalk; si algo cambiara en el volcado
        # y dejara de serlo, es mejor enterarse aquí que escribir un id al azar.
        ids = {(f["iddt"], f["iddepartamento"], f["idpuntoatencion"], f["idmunicipio"])
               for f in filas}
        if len(ids) > 1:
            return self._territorio_falta(
                f"Territorio ambiguo: {', '.join(contexto)} resuelve a {len(ids)} "
                f"combinaciones de ids en Oracle ({sorted(ids)}). El crosswalk debería "
                f"ser único por tupla; revisar catalogos_oracle.json.",
                "ambiguo",
            )
        fila = filas[0]
        return {
            "id_dt": int(fila["iddt"]),
            "id_depto": int(fila["iddepartamento"]),
            "id_pt": int(fila["idpuntoatencion"]),
            "id_ma": int(fila["idmunicipio"]),
        }

    def _territorio_falta(self, mensaje, campo):
        """Estricto ⇒ lanza; dry-run ⇒ marcadores en los cuatro ids."""
        if self.estricto:
            raise MapeoDesconocido(f"TERRITORIO — {mensaje}")
        return {k: self._pendiente(f"TERRITORIO_{k.upper()}", campo)
                for k in ("id_dt", "id_depto", "id_pt", "id_ma")}

    @staticmethod
    def _muestra(filas, clave, limite=6):
        """Primeras opciones distintas de un nivel, para que el error sea accionable."""
        vistos = sorted({f[clave] for f in filas})
        extra = f" (+{len(vistos) - limite} más)" if len(vistos) > limite else ""
        return ", ".join(repr(v) for v in vistos[:limite]) + extra

    # ── catálogo 6 — instrumento y respuestas (SP_SET_RESPUESTAS_DE_ENCUESTA) ───
    def resolver_ins_idinstrumento(self, instrumento):
        """
        INS_IDINSTRUMENTO de Oracle para un Instrumento SICAV.

        PENDIENTE DE NEGOCIO/DATO: el modelo SICAV `formulario.Instrumento` NO tiene
        ningún campo con el id de Oracle (su propio TODO dice "confirmar lista oficial
        de instrumentos y códigos exactos con área funcional / tablas Oracle"), y el
        crosswalk no incluye GIC_N_INSTRUMENTOXPREG. Sin este id, el procedure ni
        siquiera encuentra la pregunta y aborta en silencio (ver binds_respuesta).
        No se inventa.
        """
        codigo = getattr(instrumento, "codigo", instrumento)
        if self.estricto:
            raise MapeoPendienteNegocio(
                f"{catalogos.NOMBRES['instrumento']}: sin mapeo para el instrumento "
                f"SICAV {codigo!r}. Falta el id de instrumento en Oracle "
                f"(formulario.Instrumento no lo guarda). PENDIENTE de negocio/dato."
            )
        return self._pendiente("INS_IDINSTRUMENTO", codigo)

    def resolver_res_idrespuesta(self, respuesta):
        """
        RES_IDRESPUESTA (PK de GIC_N_RESPUESTAS) para una RespuestaEncuesta SICAV.

        HIPÓTESIS SIN VERIFICAR: `OpcionRespuesta.id_resp_vivanto` (ID_RESP del
        Diccionario V8, p.ej. 4565) parece el puente natural hacia RES_IDRESPUESTA.
        NO está confirmado: no tenemos volcado de GIC_N_RESPUESTAS contra el cual
        cotejarlo. Como el procedure hace `SELECT ... INTO` con ese id y traga el
        NO_DATA_FOUND con su WHEN OTHERS, un id equivocado NO da error: simplemente
        no escribe nada. Por eso se marca pendiente en vez de arriesgar el valor.

        En dry-run el marcador incluye el id_resp_vivanto candidato, para que se vea
        la hipótesis concreta que hay que validar contra Oracle.
        """
        candidato = self._id_resp_vivanto(respuesta)
        if self.estricto:
            raise MapeoPendienteNegocio(
                f"{catalogos.NOMBRES['res_idrespuesta']}: la equivalencia "
                f"id_resp_vivanto→RES_IDRESPUESTA está SIN VERIFICAR "
                f"(candidato={candidato}). Requiere volcado de GIC_N_RESPUESTAS."
            )
        return self._pendiente("RES_IDRESPUESTA", f"hip:{candidato}")

    @staticmethod
    def _id_resp_vivanto(respuesta):
        """id_resp_vivanto de la opción elegida, si la pregunta tiene opciones."""
        pregunta = getattr(respuesta, "pregunta", None)
        opciones = getattr(pregunta, "opciones", None)
        if opciones is None:
            return None
        opcion = opciones.filter(valor=respuesta.valor).first()
        return getattr(opcion, "id_resp_vivanto", None)

    def resolver_tipo_pregunta(self, pregunta):
        """
        RXP_TIPOPREGUNTA de Oracle a partir del `tipo` SICAV.

        PENDIENTE: no se identificó el dominio de valores de RXP_TIPOPREGUNTA
        (VARCHAR2 libre en el INSERT del procedure, sin catálogo ni CHECK que lo
        acote). Los tipos SICAV (TEXTO/NUMERICO/RADIO/LISTA…) no tienen equivalencia
        confirmada. No se inventa.
        """
        tipo = getattr(pregunta, "tipo", pregunta)
        if self.estricto:
            raise MapeoPendienteNegocio(
                f"{catalogos.NOMBRES['tipo_pregunta']}: sin dominio conocido para el "
                f"tipo SICAV {tipo!r}. PENDIENTE de negocio."
            )
        return self._pendiente("RXP_TIPOPREGUNTA", tipo)


# ── extras de GIC_INSERT_PERSONAS fuera del alcance de esta tarea ──────────────
# ID_DECLAR, ID_PERS_FUENTE, ID_SINIESTRO, IDPERMI no están en los catálogos 1-5.
# Son NUMBER (posiblemente opcionales). Hasta confirmar su semántica se tratan como
# pendientes explícitos (marcador en dry-run; el flujo confirmado exigirá definirlos).
_EXTRAS_PERSONA = ("id_declar", "id_pers_fuente", "id_siniestro", "idpermi")


def _extra_pendiente(resolver, nombre, proc="GIC_INSERT_PERSONAS"):
    if resolver.estricto:
        raise MapeoPendienteNegocio(f"{nombre.upper()} ({proc}) sin definir.")
    return f"‹PEND:{nombre.upper()}›"


def _partes_nombre(nombre_completo: str):
    """Divide 'PRIMER SEGUNDO PRIMERAP SEGUNDAAP' en las 4 partes del procedure."""
    tokens = (nombre_completo or "").strip().upper().split()
    pnombre = tokens[0] if len(tokens) > 0 else ""
    snombre = tokens[1] if len(tokens) > 2 else ""
    papellido = tokens[-2] if len(tokens) >= 2 else ""
    sapellido = tokens[-1] if len(tokens) >= 3 else ""
    return pnombre, snombre, papellido, sapellido


def _cod_usuario(user):
    return getattr(user, "codigo_usuario", None) or str(getattr(user, "pk", ""))


def binds_hogar(hogar, *, user, catalogos: ResolverCatalogos, instrumento_codigo=None) -> dict:
    """Argumentos de GIC_INSERT_HOGAR1 para un Hogar SICAV."""
    return {
        "usua_creacion": _cod_usuario(user),
        "id_usuario": catalogos.id_usuario_servicio(),
        "id_perfil_usuario": catalogos.id_perfil_servicio(),
        "id_tipo_caracterizacion": catalogos.resolver_tipo_caracterizacion(instrumento_codigo),
    }


def binds_persona(miembro, *, user, estado_oracle, catalogos: ResolverCatalogos) -> dict:
    """Argumentos de GIC_INSERT_PERSONAS para un MiembroHogar SICAV."""
    from django.utils import timezone

    numero = (miembro.numero_documento or "").strip().upper() if miembro.numero_documento else ""
    pnombre, snombre, papellido, sapellido = _partes_nombre(miembro.nombre_completo)
    binds = {
        "pnombre": pnombre, "snombre": snombre,
        "papellido": papellido, "sapellido": sapellido,
        "fnacimiento": miembro.fecha_nacimiento,
        "tdoc": catalogos.resolver_tdoc(miembro.tipo_documento),
        "usuario": _cod_usuario(user),
        "usu_fcreacion": timezone.now(),
        "ndocu": numero,
        "relac": catalogos.resolver_relac(miembro.parentesco),
        # Se pasa el miembro entero, no un getattr con default: el resolver debe poder
        # distinguir "el campo no existe" de "existe y vale None". Ver resolver_t_victima.
        "t_victima": catalogos.resolver_t_victima(miembro),
        "fuentee": "SICAV",
        "estado": estado_oracle,          # 'ACTIVA' (abierto)
    }
    for extra in _EXTRAS_PERSONA:
        binds[extra] = _extra_pendiente(catalogos, extra)
    return binds


def binds_miembro(hog_codigo, per_idpersona, *, user, catalogos: ResolverCatalogos) -> dict:
    """Argumentos de GIC_INSERT_MIEMBRO_HOGAR."""
    return {
        "idhogar": hog_codigo,
        "id_persona": per_idpersona,
        "usuario": _cod_usuario(user),
        "id_usuario": catalogos.id_usuario_servicio(),
        "encuestada": "S",  # marca de persona encuestada; confirmar dominio del catálogo
    }


# ── cascada territorial ───────────────────────────────────────────────────────
def binds_territorio(hog_codigo, territorio: dict) -> list:
    """
    Los CUATRO pasos de la cascada, EN ORDEN OBLIGATORIO, como
    [(procedimiento, binds), ...]. `territorio` viene de resolver_territorio().

    El orden no es cosmético (ver cuerpos PL/SQL, package body líneas 3069-3252):
    solo el PRIMERO (GIC_SP_OBDEPTOPORDT) hace INSERT de la fila en
    GIC_N_RELACION_DT_PUNTO; los otros tres son UPDATE ... WHERE hogarcodigo = X.
    Un UPDATE que no encuentra fila NO es error en Oracle: si se llamaran fuera de
    orden, escribirían cero filas y el paso "pasaría" sin dejar territorio.

    ⚠️ TRAMPA VERIFICADA en GIC_SP_OBTPUNTOATECION: su parámetro formal se llama
    `Id_DT`, pero su cuerpo hace `UPDATE ... SET iddeptoaten = Id_dt` y filtra por
    `T.IDDEPARTAMENTO = pId_DT` (líneas 3140 y 3162). Es decir: espera el id de
    DEPARTAMENTO, no el de la DT, pese al nombre. Pasarle el id de DT metería el
    valor equivocado en IDDEPTOATEN y rompería el join de los reportes
    (RL.IDDEPTOATEN = PA.IDDEPARTAMENTO) — exactamente la forma del bug histórico.
    Por eso aquí se le pasa `id_depto`. El nombre del bind DEBE seguir siendo
    'id_dt' porque el bloque invoca por nombre formal.
    """
    return [
        (P.GIC_SP_OBDEPTOPORDT,
         {"phogar_codigo": hog_codigo, "id_dt": territorio["id_dt"]}),
        (P.GIC_SP_OBTPUNTOATECION,
         {"phogar_codigo": hog_codigo, "id_dt": territorio["id_depto"]}),  # ⚠️ ver arriba
        (P.GIC_SP_OBMUNICIPIOATECION,
         {"phogar_codigo": hog_codigo, "id_pt": territorio["id_pt"]}),
        (P.GIC_SP_GUARDAMUNATEN,
         {"phogar_codigo": hog_codigo, "id_ma": territorio["id_ma"]}),
    ]


# ── respuestas del instrumento ────────────────────────────────────────────────
def per_idpersona_de_respuesta(respuesta, mapa_personas, catalogos: ResolverCatalogos):
    """
    PER_IDPERSONA para una respuesta.

    Las de nivel PERSONA salen del mapa {miembro_pk: per_idpersona} que dejó el paso
    PERSONA. Las de nivel HOGAR llegan con `miembro=NULL` en SICAV, y el procedure
    exige un NUMBER: no sabemos qué manda ahí la app vieja. La cascada territorial
    usa el literal '1' como "persona del hogar" (GIC_N_RELACION_DT_PUNTO.IDPERSONA),
    así que '1' es la sospecha razonable — pero es una SOSPECHA y aquí no se adivina.
    """
    if respuesta.miembro_id is None:
        if catalogos.estricto:
            raise MapeoPendienteNegocio(
                "PPER_IDPERSONA: respuesta de nivel HOGAR (miembro NULL) — falta "
                "confirmar qué PER_IDPERSONA espera SP_SET_RESPUESTAS_DE_ENCUESTA "
                "para preguntas de hogar (¿el literal '1', como IDPERSONA en la "
                "cascada territorial?). PENDIENTE de negocio."
            )
        return "‹PEND:PPER_IDPERSONA(nivel_hogar)›"
    return mapa_personas.get(respuesta.miembro_id)


def binds_respuesta(respuesta, *, user, catalogos: ResolverCatalogos, hog_codigo,
                    per_idpersona, instrumento) -> dict:
    """
    Argumentos de SP_SET_RESPUESTAS_DE_ENCUESTA para una RespuestaEncuesta SICAV.

    Recordatorio de por qué la verificación posterior es obligatoria: el procedure
    arranca con `SELECT PR.IXP_ORDEN INTO pOrden ... WHERE RE.RES_IDRESPUESTA = :x`
    y su `EXCEPTION WHEN OTHERS` se traga el NO_DATA_FOUND. Con un RES_IDRESPUESTA
    o un INS_IDINSTRUMENTO que Oracle no conozca, la llamada retorna sin excepción
    y SIN escribir nada.
    """
    return {
        "pcod_hogar": hog_codigo,
        "pper_idpersona": per_idpersona,
        "pres_idrespuesta": catalogos.resolver_res_idrespuesta(respuesta),
        "prxp_textorespuesta": respuesta.valor,
        "prxp_tipopreguntarespuesta": catalogos.resolver_tipo_pregunta(respuesta.pregunta),
        "pins_idinstrumento": catalogos.resolver_ins_idinstrumento(instrumento),
        "pusu_usuariocreacion": _cod_usuario(user),
        # PPER_IDPREGUNTAPADRE: el procedure lo usa como pId_Pregunta/pID_RESPUESTA
        # para SP_BORRADORESPUESTAS, SP_BORRADOVALIDADORES y las preguntas derivadas.
        # SICAV no modela "pregunta padre" con id Oracle ⇒ pendiente.
        "pper_idpreguntapadre": _extra_pendiente(
            catalogos, "pper_idpreguntapadre", "SP_SET_RESPUESTAS_DE_ENCUESTA"),
        # PBANDERA=1 dispara SP_BORRADORESPUESTAS (¡BORRA respuestas previas del
        # hogar/instrumento!). 0 solo inserta. Cuál corresponde a una migración
        # SICAV→Oracle es decisión de negocio, y el lado destructivo no se asume.
        "pbandera": _extra_pendiente(
            catalogos, "pbandera", "SP_SET_RESPUESTAS_DE_ENCUESTA"),
    }
