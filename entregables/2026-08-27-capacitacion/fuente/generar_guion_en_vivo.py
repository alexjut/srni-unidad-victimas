# -*- coding: utf-8 -*-
"""Genera los dos documentos de la práctica en vivo de la jornada.

    guion-casos-en-vivo.html    el paso a paso de los tres casos, para conducir
    usuarios-y-cedulas.html     los 37 participantes con SUS cédulas de práctica

─── Por qué se generan y no se escriben a mano ──────────────────────────────
Las cédulas salen del MISMO CSV que se le entrega a cada participante
(`credenciales_capacitacion.csv`, que a su vez lo escribe
`preparar_capacitacion`). Un documento tecleado a mano se desvía del dato el día
que alguien vuelva a preparar una jornada, y el participante se queda buscando
una cédula que no existe mientras 36 personas esperan.

El estilo se toma de `anexos_capacitacion.html` en vez de duplicarse: es un solo
sitio donde cambiar la identidad visual, y estos documentos salen idénticos a los
que ya aprobó la Dirección técnica.

─── Sin claves ──────────────────────────────────────────────────────────────
Ninguno de los dos lleva contraseñas. La credencial de cada persona viaja en su
propio correo; un documento que se proyecta en una sala y se imprime no es donde
van 37 claves.

    python fuente/generar_guion_en_vivo.py
"""
import csv
import html
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ENTREGABLE = AQUI.parent
RAIZ = ENTREGABLE.parent.parent
CREDENCIALES = RAIZ / 'credenciales_capacitacion.csv'
ESTILO_DE = AQUI / 'anexos_capacitacion.html'

FECHAS = {
    '1': ('martes 15 de septiembre', 'Equipo SRNI', 'híbrida · 15 puestos presenciales'),
    '2': ('jueves 24 de septiembre', 'Enlaces territoriales — Grupo A', 'virtual'),
    '3': ('martes 29 de septiembre', 'Enlaces territoriales — Grupo B', 'virtual'),
}


def estilo():
    """El bloque `<style>` de los anexos, para que los tres documentos sean uno."""
    texto = ESTILO_DE.read_text(encoding='utf-8')
    m = re.search(r'(<link rel="preconnect".*?</style>)', texto, re.S)
    if not m:
        raise SystemExit('No se encontró el bloque de estilo en anexos_capacitacion.html')
    return m.group(1)


def leer():
    with open(CREDENCIALES, encoding='utf-8-sig', newline='') as f:
        filas = list(csv.DictReader(f))
    if not filas:
        raise SystemExit(f'{CREDENCIALES} está vacío')
    return filas


def e(x):
    return html.escape(str(x or ''))


def cabecera(titulo, sub, meta):
    filas_meta = '\n'.join(
        f'  <div><b>{e(k)}:</b> {v}</div>' for k, v in meta.items())
    return f"""<meta charset="utf-8">
<title>{e(titulo)} — SICAV Móvil</title>
{estilo()}

<div class="hoja">

<div class="marca-bar"></div>
<div class="cabecera">
  <p class="eyebrow">Subdirección Red Nacional de Información — Unidad para las Víctimas (UARIV)</p>
  <h1>{e(titulo)}</h1>
  <p class="sub">{sub}</p>
  <div class="meta-portada">
{filas_meta}
  </div>
</div>
"""


PIE = """
<div class="firma">
  Generado por <code>fuente/generar_guion_en_vivo.py</code> desde
  <code>credenciales_capacitacion.csv</code>. Si se vuelve a preparar una jornada
  con <code>preparar_capacitacion</code>, hay que regenerar estos dos documentos.
</div>

</div>
"""


# ══════════════════════════════════════════════════════════════════════════════
# 1. El guion de los casos en vivo
# ══════════════════════════════════════════════════════════════════════════════

