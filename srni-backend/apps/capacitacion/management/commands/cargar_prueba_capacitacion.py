"""
Carga el pre-test y el post-test de la capacitación de septiembre de 2026.

Las quince preguntas son las del Anexo A del plan de capacitación, verificadas
contra el sistema real: la versión de la aplicación, la regla de vigencia de dos
años, quién autoriza la excepción, la precarga de la jornada, la cola de
sincronización, los 14 capítulos del instrumento territorial y los niveles hogar
y persona.

Pre y post comparten el mismo cuestionario a propósito: aplicar el mismo
instrumento en los dos momentos es lo que permite medir la ganancia por persona.

    python manage.py cargar_prueba_capacitacion
    python manage.py cargar_prueba_capacitacion --reemplazar
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.capacitacion.models import PreguntaPrueba, Prueba

PAREJA = 'capacitacion-2026-09'

# (enunciado, [opciones], correcta, explicación que se muestra si falla)
PREGUNTAS = [
    ("Para ingresar a SICAV Móvil, el usuario escribe:",
     ["Su nombre completo", "Su código de usuario institucional",
      "Su número de cédula", "Su correo electrónico"], "B",
     "Se ingresa con el código de usuario institucional, no con el nombre ni la cédula."),

    ("La versión de la aplicación instalada se puede confirmar:",
     ["Solo desde la Play Store", "En la pantalla de inicio de sesión",
      "Llamando a soporte", "No es posible confirmarla"], "B",
     "La versión aparece en la propia pantalla de ingreso. Inclúyala siempre al reportar una incidencia."),

    ("La regla de vigencia establece que no se puede volver a caracterizar a una persona antes de:",
     ["Seis meses", "Un año", "Dos años", "Cinco años"], "C",
     "Son dos años. Es una regla de la entidad para no duplicar el esfuerzo de campo."),

    ("Cuando una persona tiene ficha vigente y aun así debe caracterizarse, la excepción se autoriza desde:",
     ["La propia APK, tomando una foto del soporte",
      "El Panel de Control, por un perfil con permiso de autorizar",
      "Cualquier encuestador desde su celular", "Un correo a la mesa de ayuda"], "B",
     "La autoriza coordinación desde el panel. El encuestador no maneja el soporte documental: llega por canal institucional al nivel central."),

    ("Para registrar una excepción de vigencia en el panel se exige obligatoriamente:",
     ["Únicamente el número de documento", "Ruta, radicado y motivo",
      "Solo el archivo de soporte escaneado", "La autorización verbal del coordinador"], "B",
     "Ruta, radicado y motivo son obligatorios. El archivo es opcional."),

    ("Una excepción de vigencia autorizada:",
     ["Queda activa de forma permanente para esa persona",
      "Es de un solo uso y se consume al finalizar la encuesta",
      "Dura 30 días calendario", "Se puede reutilizar en otro hogar"], "B",
     "Es de un solo uso. Si más adelante la misma persona requiere otra, hay que solicitarla de nuevo."),

    ("La información que permite trabajar sin señal se descarga al dispositivo:",
     ["Al iniciar sesión (precarga de la jornada)", "Cada vez que se abre un capítulo",
      "Solo cuando el encuestador la solicita", "No se descarga: siempre se requiere conexión"], "A",
     "Se precarga al iniciar sesión. Por eso conviene entrar con señal antes de salir a campo."),

    ("Si el encuestador pierde la señal a mitad de una caracterización:",
     ["Se pierde lo diligenciado y debe empezar de nuevo",
      "Puede continuar; lo capturado queda en la cola de sincronización",
      "La app se cierra automáticamente", "Debe llamar a soporte antes de continuar"], "B",
     "Puede continuar. Lo capturado queda en la cola y sube cuando vuelve la señal."),

    ("Una caracterización se considera efectivamente entregada al sistema cuando:",
     ["Se responde el último capítulo", "Aparece el mensaje de guardado en el celular",
      "La cola de sincronización queda en cero y la sesión figura sincronizada",
      "Se cierra la aplicación"], "C",
     "Responder el último capítulo no basta: la jornada no se cierra hasta que la cola esté en cero."),

    ("El instrumento territorial vigente (V8) está organizado en:",
     ["5 capítulos", "9 capítulos", "14 capítulos", "21 capítulos"], "C",
     "Son 14 capítulos y 363 preguntas."),

    ("Una pregunta de nivel PERSONA significa que:",
     ["Se responde una sola vez para todo el hogar",
      "Se responde una vez por cada integrante del hogar",
      "Solo la responde el jefe de hogar", "Es opcional"], "B",
     "Se responde por cada integrante. En un hogar de 3 personas, un capítulo de 8 preguntas son 24 respuestas."),

    ("La lógica de saltos (skip-logic) hace que:",
     ["Se pueda saltar cualquier pregunta a criterio del encuestador",
      "Algunas preguntas se muestren u oculten según respuestas anteriores",
      "El formulario avance solo cada 5 minutos", "Se repita el capítulo si hay un error"], "B",
     "Si falta una pregunta que esperaba ver, lo más probable es que una regla la esté ocultando: revise lo respondido antes de reportarlo."),

    ("Si la persona a caracterizar no aparece en la búsqueda:",
     ["No se le puede caracterizar bajo ninguna circunstancia",
      "Se registra por alta manual siguiendo el procedimiento definido",
      "Se usa el documento de un familiar", "Se deja el campo en blanco"], "B",
     "Se usa «Agregar como víctima no incluida». Nunca el documento de otra persona."),

    ("La norma que rige el tratamiento de los datos personales que se capturan es:",
     ["Ley 1448 de 2011 únicamente", "Ley 1581 de 2012 (Habeas Data)",
      "Decreto 1084 de 2015", "No aplica norma específica"], "B",
     "Ley 1581 de 2012. Por eso los reportes de incidencia no deben incluir datos de la persona entrevistada."),

    ("Frente a un comportamiento inesperado de la aplicación, lo correcto es:",
     ["Desinstalar y reinstalar sin avisar",
      "Reportarlo por el canal definido, indicando versión, pantalla y qué se hizo antes",
      "Continuar y no mencionarlo", "Prestar el celular a otro compañero para que lo intente"], "B",
     "Un reporte sirve si permite reproducir: versión, pantalla, pasos previos y qué se esperaba."),
]

CLAVES = ['A', 'B', 'C', 'D']


class Command(BaseCommand):
    help = 'Carga el pre-test y el post-test de la capacitación de septiembre de 2026.'

    def add_arguments(self, parser):
        parser.add_argument('--reemplazar', action='store_true',
                            help='Borra las preguntas existentes y las vuelve a crear.')

    @transaction.atomic
    def handle(self, *args, **opts):
        for momento, etiqueta in ((Prueba.Momento.PRE, 'Pre-test'),
                                  (Prueba.Momento.POST, 'Post-test')):
            codigo = f'{PAREJA}-{momento.lower()}'
            prueba, creada = Prueba.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'titulo': f'{etiqueta} — Capacitación SICAV Móvil y Panel de Control',
                    'descripcion': (
                        'Quince preguntas de selección múltiple. Se responde una sola vez. '
                        'Al terminar verá su resultado y en qué falló.'),
                    'momento': momento,
                    'pareja': PAREJA,
                },
            )
            if opts['reemplazar']:
                prueba.preguntas.all().delete()

            if prueba.preguntas.exists():
                self.stdout.write(f'  {codigo}: ya tiene {prueba.total_preguntas} preguntas, se deja como está.')
                continue

            for i, (enunciado, opciones, correcta, explicacion) in enumerate(PREGUNTAS, start=1):
                PreguntaPrueba.objects.create(
                    prueba=prueba, orden=i, enunciado=enunciado,
                    opciones=[{'clave': CLAVES[j], 'texto': t} for j, t in enumerate(opciones)],
                    correcta=correcta, explicacion=explicacion,
                )
            estado = 'creada' if creada else 'actualizada'
            self.stdout.write(self.style.SUCCESS(
                f'  {codigo}: {estado} con {prueba.total_preguntas} preguntas.'))

        self.stdout.write(self.style.SUCCESS('Listo.'))
        self.stdout.write('Rutas públicas:')
        for m in ('pre', 'post'):
            self.stdout.write(f'  /api/capacitacion/prueba/{PAREJA}-{m}/')
