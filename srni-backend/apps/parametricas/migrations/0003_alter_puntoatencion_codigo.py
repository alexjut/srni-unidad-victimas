from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parametricas", "0002_alter_direccionterritorial_codigo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="puntoatencion",
            name="codigo",
            field=models.CharField(db_index=True, max_length=40, unique=True),
        ),
    ]
