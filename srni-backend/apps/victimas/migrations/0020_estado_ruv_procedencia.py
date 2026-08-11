"""Procedencia del estado RUV, y limpieza del estado que nunca fue verificado.

El padrón se cargó uniendo `GIC_PERSONA` con `M_CARACT_TABLA_RA_PER` por
`CONS_PERONA`, que resultó ser un **contador de filas** (1, 2, 3…) y no un
identificador de persona. Medido el 11-ago-2026: la fecha de nacimiento coincide
en 4 de 34.612 casos (0,0 %) y el género acierta el 50,1 %, que es el azar.

Con `estado_ruv` pasó algo peor que quedar mal asignado: la consulta filtraba
`WHERE c.estado_ruv IN (...)`, así que el dato ajeno **se gastó eligiendo quién
entra al padrón** y las 5.926.004 filas salieron con `INCLUIDO` constante.

Ver `docs/oracle-legacy/join_caracterizacion_roto.md`.

**Esta migración solo AÑADE COLUMNAS, y es deliberado.** Limpiar los 5,9 M de
`estado_ruv` va aparte, en `0021`, porque cuesta caro y esta no: desde
PostgreSQL 11 añadir una columna con `DEFAULT` no reescribe la tabla —el valor se
guarda en el catálogo—, así que esto es instantáneo sobre 5,9 M de filas. El
único costo real es construir el índice de `estado_ruv_fuente`.

Y con solo esto, las 5.926.004 filas ya quedan marcadas `SIN_VERIFICAR`, que es
la mitad importante del arreglo: el sistema deja de poder afirmar el estado sin
decir de dónde salió.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('victimas', '0019_fuente_origen_universo_ruv'),
    ]

    operations = [
        migrations.AddField(
            model_name='victima',
            name='estado_ruv_fecha',
            field=models.DateField(blank=True, help_text='Fecha del corte del que proviene el estado RUV.', null=True),
        ),
        migrations.AddField(
            model_name='victima',
            name='estado_ruv_fuente',
            field=models.CharField(choices=[('UNIVERSO_RUV', 'Universo del RUV (snapshot mensual)'), ('LEGACY_CARACT', 'Caracterización del legado — no confiable'), ('MANUAL', 'Declarado en campo por el funcionario'), ('SIN_VERIFICAR', 'Sin verificar — nadie lo ha resuelto')], db_index=True, default='SIN_VERIFICAR', help_text='De dónde salió el estado RUV. Sin esto, "no lo sabemos" es indistinguible de "lo sabemos y está incluido".', max_length=15),
        ),
    ]
