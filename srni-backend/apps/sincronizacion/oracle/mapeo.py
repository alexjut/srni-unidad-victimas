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
# Alias para las funciones sueltas del módulo, donde el nombre `catalogos` lo ocupa
# el parámetro ResolverCatalogos y taparía al módulo.
from . import catalogos as catalogos_mod
from . import procedimientos as P


class MapeoDesconocido(ValueError):
    """Un valor SICAV no tiene equivalente en el catálogo Oracle (no se inventa)."""


class MapeoPendienteNegocio(ValueError):
    """Un valor depende de una decisión de negocio aún no confirmada."""


class SinDestinoEnRespuestas(MapeoDesconocido):
    """
    Esta respuesta NO va a la tabla de respuestas del legacy: su destino es otro.

    No es un mapeo que falte: es que en el legacy ese dato vive en otra parte.
    Medido sobre territorial v8, de las 117 preguntas sin `id_preg`:

      41  subcampos "Otro, ¿cuál?" → el texto va en el RXP_TEXTORESPUESTA de la
          respuesta PADRE, que sí tiene su pregunta en Oracle
       7  subcampos de cantidad → igual
       7  identidad (segundo nombre, apellidos, los *_RUV) → GIC_PERSONA
       3  validadores (estado en el RUV, tipo de persona)
       2  hechos victimizantes → GIC_INSERT_VALIDADOR_HECHO_AUX

    Tratarlas como "pendiente de negocio" hacía abortar el hogar entero, así que
    ningún hogar territorial se podía escribir. Se distingue para que el escritor
    pueda OMITIRLAS dejando constancia, en vez de perder todo el hogar por un
    campo cuyo destino ya conocemos —y que en varios casos ya escribimos por otro
    camino—.

    ⚠️ Lo omitido se cuenta y se informa. Entre estas 117 hay al menos una que sí
    debería ir a la tabla de respuestas (`Z2`, Lugar de la Encuesta, que en Oracle
    es PRE_IDPREGUNTA=1): omitir no es resolver, es no perder el resto mientras se
    resuelve.
    """


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

