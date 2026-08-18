"""
Enciende `puede_autorizar_excepciones` en los perfiles que sí deben tenerlo.

Sin esto el campo nace en `False` para todos y **nadie** podría autorizar una
excepción: el front tendría el endpoint y ningún usuario capaz de usarlo, lo que
en campo se lee como "la plataforma no deja". El flag se agrega junto con la
columna, no en un paso manual posterior.

Quién sí y quién no, y por qué:

    COORDINADOR    ✅  recibe el soporte y coordina la operación en territorio
    SUPERVISOR     ✅  supervisa la operación; es el reemplazo natural
    ADMINISTRADOR  ✅  puede todo por definición
    ENCUESTADOR    ❌  es quien ejecuta; separar autorización de ejecución es
                       la razón de ser del cambio del 14-ago-2026
    DOCUMENTADOR   ❌  se creó de solo lectura a propósito (11-ago). Habilitar
                       una excepción altera la caracterización de una víctima,
                       que es exactamente lo que se le negó

Si un perfil no existe en esta base, no pasa nada: el `filter` no lo encuentra y
sigue. La migración corre igual en desarrollo, donde puede faltar alguno.
"""
from django.db import migrations

PERFILES_AUTORIZADORES = ['COORDINADOR', 'SUPERVISOR', 'ADMINISTRADOR']


def activar(apps, schema_editor):
    Perfil = apps.get_model('autenticacion', 'Perfil')
    Perfil.objects.filter(codigo__in=PERFILES_AUTORIZADORES).update(
        puede_autorizar_excepciones=True)


def desactivar(apps, schema_editor):
    Perfil = apps.get_model('autenticacion', 'Perfil')
    Perfil.objects.filter(codigo__in=PERFILES_AUTORIZADORES).update(
        puede_autorizar_excepciones=False)


class Migration(migrations.Migration):

    dependencies = [
        ('autenticacion', '0002_perfil_puede_autorizar_excepciones'),
    ]

    operations = [
        migrations.RunPython(activar, desactivar),
    ]
