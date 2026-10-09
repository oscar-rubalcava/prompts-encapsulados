"""Prompts Encapsulados: prensa hidráulica sola (sin la C) + versión con el nombre escrito. Reutiliza logo_prensa.py."""
import os
import logo_prensa as lp
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

INK, AMB = lp.INK, lp.AMB
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", "IBMPlexMono-Bold.ttf")

def press_group(state, glyph):
    """Prensa sin anillo. state='abierta' (hueco entre placas) o 'cerrada' (placa apoyada en la base), centrada en el lienzo."""
    head, base = lp.parts("simple", glyph)
    if state == "cerrada":
        dy_head, top_y = lp.YB - lp.PB, (lp.PB - 35 - 26) + (lp.YB - lp.PB)
    else:
        dy_head, top_y = 0, lp.PB - 35 - 26
    dy = 100 - (top_y + 150) / 2                       # centrar verticalmente (la base termina en y=150)
    return f'<g fill="{glyph}" transform="translate(0 {dy:.1f})">{"".join(base)}<g transform="translate(0 {dy_head})">{"".join(head)}</g></g>'

def press_svg(state, tile=None, glyph=INK):
    bg = f'<rect width="200" height="200" rx="44" fill="{tile}"/>' if tile else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img" aria-label="Prompts Encapsulados: prensa hidráulica">{bg}{press_group(state, glyph)}</svg>'

def wordmark_path(text, size, x, y):
    f = TTFont(FONT); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f["head"].unitsPerEm; k = size / upm; cur = x; parts = []
    for ch in text:
        g = cmap[ord(ch)]; pen = SVGPathPen(gs); gs[g].draw(TransformPen(pen, (k, 0, 0, -k, cur, y))); parts.append(pen.getCommands()); cur += gs[g].width * k
    return " ".join(parts), cur
