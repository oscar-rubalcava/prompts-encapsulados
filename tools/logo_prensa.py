"""Logo de Prompts Encapsulados: la C aplastada por una prensa hidráulica. Genera SVG (estáticos y animado)."""
import colorsys, math

INK = "#17202A"
AMB = "#%02X%02X%02X" % tuple(int(v * 255) for v in colorsys.hsv_to_rgb(0.105, 0.74, 0.98))
SW = 12            # grosor del anillo
YB = 128           # cara superior de la base (donde se apoya el anillo)
GAP = 44           # medio ángulo de la abertura de la C, en grados
RY = 17            # semialto del anillo comprimido
PB = YB - 2 * RY - SW   # cara inferior de la placa móvil con el anillo comprimido (82)

def ring_d(rx, ry):
    """Arco de la C (abierta a la derecha), apoyada sobre la base."""
    cy = YB - SW / 2 - ry; cx = 100
    pt = lambda deg: (cx + rx * math.cos(math.radians(deg)), cy + ry * math.sin(math.radians(deg)))
    (x1, y1), (x2, y2) = pt(GAP), pt(360 - GAP)
    return f"M{x1:.2f} {y1:.2f} A{rx} {ry} 0 1 1 {x2:.2f} {y2:.2f}"

def parts(mode, ink):
    """(cabeza móvil, base). La cabeza se dibuja con el anillo ya comprimido (placa inferior en y=79)."""
    plate_y = PB - 13
    head = [f'<rect x="44" y="{plate_y}" width="112" height="13" rx="3"/>']            # placa móvil
    base = ['<rect x="44" y="128" width="112" height="22" rx="3"/>']                    # cama fija
    if mode in ("simple", "completa"):
        head += [f'<rect x="93" y="{PB - 35}" width="14" height="22"/>']                          # vástago
        head += [f'<rect x="80" y="{PB - 35 - (14 if mode == "completa" else 26)}" width="40" height="{14 if mode == "completa" else 26}" rx="3"/>']  # cilindro
    if mode == "completa":
        base += ['<rect x="22" y="18" width="10" height="132"/>', '<rect x="168" y="18" width="10" height="132"/>',
                 '<rect x="22" y="18" width="156" height="12" rx="2"/>', '<rect x="22" y="146" width="156" height="14" rx="3"/>']
        base = [b for b in base if 'height="22"' not in b]   # la cama la da el travesaño inferior
    if mode == "minima":
        head = ['<rect x="36" y="54" width="128" height="16" rx="3"/>']; base = ['<rect x="36" y="130" width="128" height="16" rx="3"/>']
    return head, base

def svg(mode="simple", tile=None, glyph=INK, animated=False):
    head, base = parts(mode, glyph)
    if mode == "minima":                           # 100 de alto útil: anillo más aplastado para tocar ambas placas
        rx, ry, ring = 32, 24, None
        cy = 100; cx = 100; pt = lambda d: (cx + rx * math.cos(math.radians(d)), cy + ry * math.sin(math.radians(d)))
        (x1, y1), (x2, y2) = pt(GAP), pt(360 - GAP); d = f"M{x1:.2f} {y1:.2f} A{rx} {ry} 0 1 1 {x2:.2f} {y2:.2f}"
    else:
        d = ring_d(32, RY)
    bg = f'<rect width="200" height="200" rx="44" fill="{tile}"/>' if tile else ""
    ring = f'<path d="{d}" fill="none" stroke="{glyph}" stroke-width="{SW}" stroke-linecap="butt">'
    if animated and mode != "minima":
        d0, d1 = ring_d(25, 25), ring_d(32, RY)
        ring += f'<animate attributeName="d" values="{d0};{d1};{d1};{d0}" keyTimes="0;0.45;0.7;1" dur="2.4s" repeatCount="indefinite" calcMode="spline" keySplines="0.6 0 0.9 0.4;0 0 1 1;0.3 0 0.4 1"/>'
    ring += "</path>"
    top = "".join(head)
    if animated and mode != "minima":
        top = f'<g>{top}<animateTransform attributeName="transform" type="translate" values="0 -16;0 0;0 0;0 -16" keyTimes="0;0.45;0.7;1" dur="2.4s" repeatCount="indefinite" calcMode="spline" keySplines="0.6 0 0.9 0.4;0 0 1 1;0.3 0 0.4 1"/></g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img" aria-label="Prompts Encapsulados: una C comprimida por una prensa hidráulica">'
            f'{bg}<g fill="{glyph}">{"".join(base)}{top}</g>{ring}</svg>')
