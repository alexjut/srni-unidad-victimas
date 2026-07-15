"""
Escritor hacia Oracle legacy — MÁQUINA DE ESTADOS REANUDABLE (Etapa A).

Orquesta los procedures oficiales en orden de dependencia para materializar una
caracterización SICAV en Oracle:

    HOGAR → (por miembro: PERSONA → MIEMBRO) → TERRITORIO → (por respuesta: RESPUESTA)

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
        return RegistroEscrituraOracle.objects.filter(
            hogar=hogar, paso=paso, origen_id=str(origen_id),
            estado=EstadoPaso.VERIFICADO,
        ).exists()

    def _registrar(self, hogar, paso, origen_id, *, res: P.ResultadoInvocacion,
                   estado, hog_codigo="", per_idpersona=None, detalle=None):
        reg, _ = RegistroEscrituraOracle.objects.update_or_create(
            hogar=hogar, paso=paso, origen_id=str(origen_id),
            defaults=dict(
                estado=estado,
                bloque_plsql=res.bloque,
                payload=res.binds_redactados,
                resultado=detalle or {},
                destino_hog_codigo=hog_codigo or "",
                destino_per_idpersona=per_idpersona,
                destino_entorno="" if not self.confirmar else self.destino,
            ),
        )
        reg.intento = (reg.intento or 0) + 1
        reg.save(update_fields=["intento"])
        return reg

    def _ejecutar_paso(self, proc, binds):
        """Invoca (o simula) y devuelve el ResultadoInvocacion."""
        return P.invocar(proc, binds, confirmar=self.confirmar, cursor=self._cursor)

    # ── pasos de la máquina ──────────────────────────────────────────────────
    def paso_hogar(self, hogar, *, user, instrumento_codigo=None) -> ResultadoPaso:
        origen = hogar.pk
        if self._ya_verificado(hogar, PasoEscritura.HOGAR, origen):
            return ResultadoPaso(PasoEscritura.HOGAR, str(origen), EstadoPaso.VERIFICADO,
                                 "", {"idempotente": True})
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
        if self._ya_verificado(hogar, PasoEscritura.PERSONA, origen):
            return ResultadoPaso(PasoEscritura.PERSONA, str(origen), EstadoPaso.VERIFICADO,
                                 "", {"idempotente": True})
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

    def procesar_hogar(self, hogar, *, user=None) -> ResultadoHogar:
        """
        Ejecuta (o simula) la máquina completa para `hogar`. En DRY-RUN el
        `hog_codigo` de destino aún no existe; se usa el codigo_hogar SICAV como
        referencia visible en los bloques.
        """
        user = user or hogar.creado_por
        rh = ResultadoHogar(hog_codigo_sicav=hogar.codigo_hogar, dry_run=not self.confirmar)

        # Instrumento de la primera sesión del hogar → tipo de caracterización.
        sesion = hogar.sesiones.select_related("instrumento").first()
        instrumento_codigo = sesion.instrumento.codigo if sesion else None

        # 1. HOGAR
        r_hogar = self.paso_hogar(hogar, user=user, instrumento_codigo=instrumento_codigo)
        rh.pasos.append(r_hogar)
        # En confirmado, el HOG_CODIGO real sale de la verificación; en DRY-RUN se
        # usa el codigo SICAV como marcador de referencia en los siguientes bloques.
        hog_codigo = r_hogar.detalle.get("hog_codigo") or hogar.codigo_hogar

        # 2. por miembro: PERSONA → MIEMBRO
        for miembro in hogar.miembros.all():
            r_per = self.paso_persona(hogar, miembro, user=user, hog_codigo=hog_codigo)
            rh.pasos.append(r_per)
            per_id = r_per.detalle.get("per_idpersona")  # None en DRY-RUN
            rh.pasos.append(
                self.paso_miembro(hogar, miembro, user=user,
                                  hog_codigo=hog_codigo, per_idpersona=per_id)
            )

        # 3. TERRITORIO y 4. RESPUESTAS dependen de catálogos geográficos y del
        #    instrumento (ids Oracle). Se detallan en el diseño; su cableado real
        #    espera el mapeo de catálogos (ver mapeo.MapeoPendiente / diseño §Open).
        return rh
