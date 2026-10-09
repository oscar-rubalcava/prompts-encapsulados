"""Graba assets/demo.gif recorriendo el decodificador real con las tarjetas de ejemplo (Playwright + Pillow).
Uso:  python tools/make_demo_gif.py"""
import glob, os, sys, tempfile
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CFG = json.loads((ROOT / "tools/nombre.json").read_text(encoding="utf-8")); EXT = CFG["extension"]
EX = ROOT / "ejemplos"; URL = (ROOT / f"{CFG['corto']}.html").as_uri()
FONT = ImageFont.truetype(str(ROOT / "fonts/IBMPlexMono-Bold.ttf"), 20)
W, H, CAP = 1100, 700, 52
tmp = Path(tempfile.mkdtemp()); frames = []

def snap(pg, caption, name):
    pg.wait_for_timeout(700); p = tmp / f"{name}.png"; pg.screenshot(path=str(p), clip={"x": 0, "y": 0, "width": W, "height": H})
    im = Image.open(p).convert("RGB"); bar = Image.new("RGB", (W, CAP), (23, 32, 42)); d = ImageDraw.Draw(bar)
    d.text((22, 13), caption, font=FONT, fill=(230, 237, 245)); out = Image.new("RGB", (W, H + CAP)); out.paste(im, (0, 0)); out.paste(bar, (0, H))
    frames.append(out.resize((880, round((H + CAP) * 880 / W)), Image.LANCZOS))

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_context(viewport={"width": W, "height": H}, permissions=["clipboard-read", "clipboard-write"]).new_page(); pg.goto(URL)
    pg.set_input_files("#file", str(EX / f"asistente-de-punto-de-venta_v1.0.{EXT}.png")); snap(pg, "1 · Abres una tarjeta: la firma se verifica al instante", "f1")
    pg.set_input_files("#pubFile", str(EX / "demo_appqia.pub")); pg.wait_for_timeout(300)
    pg.set_input_files("#file", str(EX / f"asistente-de-punto-de-venta_v1.0.{EXT}.png")); snap(pg, "2 · Importas la clave del autor: ahora es de confianza", "f2")
    pg.fill("#v_nombre_negocio", "Abarrotes Lupita"); snap(pg, "3 · Rellenas las variables y copias el prompt", "f3")
    pg.set_input_files("#file", str(EX / f"resumen-de-correos-ejemplo-con-riesgos_v1.0.{EXT}.png")); snap(pg, "4 · Revisa riesgos: muestra hasta el texto oculto", "f4")
    pg.set_input_files("#file", str(EX / f"actualizacion-de-precios_v1.0.{EXT}.png")); snap(pg, "5 · Detecta una tarjeta que imita el aspecto de otro autor", "f5")
    pg.click("#tabLib"); pg.set_input_files("#libFiles", sorted(glob.glob(str(EX / "*.png")))); pg.wait_for_timeout(3500); snap(pg, "6 · Tu biblioteca: busca, filtra y ve cuánto ocupa", "f6")
    pg.screenshot(path=str(ROOT / "assets/biblioteca.png"), full_page=True)      # captura para el README
    b.close()

pal = [f.convert("P", palette=Image.ADAPTIVE, colors=160) for f in frames]
out = ROOT / "assets/demo.gif"
pal[0].save(out, save_all=True, append_images=pal[1:], duration=[2600, 2400, 2400, 3200, 2800, 3400], loop=0, optimize=True, disposal=2)
print(f"{out.name}: {len(frames)} fotogramas, {os.path.getsize(out) / 1024:,.0f} KB")
