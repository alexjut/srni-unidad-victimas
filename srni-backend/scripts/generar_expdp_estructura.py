r"""
FASE 2 — Genera el export de ESTRUCTURA de RNIENTREVISTA y lo descarga (Opción A).

APROBADO por Javier en sesión (2026-07-15). ÚNICA operación de escritura autorizada:
un Data Pump METADATA_ONLY vía DBMS_DATAPUMP (corre sobre esta conexión oracledb,
sin binario expdp ni Oracle Client). Escribe rnient_estructura.dmp/.log en
DATA_PUMP_DIR del servidor y luego los DESCARGA por la propia conexión (BFILE->BLOB).

- Requiere --confirmar (sin él, DRY-RUN: solo muestra el plan, NO ejecuta).
- METADATA_ONLY: no exporta filas → dump pequeño, sin PII de datos.
- job_name NULL (auto) → la master table se auto-elimina al completar.

Uso (en tu terminal; pide solo la contraseña, oculta):
    cd D:/desarrollo/uv-oracle-writer/srni-backend
    $env:ORA_HOST='30.0.1.9'; $env:ORA_SERVICE='ENTREVISTARN'; $env:ORA_USER='RNIENTREVISTA'
    python scripts/generar_expdp_estructura.py --confirmar

Salida local: infra/oracle-local/dumps/rnient_estructura.dmp  (+ .log)
Requiere VPN. Rotar la clave al terminar.
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

try:
    import oracledb
except ImportError:
    print("ERROR: pip install oracledb")
    sys.exit(1)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DIRECTORY = "DATA_PUMP_DIR"
DUMP = "rnient_estructura.dmp"
LOG = "rnient_estructura.log"
SCHEMA = "RNIENTREVISTA"

# --- Bloque de export (DBMS_DATAPUMP, metadata only) ---
PLSQL_EXPORT = f"""
DECLARE
  h NUMBER;
  st VARCHAR2(30);
BEGIN
  h := DBMS_DATAPUMP.OPEN('EXPORT','SCHEMA',NULL,NULL);
  DBMS_DATAPUMP.ADD_FILE(h,'{DUMP}','{DIRECTORY}',NULL,
                         DBMS_DATAPUMP.KU$_FILE_TYPE_DUMP_FILE, 1);   -- reusefile=1
  DBMS_DATAPUMP.ADD_FILE(h,'{LOG}','{DIRECTORY}',NULL,
                         DBMS_DATAPUMP.KU$_FILE_TYPE_LOG_FILE);
  DBMS_DATAPUMP.METADATA_FILTER(h,'SCHEMA_EXPR','IN (''{SCHEMA}'')');
  -- Excluir objetos JAVA (clases de ejemplo de Oracle) que crashean el worker
  -- con ORA-00600 en DBMS_JAVA, y STATISTICS (innecesarias). Irrelevantes para
  -- los 5 bloques de lógica.
  DBMS_DATAPUMP.METADATA_FILTER(h,'EXCLUDE_PATH_EXPR',
                                'IN (''STATISTICS'',''JAVA_SOURCE'',''JAVA_CLASS'')');
  DBMS_DATAPUMP.DATA_FILTER(h,'INCLUDE_ROWS',0);                     -- METADATA_ONLY
  DBMS_DATAPUMP.START_JOB(h);
  DBMS_DATAPUMP.WAIT_FOR_JOB(h, st);
  :st := st;
END;
"""

# --- Lee un archivo del DIRECTORY como BLOB temporal (para descargar) ---
PLSQL_READ_FILE = f"""
DECLARE
  src BFILE := BFILENAME('{DIRECTORY}', :fn);
  dst BLOB;
BEGIN
  DBMS_LOB.CREATETEMPORARY(dst, TRUE);
  DBMS_LOB.FILEOPEN(src, DBMS_LOB.FILE_READONLY);
  DBMS_LOB.LOADFROMFILE(dst, src, DBMS_LOB.GETLENGTH(src));
  DBMS_LOB.FILECLOSE(src);
  :out := dst;
