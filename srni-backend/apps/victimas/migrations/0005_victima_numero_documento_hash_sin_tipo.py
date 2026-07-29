"""
Añade el índice de RESPALDO por número de documento, y lo puebla.

Para qué: en la fuente hay 1.126.615 personas (14,5 %) sin tipo de documento
registrado. Con solo el hash de identidad —que incluye el tipo— esas personas serían
inencontrables: el encuestador escribe "CC + número" y la llave nunca coincide. Este
índice permite hallarlas y advertir que se verifique, sin inventarles el tipo.

El `RunPython` no es opcional: sin él, las filas ya cargadas quedan con el campo
vacío y el respaldo no las encontraría.
"""
import hashlib
import unicodedata

from django.db import migrations, models


def _num_hash(numero):
    """Copia local de `repository.base.num_hash` — una migración no importa código
    de la aplicación: debe describir lo que hizo el día que se aplicó."""
    s = (numero or "").strip()
    for ch in (" ", ".", "-"):
        s = s.replace(ch, "")
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def poblar(apps, schema_editor):
    Victima = apps.get_model("victimas", "Victima")
    pendientes, total = [], 0
    for victima in Victima.objects.iterator(chunk_size=1000):
        if not victima.numero_documento:
            continue
        victima.numero_documento_hash_sin_tipo = _num_hash(str(victima.numero_documento))
        pendientes.append(victima)
        if len(pendientes) >= 1000:
            Victima.objects.bulk_update(pendientes, ["numero_documento_hash_sin_tipo"])
            total += len(pendientes)
            pendientes = []
    if pendientes:
        Victima.objects.bulk_update(pendientes, ["numero_documento_hash_sin_tipo"])
        total += len(pendientes)
    if total:
        print(f"  victimas: {total} indice(s) de respaldo poblados")


def vaciar(apps, schema_editor):
    apps.get_model("victimas", "Victima").objects.update(numero_documento_hash_sin_tipo="")


class Migration(migrations.Migration):

    dependencies = [
        ('victimas', '0004_recalcular_hash_documento'),
    ]

    operations = [
        migrations.AddField(
            model_name='victima',
            name='numero_documento_hash_sin_tipo',
            field=models.CharField(blank=True, db_index=True, default='', help_text='SHA-256 solo del número, para encontrar personas cuyo tipo de documento no está registrado en la fuente.', max_length=64),
        ),
        migrations.RunPython(poblar, vaciar),
    ]
