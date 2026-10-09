import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import logo_prensa as lp, logo_prensa_sola as ls, logo_colores as lc
from playwright.sync_api import sync_playwright
from PIL import Image
OUT = str(ROOT / "marca"); os.makedirs(OUT, exist_ok=True)
BLANCO, INK = "#E6EDF5", lp.INK
files = {
    "encapsulados_icono.svg": ls.press_svg("abierta", tile=INK, glyph=BLANCO),
    "encapsulados_prensa_blanca_transparente.svg": ls.press_svg("abierta", tile=None, glyph=BLANCO),     # para fondos oscuros
    "encapsulados_prensa_tinta_transparente.svg": ls.press_svg("abierta", tile=None, glyph=INK),         # para fondos claros
    "encapsulados_nombre_oscuro.svg": lc.lockup(BLANCO, BLANCO, dark=True),
    "encapsulados_nombre_claro.svg": lc.lockup(BLANCO, BLANCO, dark=False),
}
for n, s in files.items(): open(f"{OUT}/{n}", "w", encoding="utf-8").write(s)
sizes = (512, 256, 128, 64, 32, 16)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 600, 'height': 600})
    for s in sizes:
        open("/tmp/icono.html", "w").write(f'<body style="margin:0;background:transparent"><img id="i" src="file://{os.path.abspath(OUT)}/encapsulados_icono.svg" width="{s}" height="{s}" style="display:block"></body>')
        pg.goto("file:///tmp/icono.html"); pg.wait_for_timeout(200)
        pg.locator('#i').screenshot(path=f"{OUT}/encapsulados_icono_{s}.png", omit_background=True)
    b.close()
ims = [Image.open(f"{OUT}/encapsulados_icono_{s}.png").convert("RGBA") for s in (16, 32, 64)]
ims[-1].save(f"{OUT}/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
print(sorted(os.listdir(OUT)))
