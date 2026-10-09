"""Arma el sitio (presentación + demo) en _site/. GitHub Pages ejecuta esto mismo al publicar.

  _site/index.html        presentación (site/index.html)
  _site/app/index.html    el decodificador y la biblioteca (encapsulados.html)
  _site/ejemplos/         tarjetas de ejemplo para descargar
  _site/assets/           GIF, imagen social, logo y tipografía

Uso, desde cualquier carpeta:  python tools/build_site.py   (y para verlo:  python -m http.server -d _site)
"""
import json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "tools/nombre.json").read_text(encoding="utf-8"))
OUT = ROOT / "_site"
shutil.rmtree(OUT, ignore_errors=True)
(OUT / "app").mkdir(parents=True); (OUT / "ejemplos").mkdir(); (OUT / "assets/fonts").mkdir(parents=True)
page = (ROOT / "site/index.html").read_text(encoding="utf-8")
for k, v in (("NOMBRE_CORTO", CFG["corto_visible"]), ("NOMBRE", CFG["nombre"]), ("CORTO", CFG["corto"]), ("SLUG", CFG["slug"]), ("USUARIO", CFG["usuario"]), ("EXTENSION", CFG["extension"])):
    page = page.replace("{{" + k + "}}", v)
assert "{{" not in page, "quedó un marcador sin reemplazar"
(OUT / "index.html").write_text(page, encoding="utf-8")
shutil.copy(ROOT / f"{CFG['corto']}.html", OUT / "app/index.html")
for f in sorted((ROOT / "ejemplos").iterdir()):
    if f.suffix in (".png", ".pub", ".pem"):
        shutil.copy(f, OUT / "ejemplos" / f.name)
for f in (ROOT / "fonts").iterdir():
    shutil.copy(f, OUT / "assets/fonts" / f.name)
for n in ("demo.gif", "social-preview.png"):
    shutil.copy(ROOT / "assets" / n, OUT / "assets" / n)
shutil.copy(ROOT / f"marca/{CFG['corto']}_icono.svg", OUT / "assets/logo.svg")
(OUT / ".nojekyll").write_text("")
n = sum(1 for _ in OUT.rglob("*") if _.is_file())
print(f"_site/: {n} archivos, {sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file()) / 1024:,.0f} KB")
