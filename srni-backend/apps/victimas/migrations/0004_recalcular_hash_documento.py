"""
Recalcula `numero_documento_hash` con la definición única de `repository.base.doc_hash`.

Por qué hace falta
------------------
Hasta el 2026-07-29 `Victima.save()` guardaba `sha256(numero.strip().upper())` —solo
el número— mientras el repositorio y el generador del padrón buscaban por
`doc_hash("<tipo>|<numero>")`, en minúsculas y sin puntos ni guiones. Eran dos hashes
distintos para la misma cosa, así que **la búsqueda por documento no encontraba nada**.

Al unificar la fórmula, las filas ya guardadas quedan con el hash viejo y seguirían
sin poder encontrarse. Esta migración las recalcula.

Cómo lo hace
------------
`numero_documento` es un `EncryptedField`: se descifra al leer y se vuelve a cifrar al
escribir, así que basta con recorrer y guardar. Se usa `.iterator()` por si la tabla
tiene volumen —el padrón puede ser de millones— y se actualiza solo la columna del
hash, sin reescribir la PII.

Es reversible en el sentido práctico: `reverse` vuelve a la fórmula anterior, por si
hubiera que retroceder el despliegue.
"""
import hashlib

from django.db import migrations


def _doc_hash_nuevo(tipo, numero):
    """Copia local de `repository.base.doc_hash`.

    Las migraciones no deben importar código de la aplicación: si mañana esa función
    cambia, esta migración —que ya corrió— seguiría describiendo lo que hizo el día
    que se aplicó, que es justo lo que debe hacer una migración.
    """
    import unicodedata

    def _limpiar(parte):
        s = (parte or "").strip()
        for ch in (" ", ".", "-"):
            s = s.replace(ch, "")
        s = s.lower()
        s = unicodedata.normalize("NFKD", s)
        return "".join(c for c in s if not unicodedata.combining(c))

    canon = f"{_limpiar(tipo)}|{_limpiar(numero)}"
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _hash_viejo(_tipo, numero):
    return hashlib.sha256(str(numero).strip().upper().encode("utf-8")).hexdigest()


def _recalcular(apps, schema_editor, formula):
    Victima = apps.get_model("victimas", "Victima")
    # `apps.get_model` da el modelo histórico, que conserva los EncryptedField y por
    # tanto sigue descifrando al leer.
    pendientes, procesadas = [], 0
    for victima in Victima.objects.select_related("tipo_documento").iterator(chunk_size=1000):
        if not victima.numero_documento:
            continue
        tipo = victima.tipo_documento.codigo if victima.tipo_documento_id else ""
        nuevo = formula(tipo, str(victima.numero_documento))
        if nuevo != victima.numero_documento_hash:
            victima.numero_documento_hash = nuevo
            pendientes.append(victima)
        if len(pendientes) >= 1000:
            Victima.objects.bulk_update(pendientes, ["numero_documento_hash"])
            procesadas += len(pendientes)
            pendientes = []
    if pendientes:
        Victima.objects.bulk_update(pendientes, ["numero_documento_hash"])
        procesadas += len(pendientes)
    if procesadas:
        print(f"  victimas: {procesadas} hash(es) de documento recalculados")


def adelante(apps, schema_editor):
    _recalcular(apps, schema_editor, _doc_hash_nuevo)


def atras(apps, schema_editor):
    _recalcular(apps, schema_editor, _hash_viejo)


class Migration(migrations.Migration):

    dependencies = [
        ("victimas", "0003_alter_victima_fuente_origen"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
