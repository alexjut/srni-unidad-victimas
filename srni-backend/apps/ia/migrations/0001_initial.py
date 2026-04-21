import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('encuestas', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsentimientoIA',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('acepto', models.BooleanField(default=False)),
                ('firma_digital', models.CharField(blank=True, db_index=True, max_length=64)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('encuestador', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='consentimientos_ia',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('sesion_encuesta', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='consentimientos_ia',
                    to='encuestas.sesionencuesta',
                )),
            ],
            options={
                'verbose_name': 'Consentimiento IA',
                'verbose_name_plural': 'Consentimientos IA',
                'ordering': ['-creado_en'],
            },
        ),
        migrations.CreateModel(
            name='SesionIA',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('inicio', models.DateTimeField(auto_now_add=True)),
                ('fin', models.DateTimeField(blank=True, null=True)),
                ('total_llamadas', models.PositiveIntegerField(default=0)),
                ('transcripcion_hash', models.CharField(blank=True, max_length=64)),
                ('sesion_encuesta', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sesion_ia',
                    to='encuestas.sesionencuesta',
                )),
            ],
            options={
                'verbose_name': 'Sesión IA',
                'verbose_name_plural': 'Sesiones IA',
                'ordering': ['-inicio'],
            },
        ),
        migrations.AddIndex(
            model_name='consentimientoia',
            index=models.Index(fields=['sesion_encuesta', 'acepto'], name='ia_consent_sesion_acepto_idx'),
        ),
        migrations.AddIndex(
            model_name='consentimientoia',
            index=models.Index(fields=['encuestador', 'creado_en'], name='ia_consent_encuestador_idx'),
        ),
    ]
