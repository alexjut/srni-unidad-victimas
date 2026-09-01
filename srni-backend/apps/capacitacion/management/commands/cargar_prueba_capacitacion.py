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

# (enunciado, [opciones], correcta, explicación)
#
# Tres criterios al escribirlas, aprendidos corrigiendo la primera versión:
#
# 1. La clave va repartida entre las cuatro letras (3 A · 4 B · 4 C · 4 D). En la
#    versión anterior once de quince eran B y ninguna era D: marcar «todo B» daba
#    11/15 y el instrumento no medía nada.
# 2. La opción correcta no puede ser sistemáticamente la más larga ni la única que
#    «suena a procedimiento». Antes lo era en las mismas once.
# 3. Los rótulos son los que el encuestador ve en pantalla, verificados contra el
#    código de la aplicación —«Registrar y caracterizar», «Alta manual», «✓ Al día»—
#    y no los nombres internos con que hablamos entre nosotros.
PREGUNTAS = [
    ("Para ingresar a SICAV Móvil se escribe:",
     ["Su número de cédula", "Su correo electrónico institucional",
      "Su código de usuario", "Su nombre completo"], "C",
     "Se ingresa con el código de usuario, que es como está rotulado el campo en la "
     "pantalla de ingreso. No es la cédula ni el correo."),

    ("La versión de la aplicación instalada se confirma:",
     ["En la pantalla de ingreso", "Únicamente desde la Play Store",
      "Llamando a soporte técnico", "No es posible confirmarla"], "A",
     "Aparece en la propia pantalla de ingreso. Inclúyala siempre que reporte una incidencia."),

    ("La regla de vigencia impide volver a caracterizar a una persona hasta que pasen, "
     "desde su última caracterización:",
     ["Seis meses", "Un año", "Cinco años", "Dos años"], "D",
     "Son dos años, contados desde la última caracterización. Es una regla de la entidad "
     "para no repetir el esfuerzo de campo."),

    ("Cuando una persona tiene ficha vigente y aun así debe caracterizarse, la excepción "
     "la autoriza:",
     ["El encuestador, con una foto del soporte",
      "El coordinador, de manera verbal en campo",
      "Un perfil con permiso de autorización, desde el panel",
      "El canal de soporte, por correo electrónico"], "C",
     "La autoriza la coordinación desde el Panel de Control. El encuestador no maneja el "
     "soporte documental: llega por canal institucional al nivel central."),

    ("Para registrar una excepción de vigencia, el panel exige:",
     ["Solo el número de documento", "Ruta, radicado y motivo",
      "Solo el archivo de soporte escaneado", "Radicado y autorización verbal"], "B",
     "Ruta, radicado y motivo son obligatorios; el archivo de soporte es opcional."),

    ("Una excepción de vigencia autorizada:",
     ["Es de un solo uso y se consume al terminar",
      "Queda activa de forma permanente para esa persona",
      "Se puede reutilizar en otro hogar", "Dura treinta días calendario"], "A",
     "Es de un solo uso. Si más adelante la misma persona requiere otra, hay que "
     "solicitarla de nuevo."),

    ("La información que permite trabajar sin señal se descarga al teléfono:",
     ["Al iniciar sesión, en la precarga de la jornada",
      "Cada vez que se abre un capítulo nuevo",
      "Solo cuando el encuestador la solicita",
      "Nunca: siempre se requiere conexión"], "A",
     "Se precarga al iniciar sesión. Por eso conviene entrar con señal antes de salir a campo."),

    ("Si se pierde la señal a mitad de una caracterización:",
     ["Se pierde lo diligenciado y se empieza de nuevo",
      "Se puede continuar; lo capturado queda en la cola",
      "La aplicación se cierra automáticamente",
      "Hay que llamar a soporte antes de continuar"], "B",
     "Puede continuar. Lo capturado queda en la cola y sube cuando vuelve la señal."),

    ("Una caracterización quedó efectivamente entregada al sistema cuando:",
     ["Se respondió el último capítulo", "Apareció el mensaje de guardado",
      "El indicador de sincronización muestra «✓ Al día»",
      "Se cerró la aplicación"], "C",
     "Responder el último capítulo no basta: hasta que el indicador no diga «✓ Al día», "
     "la información sigue solo en el teléfono."),

    ("El instrumento territorial vigente (V8) está organizado en:",
     ["5 capítulos", "9 capítulos", "21 capítulos", "14 capítulos"], "D",
     "Son 14 capítulos y 363 preguntas."),

    ("Una pregunta de nivel PERSONA:",
     ["Se responde una sola vez para todo el hogar",
      "Se responde una vez por cada integrante del hogar",
      "Solo la responde el jefe de hogar",
      "Se responde una vez por cada hogar visitado"], "B",
     "Se responde por cada integrante. En un hogar de tres personas, un capítulo con ocho "
     "preguntas de nivel persona genera 24 respuestas."),

    ("La lógica de saltos del formulario hace que:",
     ["El encuestador pueda omitir cualquier pregunta",
      "El formulario avance automáticamente cada cinco minutos",
      "El capítulo se repita cuando hay un error",
      "Algunas preguntas se muestren u oculten según lo respondido"], "D",
     "Si falta una pregunta que esperaba ver, lo más probable es que una regla la esté "
     "ocultando: revise lo respondido antes de reportarlo."),

    ("Si la persona no aparece en la búsqueda, en la tarjeta gris se usa:",
     ["El documento de un familiar cercano",
      "El botón «Registrar y caracterizar»",
      "El campo de documento en blanco",
      "Ninguna: no se la puede caracterizar"], "B",
     "«Registrar y caracterizar» abre el formulario «Alta manual»: nombres, apellidos, "
     "fecha de nacimiento y género. Nunca use el documento de otra persona."),

    ("El tratamiento de los datos personales que se capturan se rige por:",
     ["La Ley 1448 de 2011, únicamente", "El Decreto 1084 de 2015",
      "La Ley 1581 de 2012, de protección de datos",
      "Ninguna norma específica"], "C",
     "Ley 1581 de 2012. Por eso los reportes de incidencia no deben incluir datos de la "
     "persona entrevistada."),

    ("Frente a un comportamiento inesperado de la aplicación:",
     ["Se desinstala y se reinstala sin avisar",
      "Se continúa y no se menciona",
      "Se le presta el celular a un compañero",
      "Se reporta indicando versión, pantalla y pasos previos"], "D",
     "Un reporte sirve si permite reproducir el problema: versión, pantalla, pasos previos "
     "y qué se esperaba que pasara."),
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
