"""
Sprint 20 — Cargar capítulo T. CONTROL en instrumentos que lo tienen vacío.

Hallazgo QA Sprint 20: TERRITORIAL y TELEFONICO tienen el capítulo "T. CONTROL"
pero sin preguntas (los otros 5 instrumentos tienen las 3 preguntas estándar
T1/T2/T3 — finalización entrevista, duración, observaciones).

Las preguntas T1-T3 son metadata de QA del encuestador (no respuestas de la
víctima). Sin ellas no se puede cerrar correctamente una sesión.

Uso:
    python manage.py cargar_capitulo_control

Idempotente: usa update_or_create por (capitulo, codigo_externo).
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.formulario.models import Capitulo, Pregunta


# Códigos de instrumento donde falta cargar el cap T
INSTRUMENTOS_FALTANTES = ['TERRITORIAL', 'TELEFONICO']

# Plantilla de las 3 preguntas estándar T1/T2/T3 (basadas en otros instrumentos)
PREGUNTAS_CONTROL = [
    {
        'orden': 1,
        'no_pregunta': 'T1',
        'tipo': 'BOOLEAN',
        'nivel': 'HOGAR',
        'texto': 'Encuestador: ¿La entrevista fue completada?',
        'obligatoria': True,
    },
    {
        'orden': 2,
        'no_pregunta': 'T2',
        'tipo': 'NUMERICO',
        'nivel': 'HOGAR',
        'texto': '¿Cuánto tiempo tomó la entrevista (minutos)?',
        'obligatoria': True,
    },
    {
        'orden': 3,
        'no_pregunta': 'T3',
        'tipo': 'TEXTO_LARGO',
        'nivel': 'HOGAR',
        'texto': 'Observaciones generales del encuestador',
        'obligatoria': False,
    },
]


class Command(BaseCommand):
    help = 'Carga las 3 preguntas estándar de cap T. CONTROL en instrumentos vacíos.'

    @transaction.atomic
    def handle(self, *args, **options):
        creadas_total = 0
        for codigo_instr in INSTRUMENTOS_FALTANTES:
            try:
                cap = Capitulo.objects.get(codigo='T', instrumento__codigo=codigo_instr)
            except Capitulo.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'{codigo_instr}: no tiene capítulo T — saltando'
                ))
                continue

            # Sufijo por convención (T1_te, T1_tel) — usar el código del cap o instrumento
            sufijo = '_te' if codigo_instr == 'TERRITORIAL' else '_tel'

            creadas = 0
            for plantilla in PREGUNTAS_CONTROL:
                codigo_externo = f'{plantilla["no_pregunta"]}{sufijo}'
                _, created = Pregunta.objects.update_or_create(
                    capitulo=cap,
                    codigo_externo=codigo_externo,
                    defaults={
                        'orden': plantilla['orden'],
                        'no_pregunta': plantilla['no_pregunta'],
                        'tipo': plantilla['tipo'],
                        'nivel': plantilla['nivel'],
                        'texto': plantilla['texto'],
                        'obligatoria': plantilla['obligatoria'],
                        'activa': True,
                    },
                )
                creadas += int(created)
                creadas_total += int(created)

            self.stdout.write(f'{codigo_instr}: {creadas} preguntas creadas (T1, T2, T3)')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Total preguntas creadas: {creadas_total}'))
        self.stdout.write(self.style.WARNING(
            'Corre `python manage.py exportar_a_mobile` para regenerar los bundles.'
        ))
