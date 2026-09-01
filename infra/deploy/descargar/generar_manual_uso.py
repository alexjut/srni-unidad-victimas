# -*- coding: utf-8 -*-
"""
Genera infra/deploy/descargar/manual-uso.html desde el markdown del Manual de Uso.

Reutiliza el sistema visual del Manual Funcional ya publicado para que los dos
documentos se vean como parte de la misma casa.

Detalle que importa: el markdown viene con saltos de línea duros, así que primero
se unen las líneas continuadas de cada bloque. Sin ese paso, una negrita que cruza
dos líneas no se convierte y las continuaciones de un ítem salen como párrafo suelto.
"""
import io
import os
import re
import html

BASE = r'D:\desarrollo\unidad-victima'
SRC = os.path.join(BASE, 'docs', 'publicacion', 'manual-de-uso-srni-mobile.md')
FUNC = os.path.join(BASE, 'infra', 'deploy', 'descargar', 'manual.html')
DST = os.path.join(BASE, 'infra', 'deploy', 'descargar', 'manual-uso.html')

md = io.open(SRC, encoding='utf-8').read()
estilo = re.search(r'<style>(.*?)</style>',
                   io.open(FUNC, encoding='utf-8').read(), re.S).group(1)

RE_UL = re.compile(r'^[-*]\s+')
RE_OL = re.compile(r'^\d+\.\s+')


def abre_bloque(linea):
    t = linea.strip()
    if not t:
        return True
    if t.startswith(('#', '>', '|', '---', '```')):
        return True
    return bool(RE_UL.match(t) or RE_OL.match(t))


def unir_continuaciones(texto):
    """Cada bloque lógico en una sola línea."""
    salida, buf = [], None
    for linea in texto.split('\n'):
        if abre_bloque(linea):
            if buf is not None:
                salida.append(buf)
                buf = None
            t = linea.strip()
            # títulos, tablas y separadores no admiten continuación
            if not t or t.startswith(('#', '|', '---', '```')):
                salida.append(linea)
            else:
                buf = linea          # lista o cita: puede continuar
        else:
            if buf is None:
                buf = linea
            else:
                buf = buf.rstrip() + ' ' + linea.strip()
    if buf is not None:
        salida.append(buf)
    return salida


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![\w*])\*([^*\n]+)\*(?![\w*])', r'<em>\1</em>', t)
    return t


lineas = unir_continuaciones(md)
out, toc = [], []
lista = None
en_cita = False
en_tabla = False
i, n = 0, len(lineas)


def cerrar_lista():
    global lista
    if lista:
        out.append('</%s>' % lista)
        lista = None


def cerrar_cita():
    global en_cita
    if en_cita:
        out.append('</blockquote>')
        en_cita = False


def cerrar_tabla():
    global en_tabla
    if en_tabla:
        out.append('</tbody></table></div>')
        en_tabla = False


while i < n:
    s = lineas[i].strip()

    if s.startswith('|') and i + 1 < n and re.match(r'^\|[\s:|-]+\|$', lineas[i + 1].strip()):
        cerrar_lista(); cerrar_cita()
        celdas = [c.strip() for c in s.strip('|').split('|')]
        out.append('<div class="tabla-wrap"><table><thead><tr>' +
                   ''.join('<th>%s</th>' % inline(c) for c in celdas) +
                   '</tr></thead><tbody>')
        en_tabla = True
        i += 2
        continue
    if en_tabla:
        if s.startswith('|'):
            celdas = [c.strip() for c in s.strip('|').split('|')]
            out.append('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in celdas) + '</tr>')
            i += 1
            continue
        cerrar_tabla()

    m = re.match(r'^(#{1,4})\s+(.*)$', s)
    if m:
        cerrar_lista(); cerrar_cita()
        nivel, txt = len(m.group(1)), m.group(2)
        if nivel == 1:
            i += 1
            continue
        idx = 'sec%d' % len(toc)
        if nivel == 2:
            toc.append((idx, re.sub(r'^\d+\.\s*', '', txt)))
        out.append('<h%d id="%s">%s</h%d>' % (nivel, idx, inline(txt), nivel))
        i += 1
        continue

    if s == '---':
        cerrar_lista(); cerrar_cita()
        i += 1
        continue

    if s.startswith('>'):
        # Una cita ocupa varias líneas `>`; se juntan antes de convertir para
        # que una negrita que cruza el salto no quede con los asteriscos crudos.
        cerrar_lista()
        parrafos, actual = [], []
        while i < n and lineas[i].strip().startswith('>'):
            cuerpo = lineas[i].strip().lstrip('>').strip()
            if cuerpo:
                actual.append(cuerpo)
            elif actual:
                parrafos.append(' '.join(actual)); actual = []
            i += 1
        if actual:
            parrafos.append(' '.join(actual))
        out.append('<blockquote>')
        for par in parrafos:
            out.append('<p>%s</p>' % inline(par))
        out.append('</blockquote>')
        continue
    cerrar_cita()

    # La ficha de metadatos ya va en el encabezado de la página.
    if re.match(r'^\*\*(Versión del manual|Fecha|Dirigido a|Aplicación):\*\*', s):
        i += 1
        continue

    m = RE_OL.match(s)
    if m:
        if lista != 'ol':
            cerrar_lista(); out.append('<ol>'); lista = 'ol'
        out.append('<li>%s</li>' % inline(RE_OL.sub('', s)))
        i += 1
        continue

    m = RE_UL.match(s)
    if m:
        if lista != 'ul':
            cerrar_lista(); out.append('<ul>'); lista = 'ul'
        out.append('<li>%s</li>' % inline(RE_UL.sub('', s)))
        i += 1
        continue

    if not s:
        cerrar_lista()
        i += 1
        continue

    cerrar_lista()
    out.append('<p>%s</p>' % inline(s))
    i += 1

cerrar_lista(); cerrar_cita(); cerrar_tabla()

nav = '\n    '.join('<a href="#%s">%s</a>' % (idx, html.escape(t)) for idx, t in toc)
mv = re.search(r'\*\*Versión del manual:\*\*\s*([\d.]+)', md)
mv = mv.group(1) if mv else '1.2'
ma = re.search(r'\*\*Aplicación:\*\*.*?\*\*([\d.]+)\*\*', md)
ma = ma.group(1) if ma else '1.2.3'

doc = '''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%%22http://www.w3.org/2000/svg%%22 viewBox=%%220 0 100 100%%22><text y=%%22.9em%%22 font-size=%%2288%%22>&#128214;</text></svg>">
<title>Manual de Uso — SICAV Móvil</title>
<style>
%s
  .tabla-wrap{overflow-x:auto}
</style>
</head>
<body>
<div class="franja"></div>
<header class="top">
  <div class="top-inner">
    <div class="brand">
      <span class="govco">GOV.CO</span>
      <h1>Manual de Uso — SICAV Móvil</h1>
      <span class="sub">Para encuestadores de caracterización</span>
    </div>
    <div class="meta">Manual <b>v%s</b> &middot; Aplicación <b>%s</b><br>Unidad para las Víctimas — SRNI</div>
  </div>
</header>

<div class="shell">
  <nav class="toc">
    %s
    <a href="/descargar/" style="margin-top:14px;font-weight:600">&larr; Volver a la descarga</a>
  </nav>
  <main>
%s
  </main>
</div>
</body>
</html>
''' % (estilo, mv, ma, nav, '\n'.join(out))

io.open(DST, 'w', encoding='utf-8').write(doc)
print('generado:', DST)
print('secciones:', len(toc), '| bytes:', os.path.getsize(DST))
