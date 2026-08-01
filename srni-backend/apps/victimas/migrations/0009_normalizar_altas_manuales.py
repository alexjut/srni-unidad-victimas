"""
Normaliza las víctimas dadas de alta a mano en campo.

Dos arreglos en la misma pasada, sobre las mismas filas:

1. `fuente_origen='NO_INCLUIDA'` **no existe** en `Victima.FUENTE_ORIGEN`. Entraba
   porque el serializer era un `CharField` suelto. Su equivalente real es `MANUAL`.
2. Esas mismas filas quedaron con `estado_ruv='NO_INCLUIDO'`, que afirma algo que
   nadie verificó. Lo único que se comprobó es que la persona no estaba en el
   padrón descargado, y 1,88 M de víctimas **incluidas** están en esa situación
   (ver docs/oracle-legacy-padron/hallazgos_identidad_padron.md). Pasan a
   `NO_VERIFICADO`.

Se toca **solo** lo que tiene la marca `NO_INCLUIDA`: un `NO_INCLUIDO` con
fuente RUV sí viene verificado de la fuente y no se toca.

`OFFLINE` también estaba fuera de dominio, pero ese registro sí salió del padrón:
su fuente real es `RUV` y su `estado_ruv` se respeta tal como vino.
"""

from django.db import migrations


def normalizar(apps, schema_editor):
    Victima = apps.get_model('victimas', 'Victima')

    Victima.objects.filter(
        fuente_origen='NO_INCLUIDA', estado_ruv='NO_INCLUIDO'
    ).update(fuente_origen='MANUAL', estado_ruv='NO_VERIFICADO')

    # Alta manual cuyo estado ya no era NO_INCLUIDO: solo se corrige la fuente.
    Victima.objects.filter(fuente_origen='NO_INCLUIDA').update(fuente_origen='MANUAL')

    Victima.objects.filter(fuente_origen='OFFLINE').update(fuente_origen='RUV')


def revertir(apps, schema_editor):
    # No se puede distinguir un MANUAL nuevo de uno convertido, así que la reversa
    # devuelve al estado viejo lo que la ida produjo: MANUAL + NO_VERIFICADO.
    Victima = apps.get_model('victimas', 'Victima')
    Victima.objects.filter(
        fuente_origen='MANUAL', estado_ruv='NO_VERIFICADO'
    ).update(fuente_origen='NO_INCLUIDA', estado_ruv='NO_INCLUIDO')


class Migration(migrations.Migration):

    dependencies = [
        ('victimas', '0008_alter_victima_estado_ruv'),
    ]

    operations = [
        migrations.RunPython(normalizar, revertir),
    ]
