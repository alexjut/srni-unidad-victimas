"""
Carga el pre-test y el post-test de la capacitación de septiembre de 2026.

Diez preguntas de selección múltiple, verificadas contra el sistema real: la regla
de vigencia de dos años, quién autoriza la excepción, la precarga de la jornada,
la cola de sincronización y los niveles hogar y persona.

Pre y post comparten el mismo cuestionario a propósito: aplicar el mismo
instrumento en los dos momentos es lo que permite medir la ganancia por persona.
Si se cambia uno hay que cambiar el otro, o la medición deja de significar nada.

    python manage.py cargar_prueba_capacitacion
    python manage.py cargar_prueba_capacitacion --reemplazar
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.capacitacion.models import PreguntaPrueba, Prueba

PAREJA = 'capacitacion-2026-09'

# (enunciado, [opciones], correcta, explicación)
#
# Cuatro criterios al escribirlas, los tres primeros aprendidos corrigiendo la
# primera versión y el cuarto pedido por la Subdirección:
#
# 1. La clave va repartida entre las cuatro letras (3 A · 3 B · 2 C · 2 D). En la
#    primera versión once de quince eran B y ninguna era D: marcar «todo B» daba
#    11/15 y el instrumento no medía nada. Con diez preguntas, la letra que más se
#    repite da 3/10 — responder a ciegas no aprueba.
# 2. La opción correcta no puede ser sistemáticamente la más larga ni la única que
#    «suena a procedimiento». Es la misma fuga por otra vía: en el primer borrador
#    de estas diez, la correcta era la más larga en 7 de 10 —marcar «la más larga»
#    daba 7/10, tan regalado como el «todo B» de antes—. Los distractores se
#    alargaron hasta que la correcta no es la más larga en ninguna de las diez.
# 3. Los rótulos son los que el encuestador ve en pantalla, verificados contra el
#    código de la aplicación —«Registrar y caracterizar», «✓ Al día»— y no los
#    nombres internos con que hablamos entre nosotros.
# 4. Diez preguntas, no quince: la jornada pide un instrumento de cinco minutos.
#    Se conservaron las que cambian lo que el encuestador HACE en campo y se
#    dejaron fuera las de dato memorístico o de procedimiento del panel. Las cinco
#    retiradas siguen en el banco del Anexo B para refuerzo.
PREGUNTAS = [
    ("Para ingresar a SICAV Móvil se escribe:",
     ["Su código de usuario", "Su número de cédula",
      "Su correo electrónico institucional", "Su nombre completo"], "A",
     "Se ingresa con el código de usuario, que es como está rotulado el campo en la "
     "pantalla de ingreso. No es la cédula ni el correo."),

    ("La regla de vigencia impide volver a caracterizar a una persona hasta que pasen, "
     "desde su última caracterización:",
     ["Seis meses", "Un año", "Cinco años", "Dos años"], "D",
     "Son dos años, contados desde la última caracterización. Es una regla de la entidad "
     "para no repetir el esfuerzo de campo."),

    ("Cuando una persona tiene ficha vigente y aun así debe caracterizarse, la excepción "
     "la autoriza:",
     ["El encuestador, adjuntando una foto del soporte en la aplicación",
      "El coordinador de la jornada, de manera verbal en campo",
      "Un perfil con permiso de autorización, desde el panel",
      "El canal de soporte institucional, por correo electrónico"], "C",
     "La autoriza la coordinación desde el Panel de Control. El encuestador no maneja el "
     "soporte documental: llega por canal institucional al nivel central."),

    ("La información que permite trabajar sin señal se descarga al teléfono:",
     ["Cada vez que se abre un capítulo nuevo del instrumento",
      "Al iniciar sesión, en la precarga de la jornada",
      "Solo cuando el encuestador la solicita desde el menú",
      "Nunca: siempre se requiere conexión"], "B",
     "Se precarga al iniciar sesión. Por eso conviene entrar con señal antes de salir a campo."),

    ("Si se pierde la señal a mitad de una caracterización:",
     ["Se puede continuar; lo capturado queda en la cola",
      "Se pierde lo diligenciado y hay que empezar la caracterización de nuevo",
      "La aplicación se cierra automáticamente",
      "Hay que llamar a soporte antes de continuar"], "A",
     "Puede continuar. Lo capturado queda en la cola y sube cuando vuelve la señal."),

    ("Una caracterización quedó efectivamente entregada al sistema cuando:",
     ["Se respondió el último capítulo del instrumento",
      "Apareció el mensaje de guardado al terminar el último capítulo",
      "El indicador de sincronización muestra «✓ Al día»",
      "Se cerró la aplicación"], "C",
     "Responder el último capítulo no basta: hasta que el indicador no diga «✓ Al día», "
     "la información sigue solo en el teléfono."),

    ("Una pregunta de nivel PERSONA:",
     ["Se responde una sola vez para todo el hogar, sin importar cuántos sean",
      "Se responde una vez por cada integrante del hogar",
      "Solo la responde la persona reconocida como jefe de hogar",
      "Se responde una vez por cada hogar visitado"], "B",
     "Se responde por cada integrante. En un hogar de tres personas, un capítulo con ocho "
     "preguntas de nivel persona genera 24 respuestas."),

    ("La lógica de saltos del formulario hace que:",
     ["El encuestador pueda omitir cualquier pregunta que no le aplique",
      "El formulario avance automáticamente cada cinco minutos",
      "El capítulo se repita desde el principio cuando hay un error",
      "Algunas preguntas se muestren u oculten según lo respondido"], "D",
     "Si falta una pregunta que esperaba ver, lo más probable es que una regla la esté "
     "ocultando: revise lo respondido antes de reportarlo."),

    ("Si la persona no aparece en la búsqueda, en la tarjeta gris se usa:",
     ["El botón «Registrar y caracterizar»",
      "El documento de un familiar cercano",
      "El campo de documento en blanco",
      "Ninguna: no se la puede caracterizar"], "A",
     "«Registrar y caracterizar» abre el formulario de alta manual: nombres, apellidos, "
     "fecha de nacimiento y género. Nunca use el documento de otra persona."),

    ("El tratamiento de los datos personales que se capturan se rige por:",
     ["El Decreto 1084 de 2015, como único reglamento aplicable",
      "La Ley 1581 de 2012, de protección de datos",
      "La Ley 1448 de 2011, únicamente",
      "Ninguna norma específica"], "B",
     "Ley 1581 de 2012. Por eso los reportes de incidencia no deben incluir datos de la "
     "persona entrevistada."),
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
                        'Diez preguntas de selección múltiple, unos cinco minutos. Se responde '
                        'una sola vez. Al terminar verá su resultado y en qué falló.'),
                    'momento': momento,
                    'pareja': PAREJA,
                },
            )
            if opts['reemplazar']:
                prueba.preguntas.all().delete()
                # La descripción también cambió al pasar de quince preguntas a diez;
                # sin esto, una prueba ya creada seguiría anunciando el texto viejo.
                prueba.descripcion = (
                    'Diez preguntas de selección múltiple, unos cinco minutos. Se responde '
                    'una sola vez. Al terminar verá su resultado y en qué falló.')
                prueba.save(update_fields=['descripcion'])

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
