"""Procedencia del estado RUV, y limpieza del estado que nunca fue verificado.

El padrón se cargó uniendo `GIC_PERSONA` con `M_CARACT_TABLA_RA_PER` por
`CONS_PERONA`, que resultó ser un **contador de filas** (1, 2, 3…) y no un
identificador de persona. Medido el 11-ago-2026: la fecha de nacimiento coincide
en 4 de 34.612 casos (0,0 %) y el género acierta el 50,1 %, que es el azar.

Con `estado_ruv` pasó algo peor que quedar mal asignado: la consulta filtraba
`WHERE c.estado_ruv IN (...)`, así que el dato ajeno **se gastó eligiendo quién
entra al padrón** y las 5.926.004 filas salieron con `INCLUIDO` constante.

Ver `docs/oracle-legacy/join_caracterizacion_roto.md`.
"""

from django.db import migrations, models


def marcar_estado_no_verificado(apps, schema_editor):
    """
    Las filas que heredaron `INCLUIDO` del join roto pasan a `NO_VERIFICADO`.

    **No se pierde información.** El valor actual es constante por construcción
    —5.926.004 `INCLUIDO` y 1 `NO_VERIFICADO`, medido en producción—, así que no
    distingue a nadie de nadie: no hay nada que un `INCLUIDO` diga hoy que no
    diga el de al lado.

    **No bloquea a nadie.** `describir_elegibilidad` (repository/base.py) solo
    corta con `EXCLUIDO`; el resto de la decisión la toma
    `habilitado_para_caracterizacion`, que es correcto por persona porque sale de
    un join local sin dblink.

    Lo que sí cambia: el sistema deja de **afirmar** que 5,9 M de personas están
    incluidas en el RUV cuando nadie lo verificó. Eso viajaba al padrón offline
    como `FLAG_EN_RUV` y a los reportes con enfoque diferencial.
    """
    Victima = apps.get_model('victimas', 'Victima')
    Victima.objects.filter(
        estado_ruv='INCLUIDO', estado_ruv_fuente='SIN_VERIFICAR',
    ).update(estado_ruv='NO_VERIFICADO')


def revertir(apps, schema_editor):
    """
    Vuelve a `INCLUIDO` lo que esta migración marcó.

    Es reversible sin pérdida justamente porque el valor original era constante:
    restituirlo no requiere haberlo guardado en ningún lado. Los campos nuevos
    los quita el `AddField` al revertirse.
    """
    Victima = apps.get_model('victimas', 'Victima')
    Victima.objects.filter(
        estado_ruv='NO_VERIFICADO', estado_ruv_fuente='SIN_VERIFICAR',
    ).update(estado_ruv='INCLUIDO')


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
        # Va DESPUÉS de los AddField: el filtro usa `estado_ruv_fuente`, que hasta
        # este punto no existe.
        migrations.RunPython(marcar_estado_no_verificado, revertir),
    ]
