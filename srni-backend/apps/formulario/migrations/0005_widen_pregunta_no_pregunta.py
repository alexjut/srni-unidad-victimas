from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formulario', '0004_delete_instrumentoversion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pregunta',
            name='no_pregunta',
            field=models.CharField(
                blank=True, db_index=True, max_length=40,
                help_text="Número en diagrama de flujo: A1, A2, B1, C1, J1... (columna 'No. PREGUNTA VARIABLE')",
            ),
        ),
    ]