def guion(filas):
    total = len(filas)
    partes = [cabecera(
        'Guion de los casos en vivo',
        'Qué hace cada participante, con qué cédula, y qué tiene que pasar en pantalla',
        {
            'Jornadas': '15, 24 y 29 de septiembre de 2026 · 8:00 a.m. – 12:00 m.',
            'Bloque': 'A — Aplicación móvil (SICAV Móvil)',
            'Participantes': f'{total} en tres sesiones',
            'Versión de la APK': '1.2.5 (versionCode 59)',
            'Conduce': 'Javier Alexander Aguilar Castro',
            'Calidad e incidencias': 'Jorge Cardona Gregory',
        })]

    partes.append("""
<div class="caja alerta">
  <p><b>Antes de empezar, y no es opcional: cerrar sesión y volver a entrar, con
  señal.</b></p>
  <p>Es al ingresar cuando el teléfono descarga la información del padrón que
  después usa <b>sin conexión</b>, y de ella depende lo que la aplicación permita
  hacer en campo. Un celular que conserva la sesión de días anteriores va a decir
  «No habilitado» sobre una persona que <b>sí</b> se puede caracterizar, y eso se
  va a reportar como falla cuando no lo es.</p>
  <p class="nota">Lo mismo aplica a quien venía con la 1.2.4 y actualice hoy: la
  actualización no rehace la precarga; el ingreso sí.</p>
</div>

<h2><span class="n">1</span> Cómo leer las cédulas de este guion</h2>

<p class="lead">Cada participante practica sobre <b>sus propias</b> cinco personas,
para que dos personas no se pisen el mismo hogar. En este guion se escriben como
<code>999NN0000X</code>, donde <code>NN</code> es el número del participante.</p>

<p>Su <code>NN</code> está en el documento <b>Usuarios y cédulas de práctica</b>,
o en el correo con su credencial. Por ejemplo, si le corresponde el
<code>99903</code>, su caso 2 es la cédula <code>9990300001</code>.</p>

<table>
  <thead><tr><th>Cédula</th><th>Quién es</th><th>Para qué caso</th><th>Cómo llega</th></tr></thead>
  <tbody>
    <tr><td><code>999NN00001</code></td><td>ANA PRÁCTICA</td><td><b>Caso 2</b> — la que se recaracteriza</td>
        <td>Ya caracterizada hace 8 meses, con hogar y familia</td></tr>
    <tr><td><code>999NN00002</code></td><td>MARÍA PRÁCTICA</td><td><b>Caso 2</b> — la que se retira del hogar</td>
        <td>Integrante del mismo hogar</td></tr>
    <tr><td><code>999NN00003</code></td><td>ROSA PRÁCTICA, 38</td><td><b>Caso 1</b> — la señora que recibe</td>
        <td>Sin caracterización previa</td></tr>
    <tr><td><code>999NN00004</code></td><td>JUAN PRÁCTICA, 14</td><td><b>Caso 1</b> — el hijo</td>
        <td>Sin caracterización previa</td></tr>
    <tr><td><code>999NN00005</code></td><td>CARMEN PRÁCTICA, 71</td><td><b>Caso 1</b> — la madre</td>
        <td>Sin caracterización previa</td></tr>
    <tr><td><code>999NN00009</code></td><td>—</td><td><b>Caso 3</b> — la que no aparece</td>
        <td><b>No existe a propósito.</b> Es el alta manual</td></tr>
  </tbody>
</table>

<div class="caja ok">
  <p><b>Las 222 cédulas están verificadas contra producción</b> el 11 de septiembre
  de 2026, una por una, por el mismo endpoint que usa la aplicación: cada una
  responde lo que su caso necesita. Si alguna no se comporta así el día de la
  jornada, no es del escenario: repórtelo.</p>
</div>

<h2 class="salto"><span class="n">2</span> Caso 1 — Hogar completo, y sin conexión</h2>
<div class="caja">
  <p><b>La situación que se cuenta en voz alta.</b> Llega una señora de 38 años con
  su hijo de 14 y su madre de 71. Ninguno ha sido caracterizado. A mitad de la
  entrevista se cae la señal.</p>
  <p><b>Lo que hace el participante</b></p>
  <ol>
    <li>Busca la <code>999NN00003</code>. Sale en verde: <b>habilitada</b>.</li>
    <li>Conforma el hogar y agrega al hijo <code>999NN00004</code> y a la madre
      <code>999NN00005</code>.</li>
    <li>Elige el instrumento y empieza a diligenciar.</li>
    <li><b>Activa el modo avión</b> y sigue respondiendo. La aplicación no se detiene.</li>
    <li>Vuelve a encender los datos y espera a que la cola quede en cero.</li>
  </ol>
  <p><b>Se considera resuelto si:</b> la caracterización aparece sincronizada, con
  los tres integrantes y el avance al 100&nbsp;%, y el indicador dice
  <b>«✓ Al día»</b>.</p>
  <p class="nota">Lo que se está enseñando: que el trabajo no se pierde sin señal, y
  que la jornada no se cierra hasta que la cola esté en cero.</p>
</div>

<h2><span class="n">3</span> Caso 2 — Persona ya caracterizada, y una familia que cambió</h2>

<div class="caja azul">
  <p><b>Esto es lo nuevo del 11 de septiembre de 2026, y es el caso que hay que
  entender bien.</b> Antes, una persona caracterizada hace menos de dos años quedaba
  bloqueada y había que pedir una autorización a coordinación. <b>Eso desapareció.</b>
  La aplicación avisa y deja continuar; no hay nada que pedirle a nadie.</p>
</div>

<div class="caja">
  <p><b>La situación.</b> Una señora fue caracterizada hace ocho meses y ya tiene un
  hogar registrado con su familia. Hoy hay que actualizarle la caracterización.
  Además, un integrante del hogar <b>falleció en marzo</b>.</p>
  <p><b>Lo que hace el participante</b></p>
  <ol>
    <li>Busca la <code>999NN00001</code>. La aplicación <b>avisa que ya fue
      caracterizada</b> y la deja continuar. <b>No se pide autorización.</b></li>
    <li>Conforma el hogar: aparece <b>el hogar que ya existía, con su familia</b>.
      <b>No vuelve a capturar a nadie.</b> Si lo hace, cada persona queda dos veces.</li>
    <li>Entra al hogar y usa <b>«Retirar del hogar»</b> en la
      <code>999NN00002</code>. Indica el motivo <b>Falleció</b> y la fecha
      <b>del hecho</b>: marzo, no hoy.</li>
    <li>Diligencia la caracterización y la cierra.</li>
    <li>Con el Panel de Control abierto, entra a <b>Recaracterizaciones</b> y
      encuentra el registro que <b>el sistema escribió solo</b>.</li>
  </ol>
  <p><b>Se considera resuelto si:</b> completó la caracterización sin detenerse ni
  pedir permiso; el integrante quedó <b>retirado y no borrado</b>, con su fecha; los
  demás no se duplicaron; y en el panel está la fila con quién, cuándo y con cuánta
  anticipación, sin que el participante hiciera nada para crearla.</p>
  <p><b>Las tres preguntas de cierre.</b> Si nadie autoriza nada, ¿cómo responde la
  entidad el día que control interno pregunte por qué una ficha se reescribió a los
  ocho meses? ¿Por qué la fecha del retiro es la del fallecimiento y no la de hoy?
  ¿Qué pasa con la caracterización anterior cuando se retira a un integrante?</p>
</div>

<div class="caja">
  <p><b>Variante, una sola vez y en plenaria.</b> El facilitador muestra con dos
  cuentas el caso del hogar conformado por <b>otro</b> encuestador: también se puede
  continuar, sin pedirle reasignación a nadie. No se le pone a cada participante a
  propósito — si esa ruta fallara, 37 personas quedarían trabadas a la vez en lugar
  de una demostración.</p>
</div>

<h2><span class="n">4</span> Caso 3 — La persona que no aparece, y una incidencia</h2>
<div class="caja">
  <p><b>La situación.</b> Llega un señor que dice estar en el RUV. Al buscarlo, no
  aparece en el padrón.</p>
  <p><b>Lo que hace el participante</b></p>
  <ol>
    <li>Busca la <code>999NN00009</code>. Sale la tarjeta gris: <b>no está en el
      padrón</b>. No es un error y no significa que no sea víctima.</li>
    <li>Usa <b>«Registrar y caracterizar»</b> y diligencia el alta manual.</li>
    <li>Continúa con la conformación del hogar y la caracterización.</li>
    <li>Redacta un reporte de incidencia <b>sin datos de la persona</b>
      (Ley 1581 de 2012) y lo comparte con el grupo.</li>
  </ol>
  <p><b>Se considera resuelto si:</b> pudo caracterizar a quien no estaba en el
  padrón, y el reporte permite reproducir lo que vio sin exponer a nadie.</p>
  <p class="nota">Si cierra sesión a mitad del alta y vuelve a buscar el mismo
  documento <b>sin señal</b>, la aplicación debe encontrar a quien ya registró en ese
  teléfono y no pedirle capturarla de nuevo. Se corrigió en la 1.2.5.</p>
</div>

<h2 class="salto"><span class="n">5</span> Lo que se va a reportar como falla y no lo es</h2>
<table>
  <thead><tr><th>Lo que verá</th><th>Qué es</th><th>Qué hacer</th></tr></thead>
  <tbody>
    <tr><td>Dice «No habilitado — ficha vigente»</td>
        <td>El teléfono trae información del padrón de días anteriores</td>
        <td><b>Cerrar sesión y volver a entrar con señal</b></td></tr>
    <tr><td>El hogar ya tiene integrantes que el participante no capturó</td>
        <td>Es el hogar que la familia ya tenía registrado</td>
        <td>Es correcto. <b>No capturarlos de nuevo</b></td></tr>
    <tr><td>No deja borrar a un integrante ya reportado</td>
        <td>Borrarlo cambiaría un dato ya entregado</td>
        <td>Usar <b>«Retirar del hogar»</b></td></tr>
    <tr><td>Una pregunta que esperaba no aparece</td>
        <td>Una regla del formulario la oculta porque no aplica</td>
        <td>Revisar las respuestas anteriores del capítulo</td></tr>
    <tr><td>El capítulo dice «Faltan N» después de responder</td>
        <td>Hay obligatorias por <b>cada</b> integrante</td>
        <td>Revisar la sección de cada persona</td></tr>
    <tr><td>En el panel, «Autorizaciones» no deja autorizar</td>
        <td>El control de vigencia está retirado: no hay nada que autorizar</td>
        <td>Es correcto. Quedó como consulta del histórico</td></tr>
  </tbody>
</table>

<div class="caja alerta">
  <p><b>Lo único que sí es una falla</b> y hay que reportar de inmediato: que la
  aplicación <b>detenga</b> a alguien por tener una caracterización vigente después
  de haber cerrado sesión y vuelto a entrar con señal.</p>
</div>
""")
    partes.append(PIE)
    return ''.join(partes)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Los usuarios y sus cédulas
