# -*- coding: utf-8 -*-
"""Genera el cuestionario en limpio, sin respuestas, para revisión externa.

Lee las preguntas del mismo archivo que las carga en el servidor, de modo que el
documento no puede quedar desfasado de lo que responden los participantes. La
clave y las explicaciones no se leen siquiera: este documento se entrega a
personas que no deben conocerlas.

    python fuente/generar_cuestionario.py
"""
import ast
import html
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
FUENTE = RAIZ / 'srni-backend/apps/capacitacion/management/commands/cargar_prueba_capacitacion.py'
SALIDA = Path(__file__).resolve().parent.parent / 'cuestionario-sin-respuestas.html'
ESTILO = RAIZ / 'entregables/2026-09-08-auditoria-manuales/fuente/estilo-documento.css'
CLAVES = ['A', 'B', 'C', 'D']


def leer_preguntas():
    arbol = ast.parse(FUENTE.read_text(encoding='utf-8'))
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], 'id', '') == 'PREGUNTAS':
            # Solo enunciado y opciones: la correcta y la explicación se descartan aquí.
            return [(t[0], t[1]) for t in ast.literal_eval(nodo.value)]
    raise SystemExit('No se encontró la lista PREGUNTAS en el archivo de carga.')


def main():
    preguntas = leer_preguntas()
    css = ESTILO.read_text(encoding='utf-8')

    bloques = []
    for i, (enunciado, opciones) in enumerate(preguntas, start=1):
        ops = '\n'.join(
            f'      <li><span class="clave">{CLAVES[j]}</span>{html.escape(texto)}</li>'
            for j, texto in enumerate(opciones))
        bloques.append(
            f'  <div class="pregunta">\n'
            f'    <div class="num">{i}</div>\n'
            f'    <p class="enun">{html.escape(enunciado)}</p>\n'
            f'    <ol class="ops">\n{ops}\n    </ol>\n'
            f'  </div>')

    doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Cuestionario de la jornada — SICAV Móvil</title>
<style>
{css}
.pregunta{{display:grid;grid-template-columns:26px 1fr;gap:10px;margin:0 0 14px;
          break-inside:avoid;page-break-inside:avoid}}
.pregunta .num{{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--marca-ink);
                background:var(--panel);border-radius:4px;text-align:center;padding:3px 0;
                height:22px;line-height:16px}}
.pregunta .enun{{margin:2px 0 7px;font-size:12px;font-weight:600;color:var(--ink);line-height:1.45}}
.pregunta .enun{{grid-column:2}}
.ops{{grid-column:2;list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}}
.ops li{{font-size:11.4px;color:var(--ink-2);line-height:1.45;display:flex;gap:8px;
         align-items:baseline;border:1px solid var(--line);border-radius:5px;padding:5px 9px}}
.ops .clave{{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--marca-ink);
             flex:none;width:12px}}
</style>
</head>
<body>

<div class="marca-bar"></div>
<div class="cabecera">
  <div class="eyebrow">Subdirección Red Nacional de Información · UARIV</div>
  <h1>Cuestionario de la jornada<br>SICAV Móvil y Panel de Control</h1>
  <div class="sub">Diez preguntas · cinco minutos · sin respuestas</div>
  <div class="meta-portada">
    <div><b>Se aplica:</b> al comienzo (8:15 a.m.) y al cierre (11:00 a.m.)</div>
    <div><b>Formato:</b> selección múltiple, una sola respuesta</div>
    <div><b>Dónde se responde:</b> en línea, sin usuario ni contraseña</div>
    <div><b>Actualizado:</b> 8 de septiembre de 2026</div>
  </div>
</div>

<p class="lead">Es <b>el mismo cuestionario en los dos momentos</b>, a propósito: lo que
interesa no es el puntaje final aislado, sino la diferencia entre el antes y el después de
cada participante. Se responde en línea y el sistema califica solo; cada persona se
identifica con su correo institucional, que es lo que empareja las dos aplicaciones.</p>

<div class="nota"><b>Este documento no trae las respuestas.</b> La clave se conserva en el
servidor y en el repositorio del proyecto. Conviene además no difundirlo entre quienes vayan
a presentar la prueba: el pre-test solo mide algo si nadie lo ha visto antes de responderlo.</div>

{chr(10).join(bloques)}

<div class="pie">
  <span>Subdirección Red Nacional de Información · Unidad para las Víctimas</span>
  <span>Cuestionario pre-test y post-test · SICAV Móvil · 8-sep-2026</span>
</div>

</body>
</html>
"""
    SALIDA.write_text(doc, encoding='utf-8')
    print(f'{SALIDA.name}: {len(preguntas)} preguntas, sin respuestas')


if __name__ == '__main__':
    main()
