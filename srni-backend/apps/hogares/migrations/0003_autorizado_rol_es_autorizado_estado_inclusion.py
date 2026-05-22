# Generated manually — Sprint 12: Flujo Autorizado + Modelo Miembro
# BD está vacía — migración directa sin lógica de conversión de datos legados.

import django.db.models.deletion
import django.db.models.functions
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hogares', '0002_hogar_codigo_hogar_miembrohogar_fuente_origen_and_more'),
        ('victimas', '0002_add_catalogo_hecho_campos_caracterizacion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. Hogar: eliminar índice antiguo sobre jefe_hogar ───────────────
        # Debe ir ANTES del RenameField para que SQLite reconstruya la tabla sin él.
        migrations.RemoveIndex(
            model_name='hogar',
            name='hogares_hog_jefe_ho_cfe936_idx',
        ),

        # ── 2. Hogar: renombrar jefe_hogar → autorizado ──────────────────────
        migrations.RenameField(
            model_name='hogar',
            old_name='jefe_hogar',
            new_name='autorizado',
        ),
        migrations.AlterField(
            model_name='hogar',
            name='autorizado',
            field=models.ForeignKey(
                help_text='Víctima titular que autoriza y realiza la entrevista de caracterización.',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='hogares_como_autorizado',
                to='victimas.victima',
            ),
        ),

        # ── 3. Hogar: añadir índice nuevo sobre autorizado ───────────────────
        migrations.AddIndex(
            model_name='hogar',
            index=models.Index(fields=['autorizado', 'estado'], name='hogares_hog_autor_estado_idx'),
        ),

        # ── 4. MiembroHogar: eliminar índice antiguo sobre tipo_inclusion ───
        # Debe ir ANTES del RemoveField para evitar error SQLite "no such column".
        migrations.RemoveIndex(
            model_name='miembrohogar',
            name='hogares_mie_tipo_in_a9cdb5_idx',
        ),

        # ── 5. MiembroHogar: eliminar tipo_inclusion (3 valores) ────────────
        migrations.RemoveField(
            model_name='miembrohogar',
            name='tipo_inclusion',
        ),

        # ── 5. MiembroHogar: quitar JEFE de parentesco (blank=True ahora) ───
        migrations.AlterField(
            model_name='miembrohogar',
            name='parentesco',
            field=models.CharField(
                blank=True,
                choices=[
                    ('CONYUGE', 'Cónyuge / compañero/a'),
                    ('HIJO_A', 'Hijo/a'),
                    ('YERNO_NUERA', 'Yerno / nuera'),
                    ('NIETO_A', 'Nieto/a'),
                    ('PADRE_MADRE', 'Padre / madre'),
                    ('HERMANO_A', 'Hermano/a'),
                    ('OTRO_PARIENTE', 'Otro pariente'),
                    ('NO_PARIENTE', 'Sin parentesco'),
                ],
                default='',
                help_text='Relación familiar con el autorizado. Vacío para el propio autorizado.',
                max_length=20,
            ),
        ),

        # ── 5. MiembroHogar: nuevo campo rol ────────────────────────────────
        migrations.AddField(
            model_name='miembrohogar',
            name='rol',
            field=models.CharField(
                choices=[
                    ('MIEMBRO', 'Miembro del hogar'),
                    ('TUTOR', 'Tutor — responsable legal de menor'),
                    ('CUIDADOR_PERMANENTE', 'Cuidador permanente — responsable de adulto dependiente'),
                ],
                default='MIEMBRO',
                help_text='Función del integrante en el hogar.',
                max_length=20,
            ),
        ),

        # ── 6. MiembroHogar: nuevo campo es_autorizado ───────────────────────
        migrations.AddField(
            model_name='miembrohogar',
            name='es_autorizado',
            field=models.BooleanField(
                default=False,
                help_text='True para el titular que autoriza y realiza la entrevista. Solo uno por hogar.',
            ),
        ),

        # ── 7. MiembroHogar: nuevo campo estado_inclusion ───────────────────
        migrations.AddField(
            model_name='miembrohogar',
            name='estado_inclusion',
            field=models.CharField(
                choices=[
                    ('INCLUIDO', 'Incluido — víctima registrada en el RUV'),
                    ('NO_INCLUIDO', 'No incluido — no registrado en el RUV'),
                ],
                default='NO_INCLUIDO',
                help_text='Indica si la persona está registrada como víctima en el RUV.',
                max_length=15,
            ),
        ),

        # ── 8. MiembroHogar: actualizar related_name membresías → membresias ─
        migrations.AlterField(
            model_name='miembrohogar',
            name='victima',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='membresias_hogar',
                to='victimas.victima',
            ),
        ),

        # ── 9. MiembroHogar: actualizar ordering e índices ───────────────────
        migrations.AlterModelOptions(
            name='miembrohogar',
            options={
                'ordering': ['-es_autorizado', 'rol', 'created_at'],
                'verbose_name': 'Miembro del Hogar',
                'verbose_name_plural': 'Miembros del Hogar',
            },
        ),
        migrations.AddIndex(
            model_name='miembrohogar',
            index=models.Index(fields=['hogar', 'es_autorizado'], name='hogares_mie_hogar_autor_idx'),
        ),
        migrations.AddIndex(
            model_name='miembrohogar',
            index=models.Index(fields=['hogar', 'rol'], name='hogares_mie_hogar_rol_idx'),
        ),
        migrations.AddIndex(
            model_name='miembrohogar',
            index=models.Index(fields=['estado_inclusion'], name='hogares_mie_est_incl_idx'),
        ),

        # ── 10. MiembroHogar: constraint único autorizado por hogar ──────────
        migrations.AddConstraint(
            model_name='miembrohogar',
            constraint=models.UniqueConstraint(
                condition=models.Q(es_autorizado=True),
                fields=['hogar'],
                name='unique_autorizado_por_hogar',
            ),
        ),
    ]
