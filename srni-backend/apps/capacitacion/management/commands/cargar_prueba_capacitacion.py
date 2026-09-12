"""
Carga el pre-test y el post-test de la capacitación de septiembre de 2026.

Trece preguntas de selección múltiple, verificadas contra el sistema real: la regla
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
#    11/15 y el instrumento no medía nada. Con trece preguntas, la letra que más se
#    repite da 3/10 — responder a ciegas no aprueba.
# 2. La opción correcta no puede ser sistemáticamente la más larga ni la única que
#    «suena a procedimiento». Es la misma fuga por otra vía: en el primer borrador
#    de estas diez, la correcta era la más larga en 7 de 10 —marcar «la más larga»
#    daba 7/10, tan regalado como el «todo B» de antes—. Los distractores se
#    alargaron hasta que la correcta no es la más larga en ninguna de las diez.
# 3. Los rótulos son los que el encuestador ve en pantalla, verificados contra el
#    código de la aplicación —«Registrar y caracterizar», «✓ Al día»— y no los
#    nombres internos con que hablamos entre nosotros.
# 4. Trece preguntas: quince medían mal, diez dejaron fuera el régimen nuevo.
#    Se conservaron las que cambian lo que el encuestador HACE en campo y se
#    dejaron fuera las de dato memorístico o de procedimiento del panel. Las cinco
#    retiradas siguen en el banco del Anexo B para refuerzo.
#
# 3. 11-sep-2026 — de 10 a TRECE, por el retiro del control de vigencia. Dos se
#    reescribieron (la del plazo y la del trámite de autorización, cuya respuesta
#    correcta describía un permiso que ya nadie otorga) y se agregaron tres del
#    régimen nuevo, por el mismo criterio: la familia que ya está registrada, el
#    retiro de un integrante, y la fecha del hecho.
#
#    Trece a media hora de reloj siguen siendo cinco minutos largos, y el bloque
#    del pre-test tiene quince en la agenda. Preferimos ampliar a recortar
#    cobertura: las tres nuevas son las únicas que miden lo que el encuestador va
#    a hacer distinto a partir de la jornada.
PREGUNTAS = [
    # El proyecto no reparte códigos propios: cada persona entra con el usuario que
    # ya tiene en la entidad. La versión anterior de esta pregunta daba por correcta
    # «su código de usuario», que mandaba a los participantes a buscar una
    # credencial que nadie les iba a entregar.
    ("En la pantalla de ingreso de SICAV Móvil, lo que usted escribe en el primer campo es:",
     ["Su usuario institucional, el mismo de la entidad", "Su número de cédula",
      "Su correo institucional completo, con @unidadvictimas.gov.co",
      "Su nombre completo, como aparece en la cédula"], "A",
     "Se ingresa con el usuario institucional —el mismo de la entidad, sin el "
     "@unidadvictimas.gov.co—. El campo está rotulado «Código de usuario», pero lo que "
     "va allí es ese usuario: no es la cédula, ni el correo completo, ni el nombre."),

    ("Una caracterización se considera VIGENTE mientras no hayan pasado, desde que "
     "se hizo:",
     ["Seis meses", "Un año", "Cinco años", "Dos años"], "D",
     "Dos años. Hoy el sistema no bloquea a nadie por eso: la persona se caracteriza "
     "igual. Pero es el plazo que define qué cuenta como caracterización vigente, y por "
     "tanto cuáles quedan registradas como actualización anticipada."),

    ("Usted busca a una persona y la aplicación le avisa que ya fue caracterizada hace "
     "ocho meses. ¿Qué hace?",
     ["Continuar con la caracterización: el sistema no lo detiene",
      "Reportarlo a su coordinación y esperar una autorización",
      "Adjuntar una foto del soporte antes de continuar",
      "Escribir al canal de soporte institucional"], "A",
     "Se continúa. Desde septiembre de 2026 no hace falta autorización, ni radicado, ni "
     "soporte: la persona se caracteriza cuando la operación lo necesite. El sistema "
     "registra solo, al cerrar la encuesta, que la actualización se hizo sobre una ficha "
     "que aún estaba vigente; el encuestador no interviene en eso ni debe hacer nada más."),

    # Las tres siguientes son del régimen que entró el 11-sep-2026, y entran por
    # el mismo criterio con el que se eligieron las demás: cambian lo que el
    # encuestador HACE en campo. Equivocarse en cualquiera de ellas tiene
    # consecuencia sobre el dato, no sobre el examen:
    #   · recapturar a la familia duplica a cada persona del hogar;
    #   · borrar en vez de retirar altera una caracterización ya entregada;
    #   · poner la fecha de hoy hace decir al sistema que la persona pertenecía
    #     al hogar cuando ya no era cierto.
    ("Al actualizar la caracterización de una familia que ya estaba registrada, el "
     "hogar aparece con los integrantes que otro encuestador capturó antes. ¿Qué hace "
     "con ellos?",
     ["Los captura otra vez, para asegurarse de que los datos estén frescos",
      "Crea un hogar nuevo para no mezclar la información",
      "Los deja como están y solo agrega o retira lo que cambió",
      "Los borra y vuelve a armar el hogar desde cero"], "C",
     "Se dejan. Volver a capturarlos deja a cada persona DOS veces en el hogar —el "
     "sistema no lo impide— y después hay que depurarlo a mano. El hogar es de la "
     "familia, no de quien lo creó."),

    ("Una señora del hogar falleció y usted está actualizando la caracterización. ¿Qué "
     "hace en la aplicación?",
     ["La borra del hogar",
      "La deja como está y lo anota en observaciones",
      "Reporta el caso a soporte para que la quiten",
      "La retira del hogar, indicando el motivo y la fecha"], "D",
     "Se usa «Retirar del hogar». Retirar NO es borrar: la persona sigue registrada y "
     "queda anotado que desde esa fecha ya no pertenece al hogar, así que la "
     "caracterización anterior —donde sí estaba— sigue siendo válida. Borrar a alguien "
     "ya reportado cambiaría un dato que la entidad ya entregó, y el sistema lo impide."),

    ("Al retirar del hogar a una persona que falleció en marzo, y usted se está "
     "enterando hoy, la fecha que registra es:",
     ["La de hoy, que es cuando usted lo registra",
      "La de marzo, cuando ocurrió el hecho",
      "La de la caracterización anterior",
      "No se pide fecha"], "B",
     "La del hecho: marzo. Es la fecha que permite saber que en la caracterización "
     "anterior la persona sí pertenecía al hogar. Con la de hoy, el sistema diría que "
     "pertenecía hasta ahora, y eso es falso. Pregúntesela a la familia."),

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

    # Antes se preguntaba «la lógica de saltos del formulario hace que…», con la
    # respuesta redactada en el mismo lenguaje técnico del enunciado. Se cambió por
    # la situación concreta en que el encuestador se topa con esto en campo.
    ("Está respondiendo un capítulo y una pregunta que esperaba ver no aparece. "
     "Lo más probable es que:",
     ["La aplicación tenga un error y convenga reinstalarla",
      "Esa pregunta aparezca al final, en un capítulo aparte",
      "Se haya perdido la conexión y por eso esa pregunta no alcanzó a cargar",
      "No aplique para esta persona, según lo que usted ya respondió"], "D",
     "El formulario muestra u oculta preguntas según lo que usted ya respondió. Si falta "
     "una que esperaba ver, revise sus respuestas anteriores antes de reportarlo."),

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
                        'Trece preguntas de selección múltiple, unos cinco minutos. Se responde '
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
                    'Trece preguntas de selección múltiple, unos cinco minutos. Se responde '
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
