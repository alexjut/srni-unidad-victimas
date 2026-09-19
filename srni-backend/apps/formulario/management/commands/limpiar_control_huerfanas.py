"""
Quita del capítulo de control las preguntas que quedaron con el sufijo de otro
instrumento.

El capítulo «T. CONTROL» lo siembra `cargar_capitulo_control`, que arma el código de
cada pregunta con un sufijo por instrumento: `_te` para Territorial y `_tel` para los
demás. Una corrida anterior usó el sufijo equivocado, y en producción quedaron tres
preguntas de control con el código de otro perfil —las «huérfanas del Telefónico» que
el estado del 1-sep dejó anotadas como limpieza pendiente—.

No estorban al encuestador (el capítulo de control no se diligencia en campo), pero sí
al que compara: la verificación de paridad entre el servidor y la APK las cuenta como
diferencia, y mientras estén, esa verificación nunca da 8 de 8 y deja de servir como
alarma.

Nunca borra una pregunta con respuestas. Si alguien alcanzó a contestarla, deja de ser
un resto de instalación y pasa a ser un dato de campo; en ese caso se informa y se
desactiva, que quita la pregunta de la vista sin tocar lo capturado.

Uso:
    python manage.py limpiar_control_huerfanas --dry-run
    python manage.py limpiar_control_huerfanas
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.encuestas.models import RespuestaEncuesta
from apps.formulario.models import Pregunta

# El mismo criterio que usa `cargar_capitulo_control` al sembrarlas.
SUFIJO_ESPERADO = {'TERRITORIAL': '_te'}
SUFIJO_POR_DEFECTO = '_tel'


def sufijo_de(codigo_instrumento: str) -> str:
    return SUFIJO_ESPERADO.get(codigo_instrumento, SUFIJO_POR_DEFECTO)


def es_huerfana(codigo_externo: str, codigo_instrumento: str) -> bool:
    """
    ¿Esta pregunta de control lleva el sufijo de otro instrumento?

    `T1_tel` en Telefónico está bien; `T1_te` en Telefónico es un resto de una corrida
    con el sufijo equivocado. Solo se miran los códigos con forma de pregunta de
    control (`T1`, `T2`, `T3` más sufijo): cualquier otra cosa dentro del capítulo la
    puso alguien a propósito y no es asunto de este comando.
    """
    esperado = sufijo_de(codigo_instrumento)
    for base in ('T1', 'T2', 'T3'):
        if codigo_externo.startswith(base):
            resto = codigo_externo[len(base):]
            if resto.startswith('_') and resto != esperado:
                return True
    return False


class Command(BaseCommand):
    help = 'Limpia preguntas del capítulo de control con el sufijo de otro instrumento.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='No escribe: informa qué haría.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']

        candidatas = (
            Pregunta.objects
            .filter(capitulo__codigo='T')
            .select_related('capitulo', 'capitulo__instrumento')
            .order_by('capitulo__instrumento__codigo', 'orden')
        )

        borradas, desactivadas = 0, 0
        for pregunta in candidatas:
            instrumento = pregunta.capitulo.instrumento.codigo
            if not es_huerfana(pregunta.codigo_externo, instrumento):
                continue

            respuestas = RespuestaEncuesta.objects.filter(pregunta=pregunta).count()
            if respuestas:
                self.stdout.write(self.style.WARNING(
                    f'  · {instrumento} · {pregunta.codigo_externo}: tiene {respuestas} '
                    'respuesta(s) — se desactiva, no se borra'))
                desactivadas += 1
                if not dry:
                    Pregunta.objects.filter(pk=pregunta.pk).update(activa=False)
                continue

            self.stdout.write(
                f'  · {instrumento} · {pregunta.codigo_externo} '
                f'(esperado {sufijo_de(instrumento)}) — se borra')
            borradas += 1
            if not dry:
                with transaction.atomic():
                    pregunta.delete()

        if not borradas and not desactivadas:
            self.stdout.write(self.style.SUCCESS(
                'No hay preguntas de control con el sufijo equivocado.'))
            return

        etiqueta = '[DRY-RUN] ' if dry else ''
        self.stdout.write(self.style.SUCCESS(
            f'{etiqueta}{borradas} borradas · {desactivadas} desactivadas (tenían respuestas).'))
        if dry:
            self.stdout.write('Corré el comando sin --dry-run para aplicarlo.')
        else:
            self.stdout.write(self.style.WARNING(
                'Regenerá los bundles con `exportar_a_mobile` si algo cambió.'))