END;
"""


def cargar_credenciales(path: str) -> dict:
    """Lee un archivo KEY=VALUE (ORA_HOST/ORA_SERVICE/ORA_USER/ORA_PWD/ORA_PORT).

    El password NUNCA se imprime ni se expone en línea de comandos.
    """
    creds = {}
    p = Path(path)
    if not p.exists():
        print(f"ERROR: no existe el archivo de credenciales: {p}")
        sys.exit(1)
    for linea in p.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        creds[k.strip()] = v.strip().strip('"').strip("'")
    return creds


def descargar(cur, filename, destino: Path) -> int:
    out = cur.var(oracledb.DB_TYPE_BLOB)
    cur.execute(PLSQL_READ_FILE, fn=filename, out=out)
    lob = out.getvalue()
    data = lob.read() if lob is not None else b""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirmar", action="store_true",
                    help="Ejecuta el export real en prod. Sin él es DRY-RUN.")
    ap.add_argument("--cred-file",
                    help="Archivo KEY=VALUE con ORA_HOST/ORA_SERVICE/ORA_USER/ORA_PWD.")
    args = ap.parse_args()

    # Credenciales: archivo (si se da) tiene prioridad sobre variables de entorno.
    creds = cargar_credenciales(args.cred_file) if args.cred_file else {}

    def cred(k, default=None):
        return creds.get(k) or os.environ.get(k) or default

    host = cred("ORA_HOST", "30.0.1.9")
    port = int(cred("ORA_PORT", 1521))
    service = cred("ORA_SERVICE", "ENTREVISTARN")
    user = cred("ORA_USER", "RNIENTREVISTA")

    print("=" * 78)
    print(f"EXPORT ESTRUCTURA {SCHEMA} — {host}:{port}/{service} — user {user}")
    print(f"Plan: DBMS_DATAPUMP EXPORT SCHEMA={SCHEMA} METADATA_ONLY → {DIRECTORY}/{DUMP}")
    print("=" * 78)

    if not args.confirmar:
        print("\nDRY-RUN: falta --confirmar. NO se ejecuta nada.")
        print("Para ejecutar el export real (aprobado): agrega --confirmar")
        return

    password = cred("ORA_PWD") or getpass.getpass("Password (oculto): ").strip()
    if not password:
        print("ERROR: password vacía"); sys.exit(1)

    conn = oracledb.connect(user=user, password=password, host=host, port=port,
                            service_name=service)
    print(f"Conectado OK. Server version: {conn.version}")
    cur = conn.cursor()

    # 1. Export
    print(f"\n• Ejecutando DBMS_DATAPUMP (metadata only)… puede tardar decenas de segundos.")
    st = cur.var(str)
    try:
        cur.execute(PLSQL_EXPORT, st=st)
    except Exception as e:
        print(f"  ✗ ERROR en el export: {e}")
        conn.close(); sys.exit(1)
    estado = st.getvalue()
    print(f"  Estado del job: {estado}")

    # 2. Descargar dump + log por la conexión (BFILE→BLOB)
    base = Path(__file__).resolve().parents[2] / "infra" / "oracle-local" / "dumps"

    # Si el job no completó, el dump está INCOMPLETO: descargar SOLO el log para
    # diagnóstico y ABORTAR (no declarar éxito con un .dmp roto).
    if estado != "COMPLETED":
        print(f"\n  ✗ El job terminó en estado '{estado}' — el .dmp está incompleto.")
        try:
            descargar(cur, LOG, base / LOG)
            texto = (base / LOG).read_text(encoding="latin-1", errors="replace")
            print("\n── Log del export (diagnóstico) ──\n" +
                  "\n".join(texto.splitlines()[-20:]))
        except Exception as e:
            print(f"  (no se pudo descargar el log: {e})")
        cur.close(); conn.close()
        sys.exit(1)
    print(f"\n• Descargando {DUMP} vía SQL…")
    n_dmp = descargar(cur, DUMP, base / DUMP)
    print(f"  ✓ {base / DUMP}  ({n_dmp:,} bytes)")
    print(f"• Descargando {LOG} vía SQL…")
    try:
        n_log = descargar(cur, LOG, base / LOG)
        print(f"  ✓ {base / LOG}  ({n_log:,} bytes)")
        texto = (base / LOG).read_text(encoding="latin-1", errors="replace")
        cola = "\n".join(texto.splitlines()[-15:])
        print("\n── Últimas líneas del log del export ──\n" + cola)
    except Exception as e:
        print(f"  (no se pudo descargar el log: {e})")

    cur.close(); conn.close()
    print("\n" + "=" * 78)
    print(f"✓ Export de estructura descargado en: {base / DUMP}")
    print("  Siguiente: python scripts/import_estructura.py --dmp "
          f"infra/oracle-local/dumps/{DUMP} --confirmar")
    print("  Rotar la clave de RNIENTREVISTA.")
    print("=" * 78)


if __name__ == "__main__":
    main()
