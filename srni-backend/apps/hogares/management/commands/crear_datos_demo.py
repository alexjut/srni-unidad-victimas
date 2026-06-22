"""
Management command: crear_datos_demo

Genera datos de ejemplo (ficticios) para que el panel se vea poblado en la
presentación: víctimas titulares, hogares, miembros, sesiones de encuesta y
respuestas. Idempotente (no duplica si ya existe el hogar del titular).

Uso:
    python manage.py crear_datos_demo
"""
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.victimas.models import Victima
from apps.hogares.models import Hogar, MiembroHogar
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta
from apps.formulario.models import Instrumento, Pregunta
from apps.parametricas.models import TipoDocumento, Municipio
from apps.autenticacion.models import Usuario

# cons, documento, p1, p2, a1, a2, fnac, genero, mpio_dane, estado_hogar, estado_sesion, pct
# Documentos en rango 99950000xx — NO colisionan con las cédulas del mock
# (99901000xx titulares, 99902000xx miembros, 1030547250 real). Nombres
# ficticios distintos de los del mock para evitar confusión en la demo.
TITULARES = [
    (90001, '9995000001', 'Beatriz', 'Helena',   'Cuéllar',   'Naranjo',  date(1980, 5, 15), 'F', '05001', 'ACTIVO',   'COMPLETADA',  100),
    (90002, '9995000002', 'Mariela', 'Antonia',  'Bermúdez',  'Galvis',   date(1955, 1, 30), 'F', '54001', 'ACTIVO',   'COMPLETADA',  100),
    (90003, '9995000003', 'Ernesto', 'Iván',     'Pabón',     'Lozada',   date(1968, 7,  4), 'M', '05001', 'ACTIVO',   'EN_PROGRESO',  60),
    (90004, '9995000004', 'Yolanda', 'Patricia', 'Arboleda',  'Quiroz',   date(1972, 9,  7), 'F', '27001', 'BORRADOR', 'EN_PROGRESO',  35),
    (90005, '9995000005', 'Diana',   'Carolina', 'Zambrano',  'Idárraga', date(1990, 11, 25),'F', '19001', 'ACTIVO',   'COMPLETADA',  100),
    (90006, '9995000006', 'Wilmar',  'Esteban',  'Granados',  'Carvajal', date(1975, 2, 10), 'M', '11001', 'ACTIVO',   'COMPLETADA',  100),
    (90007, '9995000007', 'Sandra',  'Liliana',  'Montenegro','Acuña',    date(1988, 6,  3), 'F', '76001', 'BORRADOR', 'INICIADA',     10),
    (90008, '9995000008', 'Reinaldo','Octavio',  'Villalba',  'Forero',   date(1969, 12, 20),'M', '08001', 'ACTIVO',   'COMPLETADA',  100),
    (90009, '9995000009', 'Adriana', 'Consuelo', 'Espinosa',  'Tafur',    date(1982, 3, 28), 'F', '13001', 'ACTIVO',   'EN_PROGRESO',  75),
    (90010, '9995000010', 'Gustavo', 'Adolfo',   'Murillo',   'Bedoya',   date(1991, 8,  8), 'M', '50001', 'BORRADOR', 'SUSPENDIDA',   45),
]

TIPO_VIVIENDA = ['CASA', 'APARTAMENTO', 'CUARTO']
CONDICION = ['PROPIA', 'ARRIENDO', 'FAMILIAR']


class Command(BaseCommand):
    help = "Genera datos de ejemplo (hogares, encuestas, respuestas) para la presentación."

    def handle(self, *args, **options):
        cc = TipoDocumento.objects.filter(codigo='CC').first()
        instrumento = Instrumento.objects.filter(activo=True).order_by('codigo').first()
        if not instrumento:
            self.stderr.write("No hay instrumentos cargados. Corre primero crear_instrumentos_base / cargar_*.")
            return
        preguntas = list(Pregunta.objects.filter(capitulo__instrumento=instrumento).order_by('orden')[:6])
        encuestadores = list(Usuario.objects.filter(codigo_usuario__startswith='ENC').order_by('codigo_usuario'))
        if not encuestadores:
            encuestadores = list(Usuario.objects.all()[:1])

        creados_h = creados_s = 0

        for i, (cons, doc, p1, p2, a1, a2, fn, gen, mpio_dane, est_h, est_s, pct) in enumerate(TITULARES):
            try:
                with transaction.atomic():
                    mpio = Municipio.objects.filter(codigo_dane=mpio_dane).first()
                    enc = encuestadores[i % len(encuestadores)]

                    victima, _ = Victima.objects.get_or_create(
                        cons_persona=cons,
                        defaults={
                            'tipo_documento': cc,
                            'numero_documento': doc,
                            'primer_nombre': p1, 'segundo_nombre': p2,
                            'primer_apellido': a1, 'segundo_apellido': a2,
                            'fecha_nacimiento': fn.isoformat(), 'genero': gen,
                            'estado_ruv': 'INCLUIDO',
                            'habilitado_para_caracterizacion': True,
                            'municipio_residencia': mpio,
                        },
                    )

                    if Hogar.objects.filter(autorizado=victima).exists():
                        continue  # idempotente

                    n_personas = 2 + (i % 3)
                    hogar = Hogar.objects.create(
                        codigo_hogar=f'DEMO-{cons}',
                        autorizado=victima,
                        municipio=mpio,
                        tipo_vivienda=TIPO_VIVIENDA[i % len(TIPO_VIVIENDA)],
                        condicion_ocupacion=CONDICION[i % len(CONDICION)],
                        estrato=(i % 3) + 1,
                        numero_cuartos=(i % 3) + 1,
                        numero_personas=n_personas,
                        estado=est_h,
                        creado_por=enc,
                    )
                    creados_h += 1

                    # Titular (autorizado)
                    MiembroHogar.objects.create(
                        hogar=hogar, victima=victima,
                        nombre_completo=f'{p1} {a1}', genero=gen,
                        es_autorizado=True, rol='MIEMBRO',
                        creado_por=enc,
                    )
                    # Miembros adicionales
                    for m in range(1, n_personas):
                        MiembroHogar.objects.create(
                            hogar=hogar,
                            nombre_completo=f'Integrante {m} de {a1}',
                            genero='F' if m % 2 else 'M',
                            es_autorizado=False, rol='MIEMBRO',
                            creado_por=enc,
                        )

                    # Sesión de encuesta
                    sesion = SesionEncuesta.objects.create(
                        hogar=hogar, instrumento=instrumento, encuestador=enc,
                        estado=est_s, porcentaje_completado=pct,
                        fecha_fin=timezone.now() if est_s == 'COMPLETADA' else None,
                    )
                    creados_s += 1

                    # Respuestas de ejemplo
                    for j, preg in enumerate(preguntas):
                        RespuestaEncuesta.objects.create(
                            sesion=sesion, pregunta=preg,
                            valor=('Sí' if j % 2 == 0 else 'No'),
                        )

                    self.stdout.write(f"  Hogar DEMO-{cons} ({est_h}/{est_s}) creado")
            except Exception as e:  # noqa: BLE001
                self.stderr.write(f"  (falló titular {cons}): {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Datos demo listos: {creados_h} hogares, {creados_s} sesiones."
        ))