# Centinela de "no hay entrada curada": distinto de cualquier resultado de
# `_verificar_escribible` (un res_id int, o un marcador de dry-run, o la excepción en
# estricto). No se puede usar None para esto: None es un resultado posible. Ver
# `_consultar_crosswalk` y su uso en `resolver_res_idrespuesta`.
_SIN_CROSSWALK = object()


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

    def resolver_relac_de_miembro(self, miembro):
        """RELAC del miembro considerando el rol.

        El **autorizado** (`es_autorizado=True`) es el jefe/responsable del hogar y
        SICAV le deja `parentesco=''` (no es pariente de sí mismo). Oracle sí modela
        esa relación: GIC_PARENTESCOGENEALOGICO 1 = 'Jefe de hogar'. Por eso el
        autorizado resuelve a **RELAC=1** en vez de fallar por parentesco vacío; el
        resto de miembros cruza por su parentesco normal.
        """
        if getattr(miembro, "es_autorizado", False):
            return 1
        return self.resolver_relac(miembro.parentesco)

    # ── extras de escritura decididos CON DATO (2026-07-24) ────────────────────
    # No inventan un mapeo de catálogo (eso lo sigue prohibiendo el modo estricto):
    # son decisiones de negocio ya tomadas y respaldadas por la estructura real.
    def resolver_extra_persona(self, nombre, miembro=None):
        """
        ID_DECLAR / ID_PERS_FUENTE / ID_SINIESTRO → **NULL**. IDPERMI → ver abajo.

        Los tres primeros son ids de enlace internos de Oracle (declaración FUD,
        persona fuente, siniestro) que una caracterización SICAV nueva NO origina.
        La estructura los confirma nullable, así que NULL es fiel: se escribe lo que
        SICAV tiene = nada.

        `IDPERMI` es OTRA COSA y mandarlo en NULL era un defecto. Va a
        `PER_IDMODELOINT`, que es el puente de la persona con el Modelo Integrado, y
        de él dependen el cruce con el RUV y los hechos victimizantes de los
        reportes. Dos motivos para no dejarlo en NULL:

        1. El `DEFAULT 0` de la columna **no aplica**: el procedure inserta con una
           lista posicional de valores, así que NULL entra tal cual.
        2. El job `GIC_ACT_TIPO_RECONOCIMIENTO` que resuelve el enlace busca
           `WHERE PER_IDMODELOINT = 0`. Una fila en NULL no la ve **nunca**: queda
           fuera del cruce para siempre, sin que nadie lo note.

        Y cuando la persona viene del padrón podemos hacer algo mejor que 0: su
        `cons_persona` **es** ese identificador —el job lo cruza contra
        `M_CARACT_TABLA_RA_PER.CONS_PERONA`, que es de donde lo sacamos—, así que se
        escribe resuelto de entrada y no hace falta esperar a ningún job.
        """
        if nombre != 'idpermi':
            return None

        victima = getattr(miembro, 'victima', None) if miembro is not None else None
        cons = getattr(victima, 'cons_persona', None) if victima is not None else None
        # 0 = "pendiente de resolver", que es lo que el job busca. Nunca NULL.
        return int(cons) if cons else 0

    def resolver_pregunta_padre(self):
        """PPER_IDPREGUNTAPADRE → **NULL**.

        SICAV no modela 'pregunta padre' (derivadas de Oracle) y NO es columna
        almacenada de GIC_N_RESPUESTASENCUESTA: el procedure solo lo usa como
        pId_Pregunta para SP_BORRADORESPUESTAS/validadores. En un hogar nuevo no hay
        respuestas previas que borrar.
        """
        return None

    def resolver_pbandera(self):
        """PBANDERA → **1** (upsert idempotente).

        1 = borra+inserta la respuesta del par (hogar, pregunta); 0 = solo inserta.
        En un hogar NUEVO el borrado es no-op, y 1 hace que re-correr el Escalón 1 no
        duplique respuestas. Tampoco es columna almacenada (control del procedure).
        """
        return 1

    def resolver_t_victima(self, miembro):
        """
        T_VICTIMA (GIC_PERSONA.PER_TIPOVICTIMA) → **NULL**.

        RESUELTO CON DATO (2026-07-24). `SELECT PER_TIPOVICTIMA, COUNT(*) FROM
        GIC_PERSONA` en prod dio: **NULL = 7.755.818** personas · 'DIRECTA' = 25 ·
        'INDIRECTA (DESTINATARIO)' = 1. O sea el campo está en **DESUSO** (26 valores
        en ~7,76 M personas, 0,0003 %). Decisión de Javier (delegada por Oscar): SICAV
        **escribe NULL**, tal cual el 99,9997 % de Oracle — no se deriva ni se inventa,
        y `MiembroHogar` no necesita el campo. Disuelve el pendiente P8/T_VICTIMA (antes
        fallaba porque el modelo SICAV no traía `tipo_victima`; ya no hay nada que traer).

        `miembro` se ignora a propósito: no hay origen que leer.
        """
        return None

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
    def resolver_ins_idinstrumento(self, instrumento=None):
        """
        INS_IDINSTRUMENTO de Oracle.

        Es CONSTANTE: Oracle tiene un solo instrumento (`GIC_INSTRUMENTO` = 1 fila,
        id 1 = 'CARACTERIZACION', activo desde 2013-10-18). No modela el cuestionario
        por instrumento como SICAV —que tiene 8—, así que todas las preguntas cuelgan
        de ese id y no hay crosswalk que resolver.

        `instrumento` se acepta y se ignora: mantiene la firma por si Oracle algún día
        separa instrumentos. La consecuencia de que sea uno solo está en el resolver
        de respuestas: la pregunta se identifica por PRE_IDPREGUNTA, no por instrumento.
        """
        return catalogos.INS_IDINSTRUMENTO_CARACTERIZACION

    def resolver_res_idrespuesta(self, respuesta):
        """
        RES_IDRESPUESTA (PK de GIC_N_RESPUESTAS) para una RespuestaEncuesta SICAV.

        Estrategia, en dos saltos (ver catalogos.cargar_respuestas):
        1. **Pregunta por id**: `Pregunta.id_preg` == `PRE_IDPREGUNTA`. Puente
           verificado con datos reales (14/14 ids, 52/59 textos), no una hipótesis.
        2. **Opción por texto**, pero SOLO entre las respuestas de esa pregunta. El
           universo baja a 2-14 candidatas, así que el contexto desambigua igual que
           la fila completa en territorio: 'Cabecera municipal…' existe con id 8
           (Zona de residencia) y 3809 (Zona de correspondencia), y la pregunta decide.

        Lo que NO se hace: usar `id_resp_vivanto` (refutado, 0/14 — Mujer es 4599 en
        SICAV y 69 en Oracle), ni fuzzy matching. Si el texto no calza exacto tras
        normalizar, elegir "el más parecido" acabaría escribiendo la opción equivocada
        sin que nadie se entere (el procedure traga el error).

        ESCALERA DE DESEMPATE cuando el cruce no es exacto o hay ambigüedad
        (criterio de Javier, 2026-07-16) — en este orden, sin saltarse peldaños:
          1. **Cruce exacto** por texto normalizado dentro de la pregunta.
          2. **Filtro de escribibilidad**: descartar las huérfanas (sin fila en
             GIC_N_INSTRUMENTOXRESP).
          3. **MANUAL OFICIAL de UARIV** (`11-MU` Territorial/Étnicos, `14-MU`
             Asistencia, en `docs/perfiles/`): la autoridad sobre qué opciones existen
             y con qué redacción.
          4. **Oscar / negocio**: SOLO lo que el manual no cubra.
        El código llega hasta el peldaño 2; del 3 en adelante es curaduría humana, y
        por eso los errores de aquí nombran el manual y muestran las candidatas reales.

        ⚠️ Corrección con datos, no con teoría (2026-07-16). Aquí estaba escrito que el
        peldaño 2 "suele disolver la ambigüedad porque las filas de más son ruido". El
        export con la columna ESCRIBIBLE lo REFUTÓ: en la pregunta 30 los 4 ids de
        'Cédula de ciudadanía / Contraseña' (93, 3852, 3853, 3854) están los 4 marcados
        ESCRIBIBLE=SI. O sea el filtro no desempata nada ahí, y el caso sube al manual.
        El manual (11-MU B6) declara la opción UNA vez ⇒ confirma que sobran ids, pero
        no dice cuál surrogate es el vigente ⇒ peldaño 4. Se deja escrito porque la
        hipótesis bonita era mía y el dato dijo que no.
        """
        pregunta = getattr(respuesta, "pregunta", None)
        cat = catalogos.cargar_respuestas()

        # ── salto 1: la pregunta ────────────────────────────────────────────
        id_preg = _campo_origen(pregunta, "id_preg")
        codigo = getattr(pregunta, "codigo_externo", "?")
        if id_preg is None:
            # No es "falta un mapeo": la mayoría de estas preguntas tienen su
            # destino en otra tabla del legacy (ver `SinDestinoEnRespuestas`).
            # Se distingue para que el hogar no se pierda entero por ellas.
            raise SinDestinoEnRespuestas(
                f"la pregunta SICAV {codigo!r} no tiene `id_preg` (el puente hacia "
                f"GIC_N_PREGUNTAS.PRE_IDPREGUNTA). En territorial v8 son 117, y la "
                f"mayoría no van a la tabla de respuestas: los subcampos "
                f"'Otro, ¿cuál?' viajan en el texto de su respuesta padre, la "
                f"identidad va a GIC_PERSONA y los hechos a los validadores. Esta "
                f"respuesta se OMITE y queda registrada."
            )
        fila = cat["preguntas"].get(int(id_preg))
        if fila is None:
            meta = cat["_meta"]
            if meta.get("completo"):
                # Con el volcado completo, la ausencia SÍ significa algo.
                return self._respuesta_falta(
                    f"la pregunta SICAV {codigo!r} (id_preg={id_preg}) no existe en el "
                    f"instrumento de Oracle. El volcado está completo, así que esto es "
                    f"real: SICAV pregunta algo que Oracle no tiene dónde guardar. Es "
                    f"pendiente de negocio (Oscar), no un fallo del cruce.",
                    f"{codigo}/pre={id_preg}")
            # Sin el volcado completo, la ausencia NO significa nada. Decirlo así:
            # concluir "no existe en Oracle" desde un export truncado sería mentir con
            # cara de dato. La pregunta 5 y la 24 están porque cayeron dentro de las
            # 200 filas; la 200 y pico no están por lo mismo, no por Oracle.
            return self._respuesta_falta(
                f"la pregunta SICAV {codigo!r} (id_preg={id_preg}) no está en el volcado "
                f"de Oracle que tenemos cargado — y eso NO quiere decir que no exista en "
                f"Oracle: {meta.get('cobertura')}. Hasta que llegue el export completo, "
                f"de esta pregunta no se puede afirmar ni que existe ni que no.",
                f"{codigo}/fuera_del_volcado")

        # ── salto 2-bis: geografía — no hay opción que cruzar ────────────────
        # Las preguntas de departamento/municipio (PRE_TIPOCAMPO='DP') y la de
        # Dirección Territorial ('DT') no listan un RES_IDRESPUESTA por municipio:
        # Oracle les da UNA respuesta contenedora, con RES_RESPUESTA vacío, y el
        # lugar viaja aparte en RXP_TEXTORESPUESTA (ver _texto_respuesta).
        # Verificado sobre el catálogo completo de prod: las 19 preguntas DP/DT
        # tienen exactamente 1 respuesta, escribible. Sin este atajo, el cruce por
        # texto no tendría nada que comparar y la respuesta se perdería.
        geo = catalogos_mod.cargar_geografia()
        if int(id_preg) in (geo["preguntas_dp"] | geo["preguntas_dt"]):
            contenedoras = fila["respuestas"]
            if len(contenedoras) == 1:
                return contenedoras[0]["res_idrespuesta"]
            return self._respuesta_falta(
                f"la pregunta geográfica {codigo!r} (id_preg={id_preg}) tiene "
                f"{len(contenedoras)} respuestas en Oracle, no la única contenedora que "
                f"se espera de un campo DP/DT. No se elige a ciegas.",
                f"{codigo}/geo_contenedora_ambigua")

        # ── salto 2-ter: preguntas ABIERTAS (texto, número, fecha) ──────────
        #
        # Una pregunta abierta no tiene opciones que cruzar: lo que el encuestador
        # escribió no es una etiqueta de catálogo, es el dato. Oracle las modela
        # igual que las geográficas —UNA respuesta contenedora, con RES_RESPUESTA
        # vacío— y el valor viaja aparte, en `RXP_TEXTORESPUESTA` (ver
        # `_texto_respuesta`, que ya lo manda).
        #
        # Sin este salto, TODA pregunta abierta abortaba el hogar: el cruce por
        # texto no tenía con qué comparar. En el instrumento territorial v8 hay 55
        # preguntas abiertas —el documento del autorizado, la dirección, los
        # teléfonos, el correo—, así que ningún hogar territorial completo se podía
        # escribir. El piloto no lo vio porque llevaba tres respuestas.
        #
        # La condición es la FORMA de Oracle, no el tipo declarado en SICAV: una
        # sola respuesta y sin texto es Oracle diciendo "acá va un valor libre".
        # Si hubiera varias, o la única tuviera etiqueta, no aplica y sigue el
        # camino normal — no se elige a ciegas.
        respuestas_oracle = fila["respuestas"]
        if len(respuestas_oracle) == 1 and not (
                respuestas_oracle[0].get("res_respuesta") or "").strip():
            unica = respuestas_oracle[0]
            if unica["res_idrespuesta"] in cat["huerfanas"]:
                return self._respuesta_falta(
                    f"la pregunta abierta {codigo!r} (id_preg={id_preg}) tiene una sola "
                    f"respuesta contenedora ({unica['res_idrespuesta']}) pero es "
                    f"HUÉRFANA: sin fila en GIC_N_INSTRUMENTOXRESP el procedure haría "
                    f"NO_DATA_FOUND y no escribiría nada, en silencio.",
                    f"{codigo}/abierta_huerfana")
            return unica["res_idrespuesta"]

        # ── salto 2: la opción, por texto, dentro de esa pregunta ───────────
        etiqueta = self._etiqueta_opcion(respuesta)
        if etiqueta is None:
            return self._respuesta_falta(
                f"la respuesta a {codigo!r} vale {respuesta.valor!r} y esa opción no "
                f"existe en SICAV (formulario.OpcionRespuesta): no hay texto que cruzar. "
                f"Si la pregunta es abierta, el problema es otro: Oracle tiene "
                f"{len(fila['respuestas'])} respuestas para ella y una abierta debería "
                f"tener exactamente una, contenedora.",
                f"{codigo}/opcion_inexistente")
        objetivo = catalogos.normalizar_nombre(etiqueta)
        candidatas = [r for r in fila["respuestas"] if r["_texto"] == objetivo]

        if not candidatas:
            # El crosswalk CURADO tiene PRECEDENCIA sobre el fallo de cruce por texto:
            # cubre justamente las opciones cuya redacción SICAV≠Oracle ('Otro' vs
            # 'Otro, ¿cuál?', 'Combares' [typo de SICAV] vs 'Combates'), que por eso no
            # cruzan solas. Es autoridad humana verificada, no fuzzy: solo clave EXACTA
            # (id_preg, texto normalizado). Lo que no esté curado sigue de largo al error.
            curado = self._consultar_crosswalk(id_preg, objetivo, cat, codigo)
            if curado is not _SIN_CROSSWALK:
                return curado
            opciones = ", ".join(repr(r["res_respuesta"]) for r in fila["respuestas"]
                                 if r["res_respuesta"]) or "(pregunta abierta, sin opciones)"
            return self._respuesta_falta(
                f"la opción {etiqueta!r} de {codigo!r} no cruza por texto con ninguna "
                f"respuesta de la pregunta {id_preg} en Oracle. Candidatas: {opciones}. "
                f"Los textos de SICAV y Oracle divergen de verdad (p.ej. 'Palenquero(a)' "
                f"vs 'Palenquero (a)'), así que esto es CURADURÍA MANUAL, no un bug. "
                f"Desempate: consultar el MANUAL OFICIAL (11-MU Territorial/Étnicos, "
                f"14-MU Asistencia) — él dice cuál es la redacción oficial y por tanto "
                f"si son la misma opción. Si el manual no lo resuelve, es pendiente de "
                f"negocio (Oscar). NUNCA fuzzy matching.",
                f"{codigo}/texto_no_cruza")
        # ── salto 3: descartar las NO escribibles ANTES de juzgar ambigüedad ──
        # El orden importa. Oracle tiene filas espurias: la pregunta 30 repite
        # 'Cédula de ciudadanía / Contraseña' con 4 ids (93, 3852-3854) aunque el
        # manual 11-MU (B6) declara esa opción UNA sola vez. Como las espurias suelen
        # ser huérfanas (sin fila en GIC_N_INSTRUMENTOXRESP ⇒ no escribibles),
        # filtrarlas primero deja una sola candidata y la "ambigüedad" se disuelve.
        # Juzgar ambigüedad antes del filtro mandaría a negocio algo que es basura de datos.
        verificada = cat["_meta"].get("escribibilidad_verificada")
        if verificada:
            escribibles = [r for r in candidatas if r["res_idrespuesta"] not in cat["huerfanas"]]
            if not escribibles:
                ids = sorted(r["res_idrespuesta"] for r in candidatas)
                return self._respuesta_falta(
                    f"la opción {etiqueta!r} de {codigo!r} cruza con {ids} en Oracle, "
                    f"pero TODAS son HUÉRFANAS (sin fila en GIC_N_INSTRUMENTOXRESP): el "
                    f"procedure haría NO_DATA_FOUND y no escribiría nada, en silencio. "
                    f"Son opciones que el manual no declara y que Oracle retiró. ⚠️ Que "
                    f"SICAV ofrezca {etiqueta!r} significa que **el instrumento de SICAV "
                    f"se desvió del manual**: cotejarlo con el 11-MU/14-MU. El problema "
                    f"está en SICAV, no en Oracle.",
                    f"{codigo}/todas_huerfanas")
            candidatas = escribibles

        if len(candidatas) > 1:
            # Antes de declarar ambigüedad, el crosswalk curado puede haber fijado a
            # mano cuál RES_IDRESPUESTA corresponde a esta opción de SICAV. Si lo hizo,
            # es autoridad y desempata (clave EXACTA; nunca fuzzy). Si no, cae al error.
            curado = self._consultar_crosswalk(id_preg, objetivo, cat, codigo)
            if curado is not _SIN_CROSSWALK:
                return curado
            ids = sorted(r["res_idrespuesta"] for r in candidatas)
            matiz = (
                "Y todas son ESCRIBIBLES, así que el peldaño 2 no desempata: la teoría "
                "de que las de más serían huérfanas quedó refutada con el export del "
                "2026-07-16 (la pregunta 30 marca ESCRIBIBLE=SI en sus 4 ids). Toca el "
                "peldaño 3, el MANUAL OFICIAL (11-MU/14-MU): dice qué opciones existen "
                "y con qué redacción. Si el manual declara la opción una sola vez, "
                "confirma que sobran ids — pero NO dice cuál de los surrogates es el "
                "vigente, y eso ya es peldaño 4: pendiente de negocio (Oscar). Dato "
                "para llevarle, no suposición: contar cuál de esos ids usan de verdad "
                "las encuestas ya escritas (§3b del traspaso)."
                if verificada else
                "Puede que se resuelva sola al conocer las huérfanas (Query C2): si las "
                "espurias no son escribibles, quedaría una. Falta el export con la marca."
            )
            return self._respuesta_falta(
                f"la opción {etiqueta!r} de {codigo!r} cruza con {len(candidatas)} "
                f"respuestas de la misma pregunta {id_preg} en Oracle ({ids}): mismo "
                f"texto, ids distintos. {matiz} NUNCA elegir 'el primero' ni el menor: "
                f"el procedure traga el error y escribiría la opción equivocada callado.",
                f"{codigo}/ambigua")

        res_id = candidatas[0]["res_idrespuesta"]
        return self._verificar_escribible(res_id, cat, codigo)

    def _consultar_crosswalk(self, id_preg, objetivo, cat, codigo):
        """
        Busca la opción en el crosswalk CURADO por clave EXACTA (id_preg + texto
        normalizado de la opción SICAV) y, si la encuentra, la resuelve.

        El crosswalk es autoridad humana verificada (164/164 res_id existen y son
        escribibles), por eso se consulta cuando el cruce por texto no basta y tiene
        precedencia sobre esos fallos. Pero el res_id curado NO se devuelve crudo: pasa
        por `_verificar_escribible` igual que cualquier otro, de modo que la disciplina
        de escribibilidad no se salta por venir de una fuente curada.

        Devuelve el resultado de `_verificar_escribible` (un res_id, o —en dry-run— un
        marcador, o —en estricto— lanza) cuando hay entrada; si NO hay entrada, devuelve
        el centinela `_SIN_CROSSWALK` para que el llamador prosiga con su error de hoy.
        Solo clave EXACTA: nada de fuzzy, nunca inventar.
        """
        res_id = catalogos.cargar_crosswalk_opciones().get((int(id_preg), objetivo))
        if res_id is None:
            return _SIN_CROSSWALK
        return self._verificar_escribible(res_id, cat, codigo)

    def _verificar_escribible(self, res_id, cat, codigo):
        """
        Una RES_IDRESPUESTA sin fila en GIC_N_INSTRUMENTOXRESP NO es escribible.

        El procedure hace `SELECT ... INTO` sobre esa tabla: si no hay fila, salta
        NO_DATA_FOUND, lo traga el WHEN OTHERS y **no escribe nada sin avisar**. Query
        C2 reportó 153 huérfanas, así que el riesgo es real y medido.

        Desde el export del 2026-07-16 ya no es una suposición: la Query A v2 trae la
        columna ESCRIBIBLE por fila, así que de las respuestas que SÍ están en el volcado
        se sabe (no se cree) cuáles se pueden escribir.

        QUÉ ES REALMENTE UNA HUÉRFANA (verificado 2026-07-16, y no es lo que parecía).
        Las 10 del volcado son **opciones que el manual NO declara y que SICAV NO ofrece**:
        filas muertas del catálogo de Oracle. Ejemplo: la pregunta 28 (parentesco) tiene
        7 huérfanas —Nieto(a), Abuelo(a), Sobrino(a)…— y el manual 11-MU (pág. 56) lista
        exactamente las **6** que Oracle sí deja escribir; SICAV ofrece esas mismas 6.
        Los tres lados coinciden. Comprobado 10/10: SICAV no ofrece NINGUNA huérfana.
        ⇒ La escribibilidad de Oracle **implementa el manual**: no es una limitación, es
        el mecanismo con que Oracle retira opciones que dejaron de ser oficiales.

        Por eso esto sigue fallando ruidosamente aunque "no pueda pasar": si algún día
        SICAV manda una huérfana, no es un problema de Oracle — es que **SICAV se desvió
        del manual** y está ofreciendo una opción que no existe oficialmente. Ese es el
        hallazgo que este guard caza, y por eso el mensaje apunta a SICAV, no a Oracle.

        Si algún día se carga un volcado sin esa columna, `escribibilidad_verificada`
        vuelve a false y esto vuelve a tratarse como pendiente: la diferencia entre "sé
        que se escribe" y "supongo que se escribe" es justo lo que aquí no se puede perder.
        """
        if res_id in cat["huerfanas"]:
            return self._respuesta_falta(
                f"RES_IDRESPUESTA={res_id} ({codigo!r}) es HUÉRFANA: no tiene fila en "
                f"GIC_N_INSTRUMENTOXRESP, así que el procedure haría NO_DATA_FOUND y no "
                f"escribiría nada, en silencio. Las huérfanas son opciones que el manual "
                f"NO declara y que Oracle retiró: filas muertas del catálogo. "
                f"⚠️ Que SICAV esté mandando una significa que **SICAV se desvió del "
                f"manual** y ofrece una opción que oficialmente no existe. Revisar el "
                f"instrumento de SICAV contra el manual (11-MU/14-MU) — el problema está "
                f"de este lado, no en Oracle.", f"{codigo}/huerfana")
        if not cat["_meta"].get("escribibilidad_verificada"):
            return self._respuesta_falta(
                f"RES_IDRESPUESTA={res_id} ({codigo!r}) resuelve, pero el volcado cargado "
                f"no trae la marca de escribibilidad, así que no se puede confirmar que "
                f"tenga fila en GIC_N_INSTRUMENTOXRESP (Query C2 contó 153 huérfanas en "
                f"toda la tabla). Falta reexportar con la columna ESCRIBIBLE.",
                f"{codigo}/escribible_sin_verificar", resuelto=res_id)
        return res_id

    def _respuesta_falta(self, mensaje, clave, resuelto=None, campo="RES_IDRESPUESTA"):
        """Estricto ⇒ lanza; dry-run ⇒ marcador (con el id ya resuelto si lo hay)."""
        if self.estricto:
            raise MapeoPendienteNegocio(f"{campo} — {mensaje}")
        if resuelto is not None:
            return self._pendiente("ESCRIBIBLE", f"res={resuelto} sin verificar")
        return self._pendiente(campo, clave)

    @staticmethod
    def _etiqueta_opcion(respuesta):
        """
        Texto de la opción elegida en SICAV — es lo que se cruza contra Oracle.

        Las preguntas BOOLEAN no tienen `OpcionRespuesta`: su respuesta es 'true'/'false'.
        Oracle guarda esas preguntas con opciones 'Sí'/'No' (p.ej. AHE pre 353,
        indemnización pre 228), así que la respuesta booleana se renderiza a 'Sí'/'No' y
        el cruce por texto la resuelve como cualquier otra. Ver curacion_bloque_pr.md.
        """
        pregunta = getattr(respuesta, "pregunta", None)
        opciones = getattr(pregunta, "opciones", None)
        if opciones is not None:
            opcion = opciones.filter(valor=respuesta.valor).first()
            if opcion is not None:
                return opcion.etiqueta
        if getattr(pregunta, "tipo", None) == "BOOLEAN":
            v = str(getattr(respuesta, "valor", "") or "").strip().lower()
            if v in ("true", "1", "si", "sí", "verdadero"):
                return "Sí"
            if v in ("false", "0", "no", "falso"):
                return "No"
        return None

    def resolver_tipo_pregunta(self, pregunta):
        """
        RXP_TIPOPREGUNTA: se COPIA de Oracle, no se mapea desde SICAV.

        Historia corta de por qué esto no es un crosswalk. El nombre engaña: no es el
        tipo de widget (RADIO/TEXTO/…), es el **NIVEL** de la pregunta — `GE` general
        (hogar) / `IN` individual (persona). Como Oracle ya tiene ese valor para cada
        pregunta en `GIC_N_INSTRUMENTOXPREG.PRE_TIPOPREGUNTA`, el resolver lo lee del
        catálogo y lo devuelve tal cual. No hay nada que traducir: mandar el `tipo` de
        SICAV aquí era el dominio equivocado.

        EVIDENCIA (por si alguien duda de un campo que ya no falla):
        1. **Dominio idéntico, medido en prod** (2026-07-16):
           `SELECT DISTINCT RXP_TIPOPREGUNTA FROM GIC_N_RESPUESTASENCUESTA` → `{GE, IN}`,
           exactamente los valores de `PRE_TIPOPREGUNTA`.
        2. **Significado corroborado por una fuente independiente:** cruzando las 62
           preguntas del volcado contra `Pregunta.nivel` de SICAV —que se llenó aparte,
           leyendo el manual— concuerdan 61/63 (`GE`→HOGAR 18, `IN`→PERSONA 43).
        3. **Las 2 excepciones las cerró el manual A FAVOR de Oracle:** preguntas 8
           (celular) y 35 (étnico). 11-MU pág. 45 (A11) dice textual que el celular
           "se habilita para cada una de las personas del hogar" ⇒ Oracle acierta y el
           `nivel` de SICAV es el que está mal.

        ⚠️ LO QUE AÚN NO SE MIDIÓ (y es barato): que la app vieja escriba, fila a fila,
        el `PRE_TIPOPREGUNTA` de SU pregunta. El `DISTINCT` prueba que el dominio es el
        mismo — necesario, no suficiente. La consulta de control está en §3b-bis-E.4 del
        traspaso. Si saliera que no correlaciona, esto vuelve a ser pendiente.
        """
        cat = catalogos.cargar_respuestas()
        id_preg = _campo_origen(pregunta, "id_preg")
        codigo = getattr(pregunta, "codigo_externo", "?")
        if id_preg is None:
            return self._respuesta_falta(
                f"la pregunta SICAV {codigo!r} no tiene `id_preg`, así que no se puede "
                f"saber su RXP_TIPOPREGUNTA (que se copia del catálogo de Oracle).",
                f"{codigo}/sin_id_preg", campo="RXP_TIPOPREGUNTA")
        fila = cat["preguntas"].get(int(id_preg))
        if fila is None:
            meta = cat["_meta"]
            if meta.get("completo"):
                return self._respuesta_falta(
                    f"la pregunta SICAV {codigo!r} (id_preg={id_preg}) no existe en el "
                    f"instrumento de Oracle, así que no tiene RXP_TIPOPREGUNTA.",
                    f"{codigo}/pre={id_preg}", campo="RXP_TIPOPREGUNTA")
            return self._respuesta_falta(
                f"el RXP_TIPOPREGUNTA de {codigo!r} (id_preg={id_preg}) se copia del "
                f"catálogo de Oracle, y esa pregunta no está en el volcado que tenemos "
                f"— lo que NO quiere decir que no exista en Oracle: {meta.get('cobertura')}.",
                f"{codigo}/fuera_del_volcado", campo="RXP_TIPOPREGUNTA")
        tipo = fila["pre_tipopregunta"]
        if tipo not in catalogos.TIPOPREGUNTA_NIVEL:
            # El dominio medido en prod es {GE, IN}. Un tercer valor significa que el
            # catálogo cambió y que esta suposición caducó: mejor parar que inventar.
            return self._respuesta_falta(
                f"la pregunta {id_preg} trae PRE_TIPOPREGUNTA={tipo!r}, fuera del "
                f"dominio {sorted(catalogos.TIPOPREGUNTA_NIVEL)} medido en prod "
                f"(2026-07-16). El catálogo cambió: reverificar antes de escribir.",
                f"{codigo}/tipo={tipo}", campo="RXP_TIPOPREGUNTA")
        return tipo


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