# ══════════════════════════════════════════════════════════════════════════════

def usuarios(filas):
    total = len(filas)
    partes = [cabecera(
        'Usuarios y cédulas de práctica',
        'Quién hace las entrevistas de la práctica, y sobre qué personas',
        {
            'Participantes': f'{total} en tres sesiones',
            'Cuentas': 'el usuario institucional de cada quien · perfil COORDINADOR',
            'Verificado contra producción': '11 de septiembre de 2026 · 222 cédulas',
            'Documento hermano': 'Guion de los casos en vivo',
        })]

    partes.append("""
<div class="caja alerta">
  <p><b>Este documento no lleva contraseñas, a propósito.</b> La credencial de cada
  persona viaja en su propio correo. Un documento que se proyecta en una sala y se
  imprime no es donde van 37 claves.</p>
</div>

<div class="caja">
  <p><b>Se entra con el usuario institucional</b>, el mismo de la entidad —no la
  cédula, no el correo completo, no el nombre—. El campo está rotulado «Código de
  usuario», pero lo que va allí es ese usuario.</p>
  <p><b>Todos tienen perfil COORDINADOR</b>, que es el único que cubre la jornada
  entera: caracteriza en la aplicación y ve supervisión, reportes, auditoría y
  recaracterizaciones en el panel.</p>
</div>
""")

    for sesion in ('1', '2', '3'):
        delsesion = [f for f in filas if f['sesion'] == sesion]
        if not delsesion:
            continue
        fecha, grupo, modalidad = FECHAS[sesion]
        partes.append(
            f'\n<h2 class="salto"><span class="n">{sesion}</span> Sesión {sesion} — '
            f'{e(fecha)}</h2>\n'
            f'<p class="lead">{e(grupo)} · {e(modalidad)} · '
            f'<b>{len(delsesion)} participantes</b></p>\n')
        partes.append(
            '<table>\n  <thead><tr>'
            '<th>Usuario</th><th>Nombre</th><th>Dirección Territorial</th>'
            '<th>Caso 2<br><span class="nota">se recaracteriza</span></th>'
            '<th>Caso 2<br><span class="nota">se retira</span></th>'
            '<th>Caso 1<br><span class="nota">titular · hijo · madre</span></th>'
            '<th>Caso 3<br><span class="nota">no existe</span></th>'
            '</tr></thead>\n  <tbody>\n')
        for f in delsesion:
            caso1 = (f"{e(f['doc_caso1'])}<br>{e(f['doc_caso1_hijo'])}"
                     f"<br>{e(f['doc_caso1_madre'])}")
            partes.append(
                f"    <tr><td><code>{e(f['codigo'])}</code></td>"
                f"<td>{e(f['nombre'])}</td>"
                f"<td>{e(f['dt'])}</td>"
                f"<td><code>{e(f['doc_caso2'])}</code></td>"
                f"<td><code>{e(f['doc_caso2_miembro'])}</code></td>"
                f"<td class='nota'>{caso1}</td>"
                f"<td><code>{e(f['doc_caso3'])}</code></td></tr>\n")
        partes.append('  </tbody>\n</table>\n')

    partes.append("""
<h2 class="salto"><span class="n">4</span> Si hay que volver a preparar el escenario</h2>
<div class="caja">
  <p>Entre una jornada y la siguiente alguien va a pedir «vuélvanlo a dejar como
  estaba». Se hace con un comando, y es idempotente:</p>
  <p><code>python manage.py preparar_capacitacion --confirmar --sesion N --conservar-claves</code></p>
  <p>Devuelve la fecha de caracterización a ocho meses atrás y deja el hogar como el
  Caso 2 lo necesita. <b>Con <code>--conservar-claves</code> nadie pierde su
  contraseña.</b></p>
  <p class="nota">Si se omite esa bandera, se emiten claves nuevas y hay que volver a
  repartirlas. Las claves no se pueden re-exportar: quedan cifradas en la base.</p>
</div>

<div class="caja alerta">
  <p><b>Lo que hay que revisar antes de cada jornada:</b> que nadie haya quedado
  <b>retirado</b> del hogar de una práctica anterior. Si el integrante
  <code>999NN00002</code> ya está retirado, ese participante no tendrá a quién
  retirar y su Caso 2 queda a medias. Se deshace desde la aplicación con
  <b>«Deshacer retiro»</b>.</p>
</div>
""")
    partes.append(PIE)
    return ''.join(partes)


def main():
    filas = leer()

    for nombre, contenido in (
        ('guion-casos-en-vivo.html', guion(filas)),
        ('usuarios-y-cedulas.html', usuarios(filas)),
    ):
        destino = ENTREGABLE / nombre
        destino.write_text(contenido, encoding='utf-8')
        print(f'{nombre}: {len(contenido):,} bytes')

    print(f'{len(filas)} participantes · sin contraseñas')


if __name__ == '__main__':
    main()
