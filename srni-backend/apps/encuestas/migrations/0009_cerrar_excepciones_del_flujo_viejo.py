"""
Marca como USADA toda excepción registrada con el flujo anterior al 14-ago-2026.

`estado` nace con default `VIGENTE`, y eso es lo correcto para las
habilitaciones nuevas —se otorgan antes de usarse—. Pero las viejas son lo
contrario: se registraban **después** de caracterizar, como rastro de algo ya
hecho. Dejarlas en `VIGENTE` convertiría cada rastro histórico en un permiso
abierto para volver a saltarse la regla de los dos años sobre esa persona.

Se reconocen por tener `sesion`: en el flujo viejo la excepción colgaba de la
sesión de encuesta que la usaba, y en el nuevo nace sin ninguna.

`usada_at` se toma de `created_at` y no de `now()`: la excepción se usó cuando
se registró, no cuando corre esta migración.

En producción es probable que esto no toque ninguna fila —el endpoint viejo
escribía la auditoría con un kwarg inexistente (`ip=` sobre un modelo que tiene
`ip_origen`) y terminaba en 500 antes de responder, y ninguna encuestadora había
entrado todavía—. Corre igual: "probablemente cero" no es cero.
"""
from django.db import migrations
from django.db.models import F


def cerrar_las_viejas(apps, schema_editor):
    ExcepcionVigencia = apps.get_model('encuestas', 'ExcepcionVigencia')
    ExcepcionVigencia.objects.filter(
        sesion__isnull=False, estado='VIGENTE',
    ).update(estado='USADA', usada_en_sesion=F('sesion'), usada_at=F('created_at'))


def revertir(apps, schema_editor):
    """
    Deja de nuevo en VIGENTE solo las que esta migración cerró.

    Se distinguen por tener `usada_at == created_at`: una habilitación del flujo
    nuevo se consume al finalizar la encuesta, siempre después de crearse.
    """
    ExcepcionVigencia = apps.get_model('encuestas', 'ExcepcionVigencia')
    ExcepcionVigencia.objects.filter(
        sesion__isnull=False, estado='USADA', usada_at=F('created_at'),
    ).update(estado='VIGENTE', usada_en_sesion=None, usada_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ('encuestas', '0008_excepcionvigencia_anulada_at_and_more'),
    ]

    operations = [
        migrations.RunPython(cerrar_las_viejas, revertir),
    ]
