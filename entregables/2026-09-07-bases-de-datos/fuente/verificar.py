"""Comprueba que ninguna diapositiva se desborde de su marco 16:9.

El contenido que rebasa no se ve: la diapositiva recorta. Este script activa
cada una en un Chrome sin ventana, mide el alto real del contenido contra el
alto disponible y reporta las que no caben.

    python fuente/verificar.py

Sin argumentos revisa las dos presentaciones ya armadas.
"""

from pathlib import Path
import re
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# El mismo tamaño con el que se proyecta: 16:9 cómodo en un portátil.
VENTANA = "1600,1000"

SONDA = """
<script>
(function () {
  var filas = [];
  document.querySelectorAll('.diapo').forEach(function (d, i) {
    var previa = d.classList.contains('activa');
    d.classList.add('activa');
    // El marco recorta; el contenido real es el scrollHeight de la diapositiva.
    var sobra = d.scrollHeight - d.clientHeight;
    var cuerpo = d.querySelector('.cuerpo');
    if (cuerpo) { sobra = Math.max(sobra, cuerpo.scrollHeight - cuerpo.clientHeight); }
    if (sobra > 2) { filas.push((i + 1) + ':+' + sobra + 'px'); }
    if (!previa) { d.classList.remove('activa'); }
  });
  document.title = 'SONDA[' + filas.join(' ') + ']';
})();
</script>
"""


def revisar(html: Path) -> bool:
    marcado = html.read_text(encoding="utf-8") + SONDA
    with tempfile.TemporaryDirectory() as tmp:
        sonda = Path(tmp) / html.name
        sonda.write_text(marcado, encoding="utf-8")
        salida = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={VENTANA}", "--virtual-time-budget=8000",
             "--dump-dom", sonda.resolve().as_uri()],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout

    hallado = re.search(r"SONDA\[(.*?)\]", salida or "")
    if not hallado:
        print(f"  {html.name}: no se pudo medir (¿Chrome no cargó la página?)")
        return False
    desbordes = hallado.group(1).strip()
    if desbordes:
        print(f"  {html.name}: DESBORDAN → {desbordes}")
        return False
    print(f"  {html.name}: todas las diapositivas caben")
    return True


if __name__ == "__main__":
    objetivos = [Path(a) for a in sys.argv[1:]] or sorted(BASE.parent.glob("*.html"))
    print("Verificación de encaje 16:9")
    if not all([revisar(h) for h in objetivos]):
        raise SystemExit(1)
