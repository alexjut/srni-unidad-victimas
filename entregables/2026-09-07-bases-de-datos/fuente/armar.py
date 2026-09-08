"""Ensambla las presentaciones de bases de datos a partir del cuerpo y el estilo común.

Cada `cuerpo_*.html` contiene solo las secciones `<section class="diapo">`. Este
script les pone el estilo, la navegación y la numeración de pie, y escribe el
HTML autónomo que se abre en el navegador y se imprime a PDF.

    python fuente/armar.py

La numeración no se escribe a mano: el cuerpo lleva `<span data-num></span>` y
aquí se reemplaza por «NN / TT». Así insertar una diapositiva no obliga a
renumerar las demás.
"""

from pathlib import Path
import re

BASE = Path(__file__).resolve().parent

PLANTILLA = """<title>{titulo}</title>
<style>
{css}
</style>
<div class="escenario">
<main id="deck">

{cuerpo}
</main>

<nav class="controles" aria-label="Navegación de la presentación">
  <button type="button" id="ant" aria-label="Diapositiva anterior">◀ Anterior</button>
  <span class="contador" id="contador">01 / {total}</span>
  <button type="button" id="sig" aria-label="Diapositiva siguiente">Siguiente ▶</button>
  <span class="pista-prog" aria-hidden="true"><span id="prog" style="width:{primera}%"></span></span>
</nav>
</div>

<script>
(function () {{
  var diapos = Array.prototype.slice.call(document.querySelectorAll('.diapo'));
  var contador = document.getElementById('contador');
  var prog = document.getElementById('prog');
  var actual = 0;

  function pad(n) {{ return (n < 10 ? '0' : '') + n; }}

  function mostrar(i) {{
    actual = Math.max(0, Math.min(diapos.length - 1, i));
    diapos.forEach(function (d, n) {{ d.classList.toggle('activa', n === actual); }});
    contador.textContent = pad(actual + 1) + ' / ' + diapos.length;
    prog.style.width = ((actual + 1) / diapos.length * 100).toFixed(1) + '%';
  }}

  document.getElementById('ant').addEventListener('click', function () {{ mostrar(actual - 1); }});
  document.getElementById('sig').addEventListener('click', function () {{ mostrar(actual + 1); }});

  document.addEventListener('keydown', function (e) {{
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {{ mostrar(actual + 1); e.preventDefault(); }}
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{ mostrar(actual - 1); e.preventDefault(); }}
    else if (e.key === 'Home') {{ mostrar(0); e.preventDefault(); }}
    else if (e.key === 'End') {{ mostrar(diapos.length - 1); e.preventDefault(); }}
  }});

  var x0 = null;
  document.addEventListener('touchstart', function (e) {{ x0 = e.changedTouches[0].clientX; }}, {{ passive: true }});
  document.addEventListener('touchend', function (e) {{
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 55) {{ mostrar(actual + (dx < 0 ? 1 : -1)); }}
    x0 = null;
  }}, {{ passive: true }});

  function desdeHash() {{
    var n = parseInt((location.hash || '').replace('#', ''), 10);
    return isNaN(n) ? 0 : n - 1;
  }}
  window.addEventListener('hashchange', function () {{ mostrar(desdeHash()); }});

  mostrar(desdeHash());
}})();
</script>
"""

PRESENTACIONES = [
    ("cuerpo_bd_actual.html", "Base-de-datos-SICAV-produccion.html",
     "La base de datos de SICAV en producción · 7 sep 2026"),
    ("cuerpo_bd_anterior.html", "Base-de-datos-sistema-anterior.html",
     "La base de datos del sistema anterior · 7 sep 2026"),
]


def armar(origen: str, destino: str, titulo: str) -> None:
    css = (BASE / "estilo-sicav.css").read_text(encoding="utf-8").strip()
    cuerpo = (BASE / origen).read_text(encoding="utf-8").strip()

    # Se numera por posición de la sección, no por orden de aparición de la
    # marca: la portada no lleva pie, y aun así la siguiente es la 02.
    trozos = cuerpo.split('<section class="diapo')
    total = len(trozos) - 1
    for i in range(1, len(trozos)):
        trozos[i] = re.sub(r'<span data-num\s*/?></span>',
                           f'<span>{i:02d} / {total:02d}</span>', trozos[i])
    cuerpo = '<section class="diapo'.join(trozos)
    if 'data-num' in cuerpo:
        raise SystemExit(f"{origen}: quedaron marcas de numeración sin resolver")

    # La primera diapositiva es la que se ve al abrir.
    cuerpo = cuerpo.replace('<section class="diapo', '<section class="diapo activa', 1)

    html = PLANTILLA.format(
        titulo=titulo, css=css, cuerpo=cuerpo,
        total=f"{total:02d}", primera=f"{100 / total:.1f}",
    )
    (BASE.parent / destino).write_text(html, encoding="utf-8")
    print(f"{destino}: {total} diapositivas")


if __name__ == "__main__":
    for origen, destino, titulo in PRESENTACIONES:
        armar(origen, destino, titulo)
