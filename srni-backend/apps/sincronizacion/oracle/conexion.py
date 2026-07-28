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

# Hosts que cuentan como "la réplica local". El destino 'local' NO puede
# resolverse a ningún otro: settings.ORACLE_LEGACY se alimenta de la variable
# de entorno ORACLE_LEGACY_HOST y una sesión que la haya exportado apuntando a
# prod (p.ej. para una lectura de referencia) convertiría
# `--destino local --confirmar` en una escritura a producción con el banner
# diciendo "local". La guarda de abajo lo impide.
HOSTS_LOCALES = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0",
                           "host.docker.internal"})


class DestinoNoConfigurado(RuntimeError):
    """Falta configuración para el destino solicitado (nunca se hardcodea prod)."""


class DestinoLocalNoLocal(DestinoNoConfigurado):
    """El destino 'local' resolvió a un host que no es la réplica local."""


def _config_local() -> dict:
    cfg = getattr(settings, "ORACLE_LEGACY", {}) or {}
    host = str(cfg.get("HOST", "localhost")).strip()
    if host.lower() not in HOSTS_LOCALES:
        raise DestinoLocalNoLocal(
            f"El destino 'local' apunta a {host!r}, que no es la réplica local "
            f"(permitidos: {', '.join(sorted(HOSTS_LOCALES))}). "
            "Casi siempre significa que la sesión tiene ORACLE_LEGACY_HOST "
            "exportado hacia otro servidor. Corrige la variable; para escribir "
            "en producción se usa --destino produccion, nunca 'local'."
        )
    return {
        "host": host,
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


def describir_destino(destino: str) -> str:
    """
    'usuario@host:puerto/servicio' del destino, SIN contraseña. Para que el
    operador vea contra qué base va a escribir antes de confirmar, en vez de
    fiarse de la etiqueta 'local'/'produccion'.
    """
    cfg = resolver_config(destino)
    return f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['service']}"


def abrir_conexion(destino: str):
    """
    Abre una conexión oracledb thin al destino indicado. Import perezoso de
    oracledb para que importar esta capa NO requiera el driver ni toque la red.
    """
    import oracledb  # import diferido a propósito

    cfg = resolver_config(destino)
    dsn = f"{cfg['host']}:{cfg['port']}/{cfg['service']}"
    return oracledb.connect(user=cfg["user"], password=cfg["password"], dsn=dsn)