class UsuarioSinResolver(ValueError):
    """No hay con qué llenar `USU_USUARIOCREACION`, que es NOT NULL en Oracle."""


def _cod_usuario(user):
    """
    Código del encuestador para las columnas de auditoría del legacy.

    Falla en vez de devolver cadena vacía, y el motivo importa: en Oracle la cadena
    vacía **es** NULL, y `USU_USUARIOCREACION` es NOT NULL. Con el valor vacío el
    INSERT moría con ORA-01400 dentro del procedure, cuyo `WHEN OTHERS` se lo
    tragaba: la persona no se escribía y el paso podía darse por bueno. Un fallo
    silencioso a mitad de un hogar es peor que un error.

    `Hogar.creado_por` es nullable, así que este caso es alcanzable.
    """
    codigo = getattr(user, "codigo_usuario", None) or str(getattr(user, "pk", "") or "")
    codigo = codigo.strip()
    if not codigo:
        raise UsuarioSinResolver(
            "El hogar no tiene usuario creador y `USU_USUARIOCREACION` es NOT NULL "
            "en Oracle: sin él, el procedure falla en silencio y la persona no se "
            "escribe. Asigná `Hogar.creado_por` antes de sincronizar."
        )
    return codigo


def binds_hogar(hogar, *, user, catalogos: ResolverCatalogos, instrumento_codigo=None) -> dict:
    """Argumentos de GIC_INSERT_HOGAR1 para un Hogar SICAV."""
    return {
        "usua_creacion": _cod_usuario(user),
        "id_usuario": catalogos.id_usuario_servicio(),
        "id_perfil_usuario": catalogos.id_perfil_servicio(),
        "id_tipo_caracterizacion": catalogos.resolver_tipo_caracterizacion(instrumento_codigo),
    }


