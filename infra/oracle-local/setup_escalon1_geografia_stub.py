"""
Setup de escritura del Escalón 1 en la réplica LOCAL (Fase A3).

Hace resolver `rni_mi_pru.AP_GEOGRAFIA@DBL_RNIENTREVISTA` para que el paquete
GIC_N_CARACTERIZACION compile a VALID y sus procedures (cascada territorial +
SP_SET_RESPUESTAS_DE_ENCUESTA) sean invocables. Es un **stub loopback**: NO toca
el cuerpo del paquete (queda idéntico a prod), solo crea el destino local del dblink
—una tabla AP_GEOGRAFIA vacía en un esquema RNI_MI_PRU— y un dblink público que
apunta de vuelta al propio FREEPDB1.

Por qué el paquete estaba INVALID (diagnóstico 2026-07-24): el dblink real
`DBL_RNIENTREVISTA` no existe en la réplica; sin él la referencia a AP_GEOGRAFIA no
resuelve y TODO el paquete queda inválido → invocar cualquiera de sus procedures
(incluido FN_GET_CODIGOENCUESTA que usa GIC_INSERT_HOGAR1) disparaba un recompile
que colgaba/fallaba, y su WHEN OTHERS se tragaba el error. Una sola causa afectaba
HOGAR, TERRITORIO y RESPUESTA.

Uso (con las variables de infra/oracle-local/.env exportadas):
    python infra/oracle-local/setup_escalon1_geografia_stub.py

Requiere SYS (ORACLE_SYS_PASSWORD). Idempotente. Réplica de PRUEBA, sin PII.
"""
import os
import oracledb

STUB_PWD = os.environ.get("ORACLE_STUB_GEO_PASSWORD", "StubGeo2026")


def main():
    con = oracledb.connect(user="sys", password=os.environ["ORACLE_SYS_PASSWORD"],
                           dsn="localhost:1521/FREEPDB1", mode=oracledb.SYSDBA)
    cur = con.cursor()

    def run(sql, ignore=()):
        try:
            cur.execute(sql)
            print("  OK  :", sql.strip().split("\n")[0][:70])
        except oracledb.DatabaseError as e:
            code = e.args[0].code
            if code in ignore:
                print(f"  skip: ORA-{code:05d} (esperado)")
            else:
                print(f"  ERR : ORA-{code} {str(e).splitlines()[0][:80]}")

    # 1) esquema stub + tabla AP_GEOGRAFIA vacía (columnas usadas: ID, NOMBRE, NIVEL)
    run(f"CREATE USER RNI_MI_PRU IDENTIFIED BY {STUB_PWD}", ignore=(1920,))
    run("GRANT CREATE SESSION TO RNI_MI_PRU")
    run("ALTER USER RNI_MI_PRU QUOTA UNLIMITED ON USERS")
    run("CREATE TABLE RNI_MI_PRU.AP_GEOGRAFIA (ID NUMBER, NOMBRE VARCHAR2(400), "
        "NIVEL NUMBER, PADREID NUMBER)", ignore=(955,))
    run("GRANT SELECT ON RNI_MI_PRU.AP_GEOGRAFIA TO PUBLIC")

    # 2) dblink loopback público (el paquete lo referencia como @DBL_RNIENTREVISTA)
    run("DROP PUBLIC DATABASE LINK DBL_RNIENTREVISTA", ignore=(2024,))
    run(f"CREATE PUBLIC DATABASE LINK DBL_RNIENTREVISTA CONNECT TO RNI_MI_PRU "
        f"IDENTIFIED BY {STUB_PWD} USING 'localhost:1521/FREEPDB1'")

    # 3) recompilar → VALID
    run("ALTER PACKAGE RNIENTREVISTA.GIC_N_CARACTERIZACION COMPILE")
    run("ALTER PACKAGE RNIENTREVISTA.GIC_N_CARACTERIZACION COMPILE BODY")

    cur.execute("SELECT object_type,status FROM all_objects WHERE owner='RNIENTREVISTA' "
                "AND object_name='GIC_N_CARACTERIZACION' ORDER BY object_type")
    for tipo, estado in cur.fetchall():
        print(f"  {tipo} = {estado}")
    con.close()


if __name__ == "__main__":
    main()
