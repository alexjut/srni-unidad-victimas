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
- Territorio: los códigos DANE (departamento/municipio) son estándar nacional y
  SICAV ya los tiene (`codigo_dane`) → pass-through REAL. Los ids surrogate de DT
  y punto de atención se toman del `codigo` SICAV como mejor aproximación y se
  marcan para confirmar contra `GIC_N_DT_PUNTOS_ATENCION` (dato de prod).
- Usuario/perfil de servicio: `settings.ORACLE_LEGACY['USUARIO_SERVICIO_ID' / ...]`
  — PENDIENTE de confirmación de negocio (Oscar/UARIV). Sin él, no se confirma.

Cero PII expuesta a logs: los binds con PII van marcados en procedimientos.py y se
redactan en auditoría; este módulo solo arma los valores.
"""
from . import catalogos


class MapeoDesconocido(ValueError):
    """Un valor SICAV no tiene equivalente en el catálogo Oracle (no se inventa)."""


class MapeoPendienteNegocio(ValueError):
    """Un valor depende de una decisión de negocio aún no confirmada."""


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

    def resolver_t_victima(self, valor):
        return self._resolver(self._tipo_victima, valor, "tipo_victima")

    # ── catálogo 5 — territorio (cascada) — SE DEJA APARTE (volumen) ────────────
    def resolver_territorio(self, sesion) -> dict:
        """
        PENDIENTE (aparte por volumen). Los ids de GIC_N_DT_PUNTOS_ATENCION (IDDT,
        IDPUNTOATENCION, IDMUNICIPIO) son SURROGATE de Oracle, NO códigos DANE
        (verificado: TOLIMA=30, ALVARADO=32, no DANE). El crosswalk real (1370
        filas) está en catalogos_oracle.json; la resolución SICAV→Oracle requiere
        cruce por nombre DT/punto/municipio y se implementará en un incremento
        aparte. Hoy devuelve marcador/lanza para no producir ids inventados.
        """
        if self.estricto:
            raise MapeoDesconocido(
                "TERRITORIO: resolución SICAV→GIC_N_DT_PUNTOS_ATENCION pendiente "
                "(aparte por volumen; ids son surrogate Oracle, no DANE)."
            )
        return {"id_dt": self._pendiente("TERRITORIO_IDDT", "?"),
                "id_pt": self._pendiente("TERRITORIO_IDPT", "?"),
                "id_ma": self._pendiente("TERRITORIO_IDMA", "?")}


# ── extras de GIC_INSERT_PERSONAS fuera del alcance de esta tarea ──────────────
# ID_DECLAR, ID_PERS_FUENTE, ID_SINIESTRO, IDPERMI no están en los catálogos 1-5.
# Son NUMBER (posiblemente opcionales). Hasta confirmar su semántica se tratan como
# pendientes explícitos (marcador en dry-run; el flujo confirmado exigirá definirlos).
_EXTRAS_PERSONA = ("id_declar", "id_pers_fuente", "id_siniestro", "idpermi")


def _extra_pendiente(resolver, nombre):
    if resolver.estricto:
        raise MapeoPendienteNegocio(f"{nombre.upper()} (GIC_INSERT_PERSONAS) sin definir.")
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
        "t_victima": catalogos.resolver_t_victima(getattr(miembro, "tipo_victima", None)),
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
