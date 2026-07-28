"""
Escritor hacia Oracle legacy — MÁQUINA DE ESTADOS REANUDABLE (Etapa A).

Orquesta los procedures oficiales en orden de dependencia para materializar una
caracterización SICAV en Oracle:

    HOGAR → (por miembro: PERSONA → MIEMBRO) → TERRITORIO → (por respuesta: RESPUESTA)

Estado del cableado (2026-07-16): los cinco pasos están cableados. TERRITORIO
resuelve ids REALES contra el crosswalk de GIC_N_DT_PUNTOS_ATENCION. RESPUESTA
tiene la fontanería completa pero sus ids (INS_IDINSTRUMENTO, RES_IDRESPUESTA,
RXP_TIPOPREGUNTA, PPER_IDPERSONA de nivel hogar, PBANDERA) están PENDIENTES de
dato/negocio: en DRY-RUN salen como marcadores ‹PEND:...› y en modo estricto
lanzan, para que nunca se escriba un id inventado.

Por qué máquina de estados y no transacción (ver ruta_escritura.md §4):
- Cada procedure hace COMMIT interno ⇒ no hay rollback envolvente posible.
- Cada procedure traga excepciones (WHEN OTHERS) ⇒ hay que VERIFICAR por SELECT.
El ledger `RegistroEscrituraOracle` es la memoria: cada paso VERIFICADO no se
repite (idempotencia), y una corrida interrumpida se REANUDA desde el primer
paso no verificado.

DRY-RUN por defecto: no conecta, no ejecuta; registra el bloque PL/SQL exacto y
el payload redactado por cada paso. `confirmar=True` (+ destino explícito) es la
ÚNICA vía que abre conexión y escribe — y requiere aprobación de Javier.
"""
from dataclasses import dataclass, field

from apps.sincronizacion.models import (
    EstadoPaso, PasoEscritura, RegistroEscrituraOracle,
)
from . import procedimientos as P
from . import verificacion as V
from . import mapeo
from .conexion import abrir_conexion

# 'ACTIVA' de Oracle = hogar abierto (equivale a 'BORRADOR' en Django).
ESTADO_ORACLE_ABIERTO = "ACTIVA"


@dataclass
class ResultadoPaso:
    paso: str
    origen_id: str
    estado: str
    bloque: str
    detalle: dict = field(default_factory=dict)


@dataclass
class ResultadoHogar:
    hog_codigo_sicav: str
    dry_run: bool
    pasos: list = field(default_factory=list)  # list[ResultadoPaso]

    def resumen(self) -> dict:
        from collections import Counter
        c = Counter(p.estado for p in self.pasos)
        return {"total": len(self.pasos), **c}


