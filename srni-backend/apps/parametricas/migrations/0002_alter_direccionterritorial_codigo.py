from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parametricas", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="direccionterritorial",
            name="codigo",
            field=models.CharField(db_index=True, max_length=30, unique=True),
        ),
    ]