def identidad_de_miembro(miembro) -> dict:
    """
    Nombre, documento y fecha de nacimiento del miembro, venga de donde venga.

    ⚠️ Esto NO es un detalle de implementación: es lo que decide si en
    `GIC_PERSONA` queda una persona o una fila fantasma.

    `MiembroHogar.nombre_completo` y `.numero_documento` existen —el modelo lo dice
    en su propio help_text— **solo para miembros que NO están en el RNI**. Cuando
    el miembro viene del padrón, esos campos están VACÍOS y la identidad vive en
    `Victima`, que es a donde apunta la FK. Leer únicamente los campos del miembro
    escribía en el legacy personas sin nombre y sin documento, y los reportes
    —que salen de ahí— quedaban vacíos.

    No se vio en el piloto del 28-jul porque aquel hogar se armó con datos
    sintéticos dados de alta a mano, que sí llenan los campos del miembro.

    Orden: primero la víctima del padrón (la fuente de verdad de identidad),
    después lo capturado en el miembro (alta manual). Nunca al revés.
    """
    victima = getattr(miembro, 'victima', None)
    if victima is not None:
        nombre = ' '.join(p for p in (
            victima.primer_nombre, victima.segundo_nombre,
            victima.primer_apellido, victima.segundo_apellido) if p)
        return {
            'pnombre': (victima.primer_nombre or '').strip().upper(),
            'snombre': (victima.segundo_nombre or '').strip().upper(),
            'papellido': (victima.primer_apellido or '').strip().upper(),
            'sapellido': (victima.segundo_apellido or '').strip().upper(),
            'numero': str(victima.numero_documento or '').strip().upper(),
            'fecha_nacimiento': _a_fecha(victima.fecha_nacimiento),
            'tipo_documento': victima.tipo_documento or miembro.tipo_documento,
            'nombre_completo': nombre,
        }

    pnombre, snombre, papellido, sapellido = _partes_nombre(miembro.nombre_completo)
    return {
        'pnombre': pnombre, 'snombre': snombre,
        'papellido': papellido, 'sapellido': sapellido,
        'numero': (str(miembro.numero_documento).strip().upper()
                   if miembro.numero_documento else ''),
        'fecha_nacimiento': _a_fecha(miembro.fecha_nacimiento),
        'tipo_documento': miembro.tipo_documento,
        'nombre_completo': miembro.nombre_completo or '',
    }


