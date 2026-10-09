"""Prompts Encapsulados: prensa abierta + nombre, en distintos colores (ámbar, cobre, blanco espacial y bitonos)."""
import json, pathlib
import logo_prensa as lp, logo_prensa_sola as ls
_CFG = json.loads((pathlib.Path(__file__).resolve().parent / "nombre.json").read_text(encoding="utf-8"))

INK = lp.INK
COLORES = {           # nombre: (color de la prensa, color del nombre)
    "ambar": ("#FBB43F", "#FBB43F"),
    "cobre": ("#CF8455", "#CF8455"),
    "blanco": ("#E6EDF5", "#E6EDF5"),
    "bitono_cobre_blanco": ("#CF8455", "#E6EDF5"),      # prensa cobre, nombre blanco espacial
    "bitono_blanco_cobre": ("#E6EDF5", "#CF8455"),      # prensa blanca, nombre cobre
}

def _lineas():
    n = _CFG["nombre"].split(" ", 1)
    return n if len(n) == 2 else [n[0]]


def lockup(press, name, dark=True):
    """Icono + nombre (en dos líneas si tiene dos palabras). Texto convertido a curvas: no depende de tener la fuente instalada."""
    ls_ = _lineas()
    trazos = [ls.wordmark_path(ls_[0], 44, 148, 52), ls.wordmark_path(ls_[1], 44, 148, 100)] if len(ls_) == 2 else [ls.wordmark_path(ls_[0], 52, 148, 80)]
    w = max(e for _, e in trazos) + 24
    bg = f'<rect width="{w:.0f}" height="120" rx="26" fill="{INK}"/>' if dark else ""
    txt = name if dark else INK
    icon = f'<svg x="0" y="0" width="120" height="120" viewBox="0 0 200 200"><rect width="200" height="200" rx="44" fill="{INK}"/>{ls.press_group("abierta", press)}</svg>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} 120" role="img" aria-label="{_CFG["nombre"]}">{bg}{icon}<path d="{" ".join(d for d, _ in trazos)}" fill="{txt}"/></svg>'


def icono(press):
    return ls.press_svg("abierta", tile=INK, glyph=press)
