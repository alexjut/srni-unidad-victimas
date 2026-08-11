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
LOTE = 200_000

#: Cada cuántos lotes se aspira. **No es cada lote, y eso importa.**
#:
#: La primera versión hacía `VACUUM` tras cada lote de 50.000 y se probó contra
#: producción: 150.000 filas en 12 minutos, o sea ~8 HORAS para las 5,9 M. La
#: causa es que `VACUUM victimas_victima` recorre los 9,2 GB de tabla ENTEROS
#: cada vez; con 119 lotes eso es más de un terabyte de lectura para mover unas
#: columnas.
#:
#: Aspirando cada 5 lotes de 200.000 —cada millón de filas— el bloat máximo entre
#: pasadas es ~1,5 GB (1/5,9 de los 9,2 GB), que cabe de sobra, y las pasadas de
#: `VACUUM` bajan de 119 a 6.
VACUUM_CADA = 5


def _mover(apps, schema_editor, desde, hacia):
    """
    Mueve `estado_ruv` de un valor a otro, por lotes, aspirando cada tanto.

    **Es retomable.** Si se corta a mitad —se canceló la consulta, se cayó la
    VPN— basta con volver a lanzar la migración: el filtro solo toma las que aún
    no se movieron. Probado en producción el 11-ago, donde se cortó con 200.001
    filas ya migradas y el estado quedó consistente.
    """
    Victima = apps.get_model('victimas', 'Victima')
    conn = schema_editor.connection

    def aspirar():
        # VACUUM no puede correr dentro de una transacción. En SQLite (tests) no
        # aplica igual, así que solo en Postgres.
        if conn.vendor != 'postgresql':
            return
        estaba = conn.get_autocommit()
        conn.set_autocommit(True)
        try:
            with conn.cursor() as cur:
                cur.execute('VACUUM victimas_victima')
        finally:
            conn.set_autocommit(estaba)

    total = 0
    lotes = 0
    while True:
        # `pk__in` sobre un subconjunto acotado: un UPDATE sobre el filtro entero
        # tomaría los 9,2 GB en una sola transacción, que es justo lo que se
        # quiere evitar.
        ids = list(
            Victima.objects.filter(
                estado_ruv=desde, estado_ruv_fuente='SIN_VERIFICAR',
            ).values_list('pk', flat=True)[:LOTE]
        )
        if not ids:
            break

        Victima.objects.filter(pk__in=ids).update(estado_ruv=hacia)
        total += len(ids)
        lotes += 1

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
