"""
El libro de las recaracterizaciones sobre ficha vigente.

─── Por qué ─────────────────────────────────────────────────────────────────
El 11-sep-2026 la operación pidió retirar el bloqueo por ficha vigente: quien fue
caracterizado hace menos de dos años podrá caracterizarse otra vez sin
autorización, sin radicado y sin soporte. La petición se atiende completa.

Lo que no hay razón para perder es el dato. Esta tabla lo guarda, escrita sola al
cerrar la encuesta. Con ella se puede responder cuántas recaracterizaciones se
hicieron sobre ficha vigente, quién las hizo y con cuánta anticipación — el
informe que control interno va a pedir, y que hoy no tendríamos.

─── Esta migración NO cambia el comportamiento de nada ──────────────────────
Crea la tabla y nada más. El bloqueo sigue activo: lo gobierna
`settings.VIGENCIA['BLOQUEO_ACTIVO']`, que nace en `True` y solo se apaga por
variable de entorno. Mientras esté encendido, la tabla existe vacía.

Es deliberado: desplegar no puede retirar por su cuenta un control del Manual de
Usuario §5.1.1. Retirarlo es un acto explícito, con fecha y responsable.

Tampoco se toca `ExcepcionVigencia`. Sus filas son la evidencia del régimen
anterior —permisos otorgados, con autorizante y radicado— y hay que poder seguir
distinguiéndolas de una recaracterización de rutina.
"""

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('encuestas', '0009_cerrar_excepciones_del_flujo_viejo'),
        ('hogares', '0007_alter_miembrohogar_estado_inclusion'),
        ('victimas', '0021_limpiar_estado_ruv_no_verificado'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecaracterizacionVigente',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('realizada_at', models.DateTimeField(help_text='Cuándo se cerró la caracterización.')),
                ('ruta', models.CharField(blank=True, choices=[('GENERAL', 'General — caracterización ordinaria'), ('ACCIONES_CONSTITUCIONALES', 'Acciones constitucionales'), ('MODIFICACION_NUCLEO', 'Modificación de núcleo familiar'), ('ESPECIAL', 'Ruta especial — población diferencial')], help_text='Ruta de entrevista elegida. Sin motivo escrito, es lo más cercano que hay a un porqué.', max_length=30)),
                ('fecha_ult_caracterizacion', models.DateField(blank=True, help_text='Fecha de la caracterización ANTERIOR, la que estaba vigente.', null=True)),
                ('vigente_hasta', models.DateField(blank=True, help_text='Hasta cuándo estaba vigente esa ficha.', null=True)),
                ('dias_restantes', models.IntegerField(blank=True, help_text='Días que le faltaban por vencer. Ya calculado, para poder ordenar por gravedad sin recalcular sobre millones de filas.', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('hogar', models.ForeignKey(blank=True, help_text='Permite ir del registro a la entrevista concreta.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recaracterizaciones_vigentes', to='hogares.hogar')),
                ('realizada_por', models.ForeignKey(help_text='El encuestador que hizo la caracterización.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recaracterizaciones_vigentes', to=settings.AUTH_USER_MODEL)),
                ('sesion', models.ForeignKey(help_text='La caracterización que se hizo sobre la ficha vigente.', on_delete=django.db.models.deletion.CASCADE, related_name='recaracterizaciones_vigentes', to='encuestas.sesionencuesta')),
                ('victima', models.ForeignKey(help_text='La persona que tenía ficha vigente.', on_delete=django.db.models.deletion.PROTECT, related_name='recaracterizaciones_vigentes', to='victimas.victima')),
            ],
            options={
                'verbose_name': 'Recaracterización sobre ficha vigente',
                'verbose_name_plural': 'Recaracterizaciones sobre ficha vigente',
                'ordering': ['-realizada_at'],
                'indexes': [models.Index(fields=['-realizada_at'], name='recar_vig_fecha_idx'), models.Index(fields=['realizada_por', '-realizada_at'], name='recar_vig_autor_idx'), models.Index(fields=['victima', '-realizada_at'], name='recar_vig_victima_idx'), models.Index(fields=['dias_restantes'], name='recar_vig_dias_idx')],
                'constraints': [models.UniqueConstraint(fields=('sesion', 'victima'), name='recar_vig_sesion_victima_uniq')],
            },
        ),
    ]
