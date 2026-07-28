"""
Carga GIC_MUNICIPIO / GIC_DEPARTAMENTO reales en la réplica LOCAL (Escalón 2).

Por qué hace falta: la réplica se construyó con la ESTRUCTURA real de RNIENTREVISTA
y con el catálogo de preguntas/respuestas, pero estas dos tablas quedaron vacías. Sin
ellas no se puede comprobar lo único que importa del paso RESPUESTA geográfico: que
el valor escrito en RXP_TEXTORESPUESTA **cruza** contra GIC_MUNICIPIO.ID_MUNI_DEPTO,
que es el join que hacen los reportes (SP_CONSTANCIA, body 3625-3626).

Fuente: `apps/sincronizacion/oracle/geografia_oracle.json`, volcado de producción
(catálogo puro, sin PII): 1.126 municipios y 33 departamentos.

Solo escribe en LOCAL: el DSN está clavado a localhost, igual que el resto de scripts
de `infra/oracle-local/`. Idempotente (borra e inserta el catálogo completo).
"""
import json
import os
import pathlib
import re

import oracledb

RAIZ = pathlib.Path(__file__).resolve().parents[2]
GEO = RAIZ / "srni-backend" / "apps" / "sincronizacion" / "oracle" / "geografia_oracle.json"
ENV = pathlib.Path(__file__).with_name(".env")


def _config():
    cfg = {}
    if ENV.exists():
        for linea in ENV.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*([A-Z_]+)\s*=\s*(.*)$", linea)
            if m:
                cfg[m.group(1)] = m.group(2).strip()
    cfg.update({k: v for k, v in os.environ.items() if k.startswith("ORACLE_")})
    return cfg


def main():
    cfg = _config()
    datos = json.loads(GEO.read_text(encoding="utf-8"))
    deptos = datos["departamentos"]
    munis = datos["municipios"]
    print(f"Origen: {GEO.name} — {len(deptos)} departamentos / {len(munis)} municipios")

    # localhost, siempre: este script no debe poder alcanzar producción.
    con = oracledb.connect(user=cfg["ORACLE_LEGACY_USER"], password=cfg["ORACLE_LEGACY_PASSWORD"],
                           dsn=f"localhost:{cfg.get('ORACLE_LEGACY_PORT', '1521')}/FREEPDB1")
    cur = con.cursor()

    cur.execute("DELETE FROM gic_municipio")
    cur.execute("DELETE FROM gic_departamento")
    cur.executemany("INSERT INTO gic_departamento (id_depto, nom_depto) VALUES (:1, :2)",
                    [(int(k), v) for k, v in deptos.items()])
    cur.executemany(
        "INSERT INTO gic_municipio (id_muni_depto, id_depto, id_municipio, nom_municipio) "
        "VALUES (:1, :2, :3, :4)",
        [(m["id_muni_depto"], m["id_depto"], m["id_municipio"], m["nombre"]) for m in munis])
    con.commit()

    cur.execute("SELECT COUNT(*) FROM gic_departamento")
    n_dep = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM gic_municipio")
    n_mun = cur.fetchone()[0]
    print(f"Cargado en la réplica local: {n_dep} departamentos / {n_mun} municipios")

    cur.execute("SELECT m.id_muni_depto, m.nom_municipio, d.nom_depto FROM gic_municipio m "
                "JOIN gic_departamento d ON d.id_depto = m.id_depto "
                "WHERE m.id_muni_depto IN (5001, 73026, 76109)")
    for fila in cur.fetchall():
        print("  muestra:", fila)
    con.close()


if __name__ == "__main__":
    main()
