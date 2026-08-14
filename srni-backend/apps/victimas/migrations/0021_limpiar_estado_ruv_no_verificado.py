"""Los 5,9 M de `INCLUIDO` que nadie verificó pasan a `NO_VERIFICADO`.

Va SEPARADA de la 0020 —que solo añade columnas y es instantánea— porque esta
cuesta caro y hay que elegir cuándo pagarla.

──────────────────────────────────────────────────────────────────────────────
🔴 LO QUE CUESTA, MEDIDO ANTES DE ESCRIBIRLA (11-ago-2026, producción)
──────────────────────────────────────────────────────────────────────────────
    victimas_victima   15 GB   (9,2 GB tabla + 5,9 GB índices)
    base completa      30 GB
    disco libre        16 GB

Un `UPDATE` no modifica la fila: escribe una versión nueva y marca la vieja como
muerta. Tocar las 5.926.005 de una vez reescribe los 9,2 GB de tabla más los
índices que incluyen `estado_ruv` (hay tres), o sea **12-15 GB de bloat contra
16 GB libres**. Si Postgres llena ese disco se detiene, y no solo para SICAV: el
servidor es compartido con `sidi-*`, `catalogo-si-*` y `uariv-auth-*`.

Por eso va por LOTES con `VACUUM` cada tanto, y por eso conviene correrla
**después** de trasladar la base a `/datos` (239 GB libres); ver
`docs/infraestructura/runbook_traslado_bd_a_datos.md`.

──────────────────────────────────────────────────────────────────────────────
POR QUÉ ACTUALIZA POR `ctid` Y NO POR CLAVE PRIMARIA
──────────────────────────────────────────────────────────────────────────────
La primera versión traía los ids del lote a Python y los devolvía en un
`WHERE id IN (...)`. Se corrió así en producción el 11-ago y avanzaba a **18
minutos por lote de 200.000** —5,8 horas para lo que faltaba—, con el backend
clavado en `wait_event = IO DataFileRead`. Los planes explican por qué:

    por id (UUID)   cost 1.358.918   Nested Loop → Index Scan on ..._pkey
    por ctid        cost    65.517   Nested Loop → Tid Scan

Localizar las filas cuesta igual en los dos (`Seq Scan`, 62.210: son 3,7 M de
5,9 M, demasiadas para que valga un índice). Toda la diferencia está en cómo se
aplica el `UPDATE`: por clave primaria son 200.000 búsquedas ALEATORIAS en el
índice de UUID más otras tantas lecturas del heap; el `ctid` ya es la posición
física de la fila, así que el `Tid Scan` va directo a la página. 20× más barato
**en el plan** —ojo con esa palabra, ver abajo—, y además el lote entero se
resuelve dentro de Postgres, sin traer 200.000 UUID a Python para reenviarlos
como 7 MB de SQL.

Un UUID aleatorio como clave primaria es cómodo para todo lo demás y muy caro
justo aquí: no tiene localidad, así que recorrerlo en volumen es puro salto de
disco.

🔴 **Y sin embargo NO fue más rápido. Medido de punta a punta:**

    por id (UUID)   10.870 filas/min   (2.000.000 en 3h04)
    por ctid        10.325 filas/min   (3.726.004 en 6h01, 8 lotes, 12-ago 05:04)

Un 5% por debajo, o sea lo mismo dentro del ruido. **El costo de un plan no
incluye lo que cuesta escribir** —ni el heap, ni el WAL, ni las entradas de
índice—, y ahí estaba el cuello: la tabla tiene **26 índices (5,9 GB)** y uno de
los indexados es `estado_ruv`, así que ninguna de estas filas se puede
actualizar en modo HOT y cada una inserta una entrada en los 26. Son ~97
millones de inserciones de índice que no evita ningún `WHERE`. Medido en vivo
durante la corrida: **260 MB de WAL por minuto**, el backend en `DataFileRead`.

El `ctid` quita el costo de BUSCAR, que resultó ser la mitad que no dolía; el
piso lo pone MANTENER los índices. Se deja igual porque el código es mejor —el
lote se resuelve dentro de Postgres, sin mandar 7 MB de UUID por la red— pero
**que nadie espere velocidad de este cambio**: para eso hay que tocar los
índices, no la consulta.

Ahí hay una deuda aparte que conviene mirar con calma y no en medio de una
migración: buena parte de esos 26 son de baja cardinalidad sobre 5,9 M filas
(`genero`, `pertenencia_etnica`, `estado_valoracion`, `discapacidad`,
`fuente_origen`), y cada uno de los `varchar` arrastra además su gemelo `_like`.
Se pagan enteros en cada escritura.

⚠️ **Aplicarla acotando la migración**, no con un `migrate` a secas:

    python manage.py migrate victimas 0021

Un `migrate victimas` arrastra todo lo pendiente. El 11-ago se lanzó así por
error y esta migración empezó a correr sin querer; se canceló con
`pg_cancel_backend` y el estado quedó consistente —200.001 filas ya movidas—
porque el diseño es retomable. Salió barato, pero conviene no repetirlo.

──────────────────────────────────────────────────────────────────────────────
POR QUÉ ES SEGURA EN CUANTO A DATOS
──────────────────────────────────────────────────────────────────────────────
**No se pierde información.** El valor es constante por construcción —5.926.004
`INCLUIDO` y 1 `NO_VERIFICADO`, medido—: no hay nada que un `INCLUIDO` diga hoy
que no diga el de al lado. Por eso también es reversible sin haber guardado nada.

**No bloquea a nadie.** `describir_elegibilidad` (repository/base.py) solo corta
con `EXCLUIDO`; el resto lo decide `habilitado_para_caracterizacion`, que es
correcto por persona porque sale de un join local sin dblink.

Lo que sí cambia: el sistema deja de **afirmar** que 5,9 M de personas están
incluidas en el RUV cuando nadie lo verificó. Eso viajaba al padrón offline como
`FLAG_EN_RUV` y a los reportes con enfoque diferencial.
"""

