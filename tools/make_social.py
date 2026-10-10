"""Genera assets/social-preview.png (1280x640), la imagen que GitHub muestra al compartir el repositorio.
Se sube a mano en: Settings > General > Social preview.   Uso:  python tools/make_social.py"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "tools/nombre.json").read_text(encoding="utf-8"))
F = lambda size, bold=True: ImageFont.truetype(str(ROOT / f"fonts/IBMPlexMono-{'Bold' if bold else 'Regular'}.ttf"), size)
BG, INK, BLANCO, MUTED = (14, 19, 25), (23, 32, 42), (230, 237, 245), (147, 161, 177)
im = Image.new("RGB", (1280, 640), BG); d = ImageDraw.Draw(im)
d.rectangle([0, 0, 1280, 6], fill=BLANCO)
icon = Image.open(ROOT / f"marca/{CFG['corto']}_icono_512.png").convert("RGBA").resize((112, 112), Image.LANCZOS); im.paste(icon, (72, 70), icon)
partes = CFG["nombre"].split(" ", 1)
for i, t in enumerate(partes): d.text((72, 186 + 82 * i), t, font=F(84 if len(partes) == 2 else 96), fill=BLANCO)
d.text((72, 376), "Prompts que se pueden verificar.", font=F(32, False), fill=BLANCO)
d.text((72, 424), "Signed prompt cards you can verify.", font=F(26, False), fill=MUTED)
x = 72
for t in ("Firma Ed25519", "Cifrado AES-256", "Formato abierto"):
    w = d.textlength(t, font=F(20)) + 32; d.rounded_rectangle([x, 488, x + w, 534], radius=23, outline=(74, 90, 110), width=2)
    d.text((x + 16, 500), t, font=F(20), fill=BLANCO); x += w + 12
d.text((72, 580), f"github.com/{CFG['usuario']}/{CFG['slug']}", font=F(23, False), fill=MUTED)
cards = ["asistente-de-punto-de-venta_v1.0", "plan-de-entrenamiento-semanal_v1.0", "respuesta-a-reclamos_v1.0"]
for i, n in enumerate(cards):
    c = Image.open(ROOT / f"ejemplos/{n}.{CFG['extension']}.png").convert("RGBA"); w = 440; c = c.resize((w, round(c.height * w / c.width)), Image.LANCZOS)
    im.paste(c, (800 + (30 if i == 1 else 0), 120 + i * 175), c)
out = ROOT / "assets/social-preview.png"; im.save(out, optimize=True); print(out.name, im.size, f"{out.stat().st_size / 1024:.0f} KB")
