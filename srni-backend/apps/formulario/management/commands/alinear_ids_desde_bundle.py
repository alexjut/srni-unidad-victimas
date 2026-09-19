"""
Alinea el identificador de una pregunta del servidor con el que trae la APK.

Por qué existe. Las respuestas que manda el teléfono viajan con el **id de la
pregunta**, no con su código. Si el servidor tiene esa misma pregunta con otro id, la
respuesta se rechaza —HTTP 400— y la encuestadora no se entera: su captura se queda en
la cola del dispositivo.

Eso es lo que estaba pasando con las tres preguntas del capítulo de control del perfil
Telefónico. Se venían arrastrando como «huérfanas» desde el 1-sep-2026, y no sobraban:
existían en los dos lados con identificadores distintos. La diferencia es importante,
porque el arreglo obvio —borrarlas— habría dejado a la APK mandando respuestas de tres
preguntas que ya no existirían en el servidor.

El capítulo de control no lo carga el fixture: lo siembra `cargar_capitulo_control`,
que genera identificadores nuevos en cada instalación. Por eso el desajuste no lo
corrige `sincronizar_ids_fixture_desde_bundle`, que trabaja sobre el fixture.

Cómo se corrige sin perder nada: se crea la pregunta con el identificador de la APK,
se le pasan las respuestas y las reglas que apuntaban a la vieja, y recién entonces se
borra la vieja. Todo dentro de una transacción.

Uso:
    python manage.py alinear_ids_desde_bundle --mapa /tmp/ctrl_bundle.json --dry-run
    python manage.py alinear_ids_desde_bundle --mapa /tmp/ctrl_bundle.json

El mapa es `{"INSTRUMENTO": {"codigo_externo": "uuid-de-la-apk"}}` y sale de los
paquetes que viajan dentro de la aplicación.
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.encuestas.models import RespuestaEncuesta
from apps.formulario.models import Pregunta, ReglaSkipLogic


class Command(BaseCommand):
    help = 'Alinea ids de preguntas del servidor con los del bundle de la APK.'

    def add_arguments(self, parser):
        parser.add_argument('--mapa', required=True,
                            help='JSON {instrumento: {codigo_externo: uuid}}.')
        parser.add_argument('--dry-run', action='store_true',
                            help='No escribe: informa qué cambiaría.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        try:
            mapa = json.load(open(opts['mapa'], encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as e:
            raise CommandError(f'No se pudo leer el mapa: {e}')

        alineadas, faltantes, iguales = 0, 0, 0

        for instrumento, preguntas in mapa.items():
            for codigo, id_apk in preguntas.items():
                vieja = Pregunta.objects.filter(
                    capitulo__instrumento__codigo=instrumento,
                    codigo_externo=codigo,
                ).select_related('capitulo').first()

                if not vieja:
                    self.stdout.write(self.style.WARNING(
                        f'  · {instrumento} · {codigo}: no existe en el servidor'))
                    faltantes += 1
                    continue

                if str(vieja.id) == id_apk:
                    iguales += 1
                    continue

                respuestas = RespuestaEncuesta.objects.filter(pregunta=vieja).count()
                self.stdout.write(
                    f'  · {instrumento} · {codigo}: {str(vieja.id)[:8]} → {id_apk[:8]}'
                    + (f' (con {respuestas} respuesta(s) que se trasladan)' if respuestas else ''))
                alineadas += 1

                if not dry:
                    self._realinear(vieja, id_apk)

        etiqueta = '[DRY-RUN] ' if dry else ''
        self.stdout.write(self.style.SUCCESS(
            f'{etiqueta}{alineadas} alineadas · {iguales} ya coincidían · {faltantes} sin contraparte.'))
        if dry and alineadas:
            self.stdout.write('Corré el comando sin --dry-run para aplicarlo.')

    def _realinear(self, vieja: Pregunta, id_apk: str) -> None:
        """
        Copia la pregunta con el id de la APK, le traslada lo que colgaba de la vieja
        y borra la vieja.

        No se puede cambiar la llave primaria en sitio: la base la usa como destino de
        las respuestas y de las reglas. Por eso el rodeo, y por eso va en transacción:
        a mitad de camino quedarían dos preguntas iguales compitiendo por el mismo
        código.
        """
        with transaction.atomic():
            campos = {
                f.name: getattr(vieja, f.name)
                for f in Pregunta._meta.fields
                if f.name not in ('id',)
            }

            # El código es único dentro del capítulo, así que las dos no pueden
            # coexistir ni un instante con el mismo. Se aparta el de la vieja
            # mientras dura el traslado; se borra al final de la misma transacción.
            Pregunta.objects.filter(pk=vieja.pk).update(
                codigo_externo=f'{vieja.codigo_externo}__realineando')

            nueva = Pregunta.objects.create(id=id_apk, **campos)

            # Las opciones cuelgan de la pregunta; se recrean apuntando a la nueva.
            for opcion in vieja.opciones.all():
                opcion.pk = None
                opcion.id = None
                opcion.pregunta = nueva
                opcion.save()

            RespuestaEncuesta.objects.filter(pregunta=vieja).update(pregunta=nueva)
            ReglaSkipLogic.objects.filter(pregunta_origen=vieja).update(pregunta_origen=nueva)
            ReglaSkipLogic.objects.filter(pregunta_afectada=vieja).update(pregunta_afectada=nueva)

            vieja.delete()
