"""
Carga el CATÁLOGO (no PII) de RNIENTREVISTA-prod al Oracle LOCAL de estructura.

Trae SOLO tablas de definición/catálogo por `SELECT` directo (solo lectura en prod,
CERO footprint: ni .dmp, ni job, ni archivo en el server) y las inserta en el Oracle
local (`srni-oracle-local`, estructura ya importada, tablas vacías). Con esto el
análisis de alineación (respuestas, escribibilidad, PRE_TIPOPREGUNTA, parentesco,
Cédula) corre en local sin depender de prod y sin tocar datos de personas.

NO incluye `GIC_N_RESPUESTASENCUESTA` (respuestas reales = transaccional/sensible).

Requisitos:
  - Oracle local arriba:  cd infra/oracle-local && docker compose --env-file .env up -d
  - Credenciales prod en: infra/oracle-local/.env.prod  (gitignored, NUNCA versionar)
      ORACLE_PROD_HOST/PORT/SERVICE/USER/PASSWORD
  - Credenciales local en: infra/oracle-local/.env  (ORACLE_LEGACY_*)

Uso:
  D:/desarrollo/unidad-victima/srni-backend/.venv/Scripts/python.exe \
    scripts/cargar_catalogo_local.py
"""
import pathlib
import oracledb

oracledb.defaults.fetch_lobs = False  # CLOB/BLOB como str/bytes para round-trip

RAIZ = pathlib.Path(__file__).resolve().parents[2]  # .../uv-oracle-writer
ENV_PROD = RAIZ / "infra" / "oracle-local" / ".env.prod"
ENV_LOCAL = RAIZ / "infra" / "oracle-local" / ".env"

# Orden de dependencias: padres primero (evita choque de FK al cargar).
TABLAS = [
    "GIC_INSTRUMENTO", "GIC_TIPOCARACTERIZACION", "GIC_TIPODOC", "GIC_TEMA",
    "GIC_N_PREGUNTAS", "GIC_N_RESPUESTAS", "GIC_N_INSTRUMENTOXPREG",
    "GIC_N_INSTRUMENTOXRESP",
]


def _load_env(path):
    env = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _try(cur, sql):
    try:
        cur.execute(sql)
        return True
    except Exception as ex:  # noqa: BLE001 — best-effort en DDL de setup
        return str(ex)[:70]


def main():
    pe = _load_env(ENV_PROD)
    le = _load_env(ENV_LOCAL)
    pw = pe.get("ORACLE_PROD_PASSWORD", "")
    if not pw or "PON_AQUI" in pw:
        raise SystemExit("Falta la clave real en infra/oracle-local/.env.prod")

    prod = oracledb.connect(
        user=pe["ORACLE_PROD_USER"], password=pw,
        dsn=f"{pe['ORACLE_PROD_HOST']}:{pe.get('ORACLE_PROD_PORT', '1521')}/{pe['ORACLE_PROD_SERVICE']}",
    )
    loc = oracledb.connect(
        user=le.get("ORACLE_LEGACY_USER", "RNIENTREVISTA"), password=le["ORACLE_LEGACY_PASSWORD"],
        dsn=f"localhost:{le.get('ORACLE_LEGACY_PORT', '1521')}/{le.get('ORACLE_LEGACY_SERVICE', 'FREEPDB1')}",
    )
    pc, lc = prod.cursor(), loc.cursor()

    # 1) Desactivar triggers (asignan PK) y FKs para preservar los ids reales.
    for t in TABLAS:
        _try(lc, f"ALTER TABLE {t} DISABLE ALL TRIGGERS")
    for t in TABLAS:
        lc.execute("SELECT constraint_name FROM user_constraints "
                   "WHERE table_name=:t AND constraint_type='R'", [t])
        for (cn,) in lc.fetchall():
            _try(lc, f'ALTER TABLE {t} DISABLE CONSTRAINT "{cn}"')
    loc.commit()

    # 2) Cargar tabla por tabla (solo lectura en prod).
    for t in TABLAS:
        pc.execute(f"SELECT * FROM {t}")
        cols = [d[0] for d in pc.description]
        rows = pc.fetchall()
        _try(lc, f"DELETE FROM {t}")
        if rows:
            ph = ",".join(f":{i + 1}" for i in range(len(cols)))
            lc.executemany(f'INSERT INTO {t} ({",".join(cols)}) VALUES ({ph})', rows)
        loc.commit()
        n = lc.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:28} prod={len(rows):>6}  local={n:>6}  {'OK' if n == len(rows) else '<<DIF'}")

    # 3) Reactivar triggers; FKs con NOVALIDATE (base local de prueba).
    for t in TABLAS:
        _try(lc, f"ALTER TABLE {t} ENABLE ALL TRIGGERS")
        lc.execute("SELECT constraint_name FROM user_constraints WHERE table_name=:t "
                   "AND constraint_type='R' AND status='DISABLED'", [t])
        for (cn,) in lc.fetchall():
            _try(lc, f'ALTER TABLE {t} ENABLE NOVALIDATE CONSTRAINT "{cn}"')
    loc.commit()
    prod.close()
    loc.close()
    print("LISTO: catálogo cargado en el Oracle local.")


if __name__ == "__main__":
    main()