def _a_fecha(valor):
    """
    Fecha lista para el bind de Oracle.

    `Victima.fecha_nacimiento` es un `EncryptedField`: al descifrarlo vuelve como
    TEXTO ('1985-06-15'), no como `date`. Pasarle esa cadena al procedure sería un
    error de tipo, o peor, una fecha mal interpretada.
    """
    import datetime

    if valor in (None, ''):
        return None
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    try:
        return datetime.date.fromisoformat(str(valor)[:10])
    except (ValueError, TypeError):
        return None


def binds_persona(miembro, *, user, estado_oracle, catalogos: ResolverCatalogos) -> dict:
    """Argumentos de GIC_INSERT_PERSONAS para un MiembroHogar SICAV."""
    from django.utils import timezone

    ident = identidad_de_miembro(miembro)
    numero = ident['numero']
    pnombre = ident['pnombre']
    snombre = ident['snombre']
    papellido = ident['papellido']
    sapellido = ident['sapellido']
    binds = {
        "pnombre": pnombre, "snombre": snombre,
        "papellido": papellido, "sapellido": sapellido,
        "fnacimiento": ident['fecha_nacimiento'],
        "tdoc": catalogos.resolver_tdoc(ident['tipo_documento']),
        "usuario": _cod_usuario(user),
        # Hora LOCAL y sin zona: `GIC_PERSONA.USU_FCREACION` es un DATE de Oracle, que
        # no guarda zona horaria. Mandar el datetime aware de Django escribía la hora
        # UTC —cinco horas en el futuro— en una columna que todos los reportes leen
        # como hora de Colombia.
        "usu_fcreacion": timezone.localtime(timezone.now()).replace(tzinfo=None),
        "ndocu": numero,
        "relac": catalogos.resolver_relac_de_miembro(miembro),
        # Se pasa el miembro entero, no un getattr con default: el resolver debe poder
        # distinguir "el campo no existe" de "existe y vale None". Ver resolver_t_victima.
        "t_victima": catalogos.resolver_t_victima(miembro),
        "fuentee": "SICAV",
        # OJO: este `estado` es el de la PERSONA (`PER_ESTADO`), no el del hogar. Su
        # dominio es INCLUIDO / NO INCLUIDO —el legacy los compara así en
        # GIC_OBTENER_PERSONAS—, no 'ACTIVA', que es el estado del HOGAR. Con
        # 'ACTIVA' la persona existía en la tabla pero el legacy no la devolvía nunca.
        "estado": estado_persona_oracle(miembro),
    }
    for extra in _EXTRAS_PERSONA:
        binds[extra] = catalogos.resolver_extra_persona(extra, miembro)
    return binds