from django.db import migrations

#: Filas por lote. Cada `UPDATE` es una transacción corta, importante en una base
#: que otros están usando.
#:
#: Subió de 200.000 a 500.000 al pasar a `ctid`: lo caro dejó de ser aplicar el
#: `UPDATE` y pasó a ser el `Seq Scan` que busca las filas —recorre hasta juntar
#: `LOTE` coincidencias—, así que menos lotes es menos veces recorrida la tabla.
LOTE = 500_000

#: Cada cuántos lotes se aspira. **No es cada lote, y eso importa.**
#:
#: La primera versión hacía `VACUUM` tras cada lote de 50.000 y se probó contra
#: producción: 150.000 filas en 12 minutos, o sea ~8 HORAS para las 5,9 M. La
#: causa es que `VACUUM victimas_victima` recorre los 9,2 GB de tabla ENTEROS
#: cada vez; con 119 lotes eso es más de un terabyte de lectura para mover unas
#: columnas.
#:
#: Aspirando cada 3 lotes de 500.000 —cada millón y medio de filas— el bloat
#: máximo entre pasadas es ~2,3 GB (1,5/5,9 de los 9,2 GB), que cabe de sobra con
#: `/datos`, y las pasadas de `VACUUM` bajan de 119 a 4.
VACUUM_CADA = 3


def _mover(apps, schema_editor, desde, hacia):
    """
    Mueve `estado_ruv` de un valor a otro, por lotes, aspirando cada tanto.

    **Es retomable.** Si se corta a mitad —se canceló la consulta, se cayó la
    VPN— basta con volver a lanzar la migración: el filtro solo toma las que aún
    no se movieron. Probado dos veces en producción el 11-ago: se cortó con
    200.001 filas migradas y otra vez con 2.200.001 —esta segunda a propósito,
    para reemplazar el recorrido por clave primaria por el de `ctid`—, y las dos
    veces el estado quedó consistente y la siguiente corrida siguió de largo.
    """
    Victima = apps.get_model('victimas', 'Victima')
    conn = schema_editor.connection
    tabla = Victima._meta.db_table

    def aspirar():
        # VACUUM no puede correr dentro de una transacción. En SQLite (tests) no
        # aplica igual, así que solo en Postgres.
        if conn.vendor != 'postgresql':
            return
        estaba = conn.get_autocommit()
        conn.set_autocommit(True)
        try:
            with conn.cursor() as cur:
                cur.execute(f'VACUUM {tabla}')
        finally:
            conn.set_autocommit(estaba)

    if conn.vendor != 'postgresql':
        # SQLite (tests): no hay `ctid` ni razón para lotear un volumen de juguete.
        return Victima.objects.filter(
            estado_ruv=desde, estado_ruv_fuente='SIN_VERIFICAR',
        ).update(estado_ruv=hacia)

    tabla = Victima._meta.db_table
    # El `LIMIT` acota el lote sin traerlo a Python: el subselect y el `UPDATE`
    # se resuelven dentro de Postgres, y el `ctid` de cada fila lleva al
    # `Tid Scan` directo a su página. Un UPDATE sobre el filtro entero tomaría
    # los 9,2 GB en una sola transacción, que es justo lo que se quiere evitar.
    sql = (
        f'UPDATE {tabla} SET estado_ruv = %s WHERE ctid IN ('
        f' SELECT ctid FROM {tabla}'
        f" WHERE estado_ruv = %s AND estado_ruv_fuente = 'SIN_VERIFICAR'"
        f' LIMIT %s)'
    )

    total = 0
    lotes = 0
    while True:
        with conn.cursor() as cur:
            cur.execute(sql, [hacia, desde, LOTE])
            movidas = cur.rowcount
        if not movidas:
            break

        total += movidas
        lotes += 1
        # Va al log del servidor: la migración corre desatendida y sin esto no
        # hay forma de saber si avanza o si está clavada esperando disco.
        print(f'  lote {lotes}: {movidas:,} filas ({total:,} en total)', flush=True)

        if lotes % VACUUM_CADA == 0:
            aspirar()

    aspirar()          # una última, para devolver el espacio del tramo final
    return total


def marcar_no_verificado(apps, schema_editor):
    _mover(apps, schema_editor, 'INCLUIDO', 'NO_VERIFICADO')


def revertir(apps, schema_editor):
    _mover(apps, schema_editor, 'NO_VERIFICADO', 'INCLUIDO')


class Migration(migrations.Migration):

    # `atomic = False` es obligatorio: `VACUUM` no puede ejecutarse dentro de una
    # transacción, y además envolver 5,9 M de filas en una sola sería exactamente
    # el problema que esta migración evita.
    atomic = False

    dependencies = [
        ('victimas', '0020_estado_ruv_procedencia'),
    ]

    operations = [
        migrations.RunPython(marcar_no_verificado, revertir),
    ]
