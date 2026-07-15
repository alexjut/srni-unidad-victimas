#!/usr/bin/env python
"""
Importa un export de ESTRUCTURA (metadata) de RNIENTREVISTA al Oracle LOCAL.

Diseñado para el contenedor `srni-oracle-local` (infra/oracle-local/docker-compose.yml,
imagen gvenzl/oracle-free). NO toca ningún servidor real.

MODO SEGURO — DRY-RUN por defecto:
  - Sin `--dmp <archivo existente>` o sin `--confirmar`, NO ejecuta impdp:
    solo valida el contenedor e imprime el plan exacto (comandos que correría).
  - Con `--dmp ruta.dmp --confirmar` ejecuta la importación real (metadata only).

Pasos que ejecuta (con --confirmar):
  1. Verifica que el contenedor esté corriendo y responда SELECT 1 FROM DUAL.
  2. Copia el .dmp a /opt/oracle/dumps dentro del contenedor (si no está ya ahí).
  3. Crea la DIRECTORY DUMP_DIR y otorga privilegios de import al esquema.
  4. Corre impdp con CONTENT=METADATA_ONLY (estructura, sin filas).
  5. Reporta objetos INVALID e intenta recompilar.

Uso:
  # Dry-run (mecanismo listo, sin archivo):
  python scripts/import_estructura.py

  # Import real cuando llegue el .dmp:
  python scripts/import_estructura.py --dmp infra/oracle-local/dumps/rnient_estructura.dmp --confirmar
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# La consola de Windows (cp1252) no puede imprimir ✓/✗/… → forzar UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CONTAINER = os.environ.get("ORACLE_LOCAL_CONTAINER", "srni-oracle-local")
SCHEMA = os.environ.get("ORACLE_LEGACY_USER", "RNIENTREVISTA")
SERVICE = os.environ.get("ORACLE_LEGACY_SERVICE", "FREEPDB1")
SYS_PASS = os.environ.get("ORACLE_SYS_PASSWORD", "")
SCHEMA_PASS = os.environ.get("ORACLE_LEGACY_PASSWORD", "")
# Ruta compartida host↔contenedor (montada en docker-compose como ./dumps).
DUMPS_DIR_CONTENEDOR = "/opt/oracle/dumps"

# Privilegios mínimos para importar el esquema completo (tablas, secuencias,
# triggers, vistas, packages) — se otorgan como SYSTEM antes del impdp.
GRANTS = (
    "GRANT CONNECT, RESOURCE, CREATE VIEW, CREATE PROCEDURE, CREATE TRIGGER, "
    "CREATE SEQUENCE, CREATE SYNONYM, CREATE TABLE, CREATE TYPE, "
    "UNLIMITED TABLESPACE TO {schema}"
).format(schema=SCHEMA)


def run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, **kw)


def contenedor_corriendo() -> bool:
    r = subprocess.run(
        ["docker", "ps", "--filter", f"name=^{CONTAINER}$", "--filter",
         "status=running", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    return CONTAINER in r.stdout


def sqlplus(sql: str, user="system"):
    """Ejecuta SQL dentro del contenedor vía sqlplus."""
    pwd = SYS_PASS if user == "system" else SCHEMA_PASS
    conn = f"{user}/{pwd}@localhost:1521/{SERVICE}"
    script = f"SET HEADING OFF FEEDBACK OFF;\n{sql}\nEXIT;\n"
    return run(
        ["docker", "exec", "-i", CONTAINER, "sqlplus", "-S", conn],
        input=script, text=True, capture_output=True,
    )


def verificar_conexion() -> bool:
    print("• Verificando contenedor y conexión…")
    if not contenedor_corriendo():
        print(f"  ✗ El contenedor '{CONTAINER}' no está corriendo. "
              f"Levántalo con: cd infra/oracle-local && docker compose --env-file .env up -d")
        return False
    if not SYS_PASS:
        print("  ✗ Falta ORACLE_SYS_PASSWORD en el entorno.")
        return False
    r = sqlplus("SELECT 'PONG' FROM DUAL;")
    if "PONG" in (r.stdout or ""):
        print("  ✓ Oracle local responde (SELECT ... FROM DUAL).")
        return True
    print(f"  ✗ Sin respuesta válida:\n{r.stdout}\n{r.stderr}")
    return False


def plan_impdp(dumpfile_en_contenedor: str) -> list:
    logfile = "import_estructura.log"
    return [
        "docker", "exec", CONTAINER, "impdp",
        f"system/{SYS_PASS}@localhost:1521/{SERVICE}",
        f"DIRECTORY=DUMP_DIR",
        f"DUMPFILE={dumpfile_en_contenedor}",
        f"LOGFILE={logfile}",
        f"SCHEMAS={SCHEMA}",
        "CONTENT=METADATA_ONLY",          # solo estructura (redundante pero explícito)
        "TABLE_EXISTS_ACTION=SKIP",
        "EXCLUDE=STATISTICS",
        # Ignora tablespaces/almacenamiento del origen → todo al tablespace del user.
        "TRANSFORM=SEGMENT_ATTRIBUTES:N",
    ]


def main():
    ap = argparse.ArgumentParser(description="Import de estructura RNIENTREVISTA al Oracle local")
    ap.add_argument("--dmp", help="Ruta al archivo .dmp (en el host)")
    ap.add_argument("--confirmar", action="store_true",
                    help="Ejecuta la importación real. Sin este flag es DRY-RUN.")
    args = ap.parse_args()

    if not verificar_conexion():
        sys.exit(1)

    dmp = Path(args.dmp).resolve() if args.dmp else None
    existe = dmp is not None and dmp.exists()
    dumpfile_nombre = dmp.name if dmp else "rnient_estructura.dmp"

    if not existe:
        print(f"\n• DRY-RUN: no hay .dmp válido"
              f"{'' if dmp is None else f' (no existe: {dmp})'}. No se ejecuta nada.")
        print("  Cuando llegue el archivo, colócalo en infra/oracle-local/dumps/ y corre:")
        print(f"    python scripts/import_estructura.py --dmp infra/oracle-local/dumps/{dumpfile_nombre} --confirmar")
        print("\n  Comando impdp que se ejecutaría (plan):")
        print("    " + " ".join(plan_impdp(dumpfile_nombre)).replace(SYS_PASS or "***", "***"))
        return

    if not args.confirmar:
        print(f"\n• DRY-RUN: {dmp} existe pero falta --confirmar. No se ejecuta impdp.")
        print("  Plan:\n    " + " ".join(plan_impdp(dumpfile_nombre)).replace(SYS_PASS or "***", "***"))
        return

    # --- Importación real ---
    print(f"\n• Importando estructura desde {dmp} …")

    # 1. Asegurar que el .dmp esté en la carpeta compartida (montada en el contenedor).
    dumps_host = Path(__file__).resolve().parents[2] / "infra" / "oracle-local" / "dumps"
    dumps_host.mkdir(parents=True, exist_ok=True)
    destino = dumps_host / dmp.name
    if dmp != destino:
        shutil.copy2(dmp, destino)
        print(f"  ✓ Copiado a {destino} (visible como {DUMPS_DIR_CONTENEDOR} en el contenedor).")

    # 2. Crear DIRECTORY y otorgar privilegios (como SYSTEM).
    print("• Creando DIRECTORY DUMP_DIR y otorgando privilegios…")
    sqlplus(f"CREATE OR REPLACE DIRECTORY DUMP_DIR AS '{DUMPS_DIR_CONTENEDOR}';")
    sqlplus(f"GRANT READ, WRITE ON DIRECTORY DUMP_DIR TO SYSTEM, {SCHEMA};")
    sqlplus(GRANTS + ";")

    # 3. impdp.
    print("• Ejecutando impdp (metadata only)…")
    r = run(plan_impdp(dmp.name), text=True)
    print(f"  impdp exit code: {r.returncode} (errores de objetos con dependencias externas son esperables)")

    # 4. Reportar INVALID e intentar recompilar.
    print("• Objetos INVALID tras el import:")
    inv = sqlplus(
        f"SELECT object_type||' '||object_name FROM all_objects "
        f"WHERE owner='{SCHEMA}' AND status='INVALID' ORDER BY object_type, object_name;"
    )
    print(inv.stdout or "  (ninguno)")
    print("• Intentando recompilar el esquema (UTL_RECOMP)…")
    sqlplus(f"BEGIN SYS.UTL_RECOMP.RECOMP_SERIAL('{SCHEMA}'); END;")
    print("\n✓ Import finalizado. Revisa docs/oracle-legacy/oracle-local-setup.md "
          "para la guía de objetos INVALID críticos vs. ignorables.")


if __name__ == "__main__":
    main()