#: Los dos únicos valores que el legacy reconoce en `PER_ESTADO`.
PERSONA_INCLUIDA = "INCLUIDO"
PERSONA_NO_INCLUIDA = "NO INCLUIDO"


def estado_persona_oracle(miembro) -> str:
    """
    `PER_ESTADO` a partir de lo que SICAV ya sabe del miembro.

    El dato existe: `MiembroHogar.estado_inclusion` guarda si la persona está
    incluida en el RUV. `NO_VERIFICADO` —el alta manual, que no se pudo verificar
    contra el RUV— se escribe como NO INCLUIDO, que es lo único que el legacy sabe
    representar; la matización queda en SICAV, que es donde se puede explicar.
    """
    if getattr(miembro, "estado_inclusion", None) == "INCLUIDO":
        return PERSONA_INCLUIDA
    victima = getattr(miembro, "victima", None)
    if victima is not None and getattr(victima, "estado_ruv", None) == "INCLUIDO":
        return PERSONA_INCLUIDA
    return PERSONA_NO_INCLUIDA


def binds_miembro(hog_codigo, per_idpersona, *, user, catalogos: ResolverCatalogos,
                  miembro=None) -> dict:
    """
    Argumentos de GIC_INSERT_MIEMBRO_HOGAR.

    `encuestada` iba en `'S'` para todos, y el legacy compara contra `'SI'`
    (`GIC_ACTUALIZA_ENCUESTADO` escribe ese literal). Con `'S'`, el campo
    JEFE_HOGAR de los reportes salía 'NO' para todo el hogar: nadie figuraba como
    la persona entrevistada.

    Y no va para todos: es **la persona a la que se le hizo la entrevista**, o sea
    el autorizado del hogar. Marcar a los cinco miembros como encuestados es una
    afirmación falsa sobre cómo se levantó el dato.
    """
    entrevistada = bool(getattr(miembro, "es_autorizado", False)) if miembro else False
    return {
        "idhogar": hog_codigo,
        "id_persona": per_idpersona,
        "usuario": _cod_usuario(user),
        "id_usuario": catalogos.id_usuario_servicio(),
        "encuestada": "SI" if entrevistada else "NO",
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
def per_idpersona_de_respuesta(respuesta, mapa_personas, catalogos: ResolverCatalogos,
                               jefe_per_idpersona=None):
    """
    PER_IDPERSONA para una respuesta.

    Las de nivel PERSONA salen del mapa {miembro_pk: per_idpersona} que dejó el paso
    PERSONA. Las de nivel HOGAR llegan con `miembro=NULL` en SICAV y se anclan al
    **autorizado/jefe del hogar** (`jefe_per_idpersona`): es la persona que responde
    por el hogar, y GIC_N_RESPUESTASENCUESTA.PER_IDPERSONA es nullable, así que el
    jefe es la elección fiel (no un literal inventado). Sin jefe no se puede anclar.
    """
    if respuesta.miembro_id is None:
        if jefe_per_idpersona is not None:
            return jefe_per_idpersona
        if catalogos.estricto:
            raise MapeoPendienteNegocio(
                "PPER_IDPERSONA: respuesta de nivel HOGAR (miembro NULL) y el hogar no "
                "tiene miembro autorizado (es_autorizado=True) al que anclarla. Marca un "
                "autorizado en el hogar."
            )
        return "‹PEND:PPER_IDPERSONA(nivel_hogar)›"
    return mapa_personas.get(respuesta.miembro_id)


def _texto_respuesta(respuesta, catalogos: ResolverCatalogos):
    """
    RXP_TEXTORESPUESTA. Para las preguntas geográficas (PRE_TIPOCAMPO='DP') traduce
    el código DANE de SICAV al ID_MUNI_DEPTO de Oracle; el resto va tal cual.

    Medido en producción (2026-07-28): esas preguntas guardan el DANE SIN cero a la
    izquierda y cruzan 28.151/28.151 (100%) contra GIC_MUNICIPIO. SICAV lo guarda
    CON cero, así que sin esta traducción se escribiría un texto que ningún reporte
    territorial resuelve — y el procedure se traga el problema sin avisar.
    """
    valor = respuesta.valor
    pregunta = getattr(respuesta, "pregunta", None)
    id_preg = _campo_origen(pregunta, "id_preg")
    if id_preg is None or int(id_preg) not in catalogos_mod.cargar_geografia()["preguntas_dp"]:
        return valor

    normalizado = catalogos_mod.normalizar_codigo_municipio(valor)
    if normalizado is not None:
        return normalizado
    if catalogos.estricto:
        raise MapeoDesconocido(
            f"Geografía: la pregunta {id_preg} es de departamento/municipio y el valor "
            f"{valor!r} de SICAV no cruza contra GIC_MUNICIPIO.ID_MUNI_DEPTO "
            f"({len(catalogos_mod.cargar_geografia()['municipios'])} municipios en "
            f"Oracle). No se escribe un código que los reportes no van a resolver."
        )
    return f"‹PEND:GEOGRAFIA({valor})›"


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
        "prxp_textorespuesta": _texto_respuesta(respuesta, catalogos),
        "prxp_tipopreguntarespuesta": catalogos.resolver_tipo_pregunta(respuesta.pregunta),
        "pins_idinstrumento": catalogos.resolver_ins_idinstrumento(instrumento),
        "pusu_usuariocreacion": _cod_usuario(user),
        # PPER_IDPREGUNTAPADRE: el procedure lo usa como pId_Pregunta/pID_RESPUESTA
        # para SP_BORRADORESPUESTAS, SP_BORRADOVALIDADORES y las preguntas derivadas.
        # SICAV no modela "pregunta padre" con id Oracle ⇒ pendiente.
        "pper_idpreguntapadre": catalogos.resolver_pregunta_padre(),
        # PBANDERA=1 dispara SP_BORRADORESPUESTAS (borra+inserta la respuesta del par
        # hogar/pregunta). En un hogar NUEVO el borrado es no-op y hace la escritura
        # idempotente (re-correr no duplica). Decidido con dato (2026-07-24).
        "pbandera": catalogos.resolver_pbandera(),
    }