class EscritorOracle:
    """
    Orquesta la escritura de UN hogar. Reutilizable por lote (ver management
    command). `confirmar=False` ⇒ DRY-RUN puro (sin conexión).
    """

    def __init__(self, *, confirmar: bool = False, destino: str = "",
                 catalogos: mapeo.ResolverCatalogos = None):
        self.confirmar = confirmar
        self.destino = destino
        if confirmar:
            if not destino:
                raise ValueError("confirmar=True requiere destino ('local'|'produccion').")
            if catalogos is None:
                raise ValueError(
                    "confirmar=True requiere un ResolverCatalogos REAL (no placeholder)."
                )
            self.catalogos = catalogos
        else:
            # DRY-RUN: resolver real en modo NO estricto → marcadores ‹PEND:...›
            # para lo que aún no tiene mapeo, valores reales para lo que sí.
            self.catalogos = catalogos or mapeo.ResolverCatalogos.desde_settings(estricto=False)
        self._conn = None
        self._cursor = None

    # ── ciclo de conexión (solo ruta confirmada) ─────────────────────────────
    def __enter__(self):
        if self.confirmar:
            self._conn = abrir_conexion(self.destino)
            self._cursor = self._conn.cursor()
        return self

    def __exit__(self, *exc):
        if self._cursor is not None:
            self._cursor.close()
        if self._conn is not None:
            self._conn.close()
        return False

    # ── helpers de ledger (idempotencia + auditoría) ─────────────────────────
    def _ya_verificado(self, hogar, paso, origen_id) -> bool:
        return self._registro_verificado(hogar, paso, origen_id) is not None

    def _registro_verificado(self, hogar, paso, origen_id):
        """
        El registro VERIFICADO de este paso **en ESTE destino** (o None).

        Sirve para que un re-run idempotente recupere el destino ya escrito
        (HOG_CODIGO / PER_IDPERSONA): los pasos siguientes lo necesitan y, si no se
        recuperara, se anclarían con el código SICAV en vez del real de Oracle.

        ⚠️ El filtro por `destino_entorno` NO es cosmético (bug encontrado el
        2026-07-28, antes del primer piloto). Sin él, un hogar ya escrito contra la
        réplica LOCAL se daba por hecho al correr contra PRODUCCIÓN: el paso HOGAR
        devolvía `idempotente=True` sin escribir una sola fila, y los pasos
        siguientes se anclaban a un HOG_CODIGO que en producción no existe. El
        comando habría reportado "VERIFICADO" en todos los pasos **sin haber
        migrado nada** — el fallo silencioso exacto que esta capa existe para evitar.

        Cada destino lleva su propia contabilidad: escribir en local no adelanta
        trabajo en producción, ni al revés.
        """
        return RegistroEscrituraOracle.objects.filter(
            hogar=hogar, paso=paso, origen_id=str(origen_id),
            estado=EstadoPaso.VERIFICADO,
            destino_entorno=self.destino,
        ).first()

    @staticmethod
    def _id_oracle(valor):
        """
        Solo un id numérico REAL entra a las columnas destino_* del ledger.

        En DRY-RUN estos valores pueden ser None o un marcador ‹PEND:...› (p.ej. el
        PER_IDPERSONA de una respuesta de nivel hogar). Esas columnas describen lo
        que quedó en Oracle, así que un marcador no tiene nada que hacer ahí: se
        guarda NULL y el marcador sigue visible en el payload y en el bloque PL/SQL.
        """
        return valor if isinstance(valor, int) else None

    def _registrar(self, hogar, paso, origen_id, *, res: P.ResultadoInvocacion,
                   estado, hog_codigo="", per_idpersona=None, detalle=None):
        # `destino_entorno` forma parte de la CLAVE, no de los defaults: si fuera un
        # default, escribir en producción sobrescribiría el registro de la corrida
        # local en vez de convivir con él (ver la constraint del modelo).
        reg, _ = RegistroEscrituraOracle.objects.update_or_create(
            hogar=hogar, paso=paso, origen_id=str(origen_id),
            destino_entorno="" if not self.confirmar else self.destino,
            defaults=dict(
                estado=estado,
                bloque_plsql=res.bloque,
                payload=res.binds_redactados,
                resultado=detalle or {},
                destino_hog_codigo=hog_codigo or "",
                destino_per_idpersona=self._id_oracle(per_idpersona),
            ),
        )
        reg.intento = (reg.intento or 0) + 1
        reg.save(update_fields=["intento"])
        return reg

    def _ejecutar_paso(self, proc, binds):
        """Invoca (o simula) y devuelve el ResultadoInvocacion."""
        return P.invocar(proc, binds, confirmar=self.confirmar, cursor=self._cursor)

    @staticmethod
    def _fusionar(resultados):
        """
        Funde varias invocaciones en un ResultadoInvocacion único para el ledger.

        La cascada territorial son 4 procedures pero UN paso de la máquina (un solo
        registro, origen = la sesión). Se conservan los 4 bloques y sus binds para
        que la auditoría muestre exactamente qué se ejecutó y en qué orden.
        """
        return P.ResultadoInvocacion(
            procedimiento=" → ".join(r.procedimiento for r in resultados),
            bloque="\n\n".join(r.bloque for r in resultados),
            binds_redactados={r.procedimiento: r.binds_redactados for r in resultados},
            ejecutado=all(r.ejecutado for r in resultados),
            salidas={},
        )

    # ── pasos de la máquina ──────────────────────────────────────────────────
    def paso_hogar(self, hogar, *, user, instrumento_codigo=None) -> ResultadoPaso:
        origen = hogar.pk
        reg = self._registro_verificado(hogar, PasoEscritura.HOGAR, origen)
        if reg is not None:
            # Re-run: recupera el HOG_CODIGO real ya escrito para que territorio y
            # respuestas se anclen a él, no al código SICAV de referencia.
            return ResultadoPaso(PasoEscritura.HOGAR, str(origen), EstadoPaso.VERIFICADO,
                                 "", {"idempotente": True, "hog_codigo": reg.destino_hog_codigo})
        binds = mapeo.binds_hogar(hogar, user=user, catalogos=self.catalogos,
                                  instrumento_codigo=instrumento_codigo)
        res = self._ejecutar_paso(P.GIC_INSERT_HOGAR1, binds)

        estado, hog_codigo, detalle = EstadoPaso.DRY_RUN, "", {}
        if self.confirmar:
            marcador = res.salidas.get("marcador")
            ok, detalle = V.verificar_hogar(
                self._cursor, id_usuario=binds["id_usuario"], marcador=marcador,
            )
            hog_codigo = detalle.get("hog_codigo") or ""
            estado = EstadoPaso.VERIFICADO if ok else EstadoPaso.FALLIDO
        self._registrar(hogar, PasoEscritura.HOGAR, origen, res=res, estado=estado,
                        hog_codigo=hog_codigo, detalle=detalle)
        return ResultadoPaso(PasoEscritura.HOGAR, str(origen), estado, res.bloque, detalle)

    def paso_persona(self, hogar, miembro, *, user, hog_codigo) -> ResultadoPaso:
        origen = miembro.pk
        reg = self._registro_verificado(hogar, PasoEscritura.PERSONA, origen)
        if reg is not None:
            # Re-run: recupera el PER_IDPERSONA real para el mapa que ancla respuestas.
            return ResultadoPaso(PasoEscritura.PERSONA, str(origen), EstadoPaso.VERIFICADO,
                                 "", {"idempotente": True, "per_idpersona": reg.destino_per_idpersona})
        binds = mapeo.binds_persona(
            miembro, user=user, estado_oracle=ESTADO_ORACLE_ABIERTO, catalogos=self.catalogos,
        )
        res = self._ejecutar_paso(P.GIC_INSERT_PERSONAS, binds)

        estado, per_id, detalle = EstadoPaso.DRY_RUN, None, {}
        if self.confirmar:
            per_id = res.salidas.get("valsecuencia")
            ok, detalle = V.verificar_persona(self._cursor, per_idpersona=per_id)
            estado = EstadoPaso.VERIFICADO if ok else EstadoPaso.FALLIDO
        self._registrar(hogar, PasoEscritura.PERSONA, origen, res=res, estado=estado,
                        hog_codigo=hog_codigo, per_idpersona=per_id, detalle=detalle)
        return ResultadoPaso(PasoEscritura.PERSONA, str(origen), estado, res.bloque, detalle)

    def paso_miembro(self, hogar, miembro, *, user, hog_codigo, per_idpersona) -> ResultadoPaso:
        origen = miembro.pk
        if self._ya_verificado(hogar, PasoEscritura.MIEMBRO, origen):
            return ResultadoPaso(PasoEscritura.MIEMBRO, str(origen), EstadoPaso.VERIFICADO,
                                 "", {"idempotente": True})
        binds = mapeo.binds_miembro(hog_codigo, per_idpersona, user=user, catalogos=self.catalogos)
        res = self._ejecutar_paso(P.GIC_INSERT_MIEMBRO_HOGAR, binds)

        estado, detalle = EstadoPaso.DRY_RUN, {}
        if self.confirmar:
            ok, detalle = V.verificar_miembro(
                self._cursor, hog_codigo=hog_codigo, per_idpersona=per_idpersona,
            )
            estado = EstadoPaso.VERIFICADO if ok else EstadoPaso.FALLIDO
        self._registrar(hogar, PasoEscritura.MIEMBRO, origen, res=res, estado=estado,
                        hog_codigo=hog_codigo, per_idpersona=per_idpersona, detalle=detalle)
        return ResultadoPaso(PasoEscritura.MIEMBRO, str(origen), estado, res.bloque, detalle)

    def paso_territorio(self, hogar, sesion, *, hog_codigo) -> ResultadoPaso:
        """
        Cascada territorial: 4 procedures, 1 paso de la máquina (origen = sesión).

        Es el paso que históricamente rompió los reportes cuando quedó incompleto,
        así que la verificación no comprueba "se llamó", sino que la fila de
        GIC_N_RELACION_DT_PUNTO tenga IDDT, IDMUNATEN e IDPUNTOATEN no nulos
        (V.verificar_territorio).
        """
        origen = sesion.pk
        if self._ya_verificado(hogar, PasoEscritura.TERRITORIO, origen):
            return ResultadoPaso(PasoEscritura.TERRITORIO, str(origen), EstadoPaso.VERIFICADO,
                                 "", {"idempotente": True})
        territorio = self.catalogos.resolver_territorio(sesion)
        llamadas = mapeo.binds_territorio(hog_codigo, territorio)
        resultados = [self._ejecutar_paso(proc, binds) for proc, binds in llamadas]
        res = self._fusionar(resultados)

        estado, detalle = EstadoPaso.DRY_RUN, {"territorio_resuelto": territorio}
        if self.confirmar:
            ok, detalle = V.verificar_territorio(self._cursor, hog_codigo=hog_codigo)
            estado = EstadoPaso.VERIFICADO if ok else EstadoPaso.FALLIDO
        self._registrar(hogar, PasoEscritura.TERRITORIO, origen, res=res, estado=estado,
                        hog_codigo=hog_codigo, detalle=detalle)
        return ResultadoPaso(PasoEscritura.TERRITORIO, str(origen), estado, res.bloque, detalle)

    def paso_respuesta(self, hogar, respuesta, *, user, hog_codigo, per_idpersona,
                       instrumento) -> ResultadoPaso:
        """Una respuesta del instrumento vía SP_SET_RESPUESTAS_DE_ENCUESTA."""
        origen = respuesta.pk
        if self._ya_verificado(hogar, PasoEscritura.RESPUESTA, origen):
            return ResultadoPaso(PasoEscritura.RESPUESTA, str(origen), EstadoPaso.VERIFICADO,
                                 "", {"idempotente": True})
        binds = mapeo.binds_respuesta(
            respuesta, user=user, catalogos=self.catalogos, hog_codigo=hog_codigo,
            per_idpersona=per_idpersona, instrumento=instrumento,
        )
        res = self._ejecutar_paso(P.SP_SET_RESPUESTAS_DE_ENCUESTA, binds)

        estado, detalle = EstadoPaso.DRY_RUN, {}
        if self.confirmar:
            ok, detalle = V.verificar_respuesta(
                self._cursor, hog_codigo=hog_codigo, per_idpersona=per_idpersona,
                res_idrespuesta=binds["pres_idrespuesta"],
            )
            estado = EstadoPaso.VERIFICADO if ok else EstadoPaso.FALLIDO
        self._registrar(hogar, PasoEscritura.RESPUESTA, origen, res=res, estado=estado,
                        hog_codigo=hog_codigo, per_idpersona=per_idpersona, detalle=detalle)
        return ResultadoPaso(PasoEscritura.RESPUESTA, str(origen), estado, res.bloque, detalle)

    def procesar_hogar(self, hogar, *, user=None) -> ResultadoHogar:
        """
        Ejecuta (o simula) la máquina completa para `hogar`. En DRY-RUN el
        `hog_codigo` de destino aún no existe; se usa el codigo_hogar SICAV como
        referencia visible en los bloques.
        """
        user = user or hogar.creado_por
        rh = ResultadoHogar(hog_codigo_sicav=hogar.codigo_hogar, dry_run=not self.confirmar)

        # Sesión que ancla instrumento y territorio de ATENCIÓN (el territorio NO
        # cuelga del hogar: Hogar.municipio es residencia, eje distinto).
        # ⚠️ Se toma la PRIMERA sesión: GIC_N_RELACION_DT_PUNTO admite una sola fila
        # por hogar (PK hogarcodigo+idpersona='1'), así que si un hogar tuviera
        # varias sesiones con territorios distintos, Oracle solo puede guardar uno.
        # Pendiente de confirmar con negocio si ese caso existe.
        sesion = hogar.sesiones.select_related(
            "instrumento", "direccion_territorial", "departamento_atencion",
            "municipio_atencion", "punto_atencion",
        ).first()
        instrumento_codigo = sesion.instrumento.codigo if sesion else None

        # 1. HOGAR
        r_hogar = self.paso_hogar(hogar, user=user, instrumento_codigo=instrumento_codigo)
        rh.pasos.append(r_hogar)
        # En confirmado, el HOG_CODIGO real sale de la verificación; en DRY-RUN se
        # usa el codigo SICAV como marcador de referencia en los siguientes bloques.
        hog_codigo = r_hogar.detalle.get("hog_codigo") or hogar.codigo_hogar

        # 2. por miembro: PERSONA → MIEMBRO. El mapa miembro→PER_IDPERSONA que deja
        #    este bucle es lo que después ancla cada respuesta de nivel PERSONA.
        mapa_personas = {}
        for miembro in hogar.miembros.all():
            r_per = self.paso_persona(hogar, miembro, user=user, hog_codigo=hog_codigo)
            rh.pasos.append(r_per)
            per_id = r_per.detalle.get("per_idpersona")  # None en DRY-RUN
            mapa_personas[miembro.pk] = per_id
            rh.pasos.append(
                self.paso_miembro(hogar, miembro, user=user,
                                  hog_codigo=hog_codigo, per_idpersona=per_id)
            )

        if sesion is None:
            # Sin sesión no hay territorio de atención ni respuestas que escribir.
            return rh

        # 3. TERRITORIO (cascada de 4 procedures, ver paso_territorio)
        rh.pasos.append(self.paso_territorio(hogar, sesion, hog_codigo=hog_codigo))

        # 4. RESPUESTAS del instrumento. Las de nivel HOGAR se anclan al autorizado
        #    (jefe); las de nivel PERSONA a su propio miembro (mapa_personas).
        jefe = hogar.miembros.filter(es_autorizado=True).first()
        jefe_per_id = mapa_personas.get(jefe.pk) if jefe else None
        respuestas = sesion.respuestas.select_related("pregunta").all()
        for respuesta in respuestas:
            per_id = mapeo.per_idpersona_de_respuesta(
                respuesta, mapa_personas, self.catalogos, jefe_per_idpersona=jefe_per_id)
            rh.pasos.append(
                self.paso_respuesta(hogar, respuesta, user=user, hog_codigo=hog_codigo,
                                    per_idpersona=per_id, instrumento=sesion.instrumento)
            )
        return rh
