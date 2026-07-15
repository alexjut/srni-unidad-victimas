"""
Conexión oracledb (thin) hacia el Oracle legacy, parametrizada por settings.

NUNCA se conecta al importar el módulo. `abrir_conexion()` solo se invoca desde
la ruta confirmada del escritor. El destino se resuelve de forma explícita:

- 'local'      → settings.ORACLE_LEGACY (default: Oracle Docker local, sin datos).
- 'produccion' → requiere que el operador exporte las variables ORACLE_PROD_*
                 en el entorno; jamás hay credenciales de prod en el repo ni en
                 settings. Sin esas variables, aborta.

Regla de oro: la EXISTENCIA de esta capa no habilita ninguna escritura. Se espera
aprobación explícita de Javier antes de la primera conexión, incluso a local.
"""
import os

from django.conf import settings

DESTINO_LOCAL = "local"
DESTINO_PRODUCCION = "produccion"


class DestinoNoConfigurado(RuntimeError):
    """Falta configuración para el destino solicitado (nunca se hardcodea prod)."""


def _config_local() -> dict:
    cfg = getattr(settings, "ORACLE_LEGACY", {}) or {}
    return {
        "host": cfg.get("HOST", "localhost"),
        "port": int(cfg.get("PORT", 1521)),
        "service": cfg.get("SERVICE", "FREEPDB1"),
        "user": cfg.get("USER", "RNIENTREVISTA"),
        "password": cfg.get("PASSWORD", ""),
    }


def _config_produccion() -> dict:
    # Producción SOLO por variables de entorno del operador. Cero valores por
    # defecto: si falta cualquiera, no se conecta.
    faltantes = [
        v for v in ("ORACLE_PROD_HOST", "ORACLE_PROD_SERVICE",
                    "ORACLE_PROD_USER", "ORACLE_PROD_PASSWORD")
        if not os.environ.get(v)
    ]
    if faltantes:
        raise DestinoNoConfigurado(
            "Faltan variables de entorno para producción: " + ", ".join(faltantes)
        )
    return {
        "host": os.environ["ORACLE_PROD_HOST"],
        "port": int(os.environ.get("ORACLE_PROD_PORT", 1521)),
        "service": os.environ["ORACLE_PROD_SERVICE"],
        "user": os.environ["ORACLE_PROD_USER"],
        "password": os.environ["ORACLE_PROD_PASSWORD"],
    }


def resolver_config(destino: str) -> dict:
    if destino == DESTINO_LOCAL:
        return _config_local()
    if destino == DESTINO_PRODUCCION:
        return _config_produccion()
    raise DestinoNoConfigurado(f"Destino desconocido: {destino!r}")


def abrir_conexion(destino: str):
    """
    Abre una conexión oracledb thin al destino indicado. Import perezoso de
    oracledb para que importar esta capa NO requiera el driver ni toque la red.
    """
    import oracledb  # import diferido a propósito

    cfg = resolver_config(destino)
    dsn = f"{cfg['host']}:{cfg['port']}/{cfg['service']}"
    return oracledb.connect(user=cfg["user"], password=cfg["password"], dsn=dsn)
