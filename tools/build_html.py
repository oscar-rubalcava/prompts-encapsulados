"""Genera encapsulados.html (el decodificador y la biblioteca, en un solo archivo) a partir de tools/encapsulados.template.html.

Incrusta IBM Plex Mono sin modificar, su licencia OFL, el logo, la versión y el hash del script para la CSP.
Uso, desde cualquier carpeta:  python tools/build_html.py
"""
import base64, hashlib, re, sys, urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import importlib, json
import logo_prensa as lp, logo_prensa_sola as ls

CFG = json.loads((HERE / "nombre.json").read_text(encoding="utf-8"))          # nombre, slug, usuario, etc.: se cambian con tools/renombrar.py
REPO_URL = f"https://github.com/{CFG['usuario']}/{CFG['slug']}"
programa = importlib.import_module(CFG["corto"])        # el módulo principal, por el nombre de la configuración
BLANCO = "#E6EDF5"

icon = ls.press_svg("abierta", tile=lp.INK, glyph=BLANCO)
b64 = lambda rel: base64.b64encode((ROOT / rel).read_bytes()).decode()
lic = (ROOT / "fonts/IBMPlexMono-OFL.txt").read_text(encoding="utf-8").replace("</script", "<\\/script")
html = (HERE / f"{CFG['corto']}.template.html").read_text(encoding="utf-8")
for k, v in (("{{FAVICON}}", urllib.parse.quote(icon, safe="")), ("{{FONT_REGULAR}}", b64("fonts/IBMPlexMono-Regular.ttf")),
             ("{{FONT_BOLD}}", b64("fonts/IBMPlexMono-Bold.ttf")), ("{{LOGO}}", icon), ("{{LICENSE}}", lic),
             ("{{APP_VERSION}}", programa.__version__), ("{{REPO_URL}}", REPO_URL), ("{{NOMBRE}}", CFG["nombre"]), ("{{NOMBRE_CORTO}}", CFG["corto_visible"]),
             ("{{FORMATO_ID}}", CFG["formato_id"]), ("{{MAGIC}}", CFG["magic"]), ("{{MAGIC_BYTES}}", "[" + ", ".join(f"0x{ord(c):02X}" for c in CFG["magic"]) + "]")):
    assert k in html, f"falta el marcador {k} en la plantilla"
    html = html.replace(k, v)
m = re.search(r"<script>(.*?)</script>", html, re.S)
assert m, "no encontré el script ejecutable"
digest = base64.b64encode(hashlib.sha256(m.group(1).encode("utf-8")).digest()).decode()
assert "{{SCRIPT_HASH}}" in html
html = html.replace("{{SCRIPT_HASH}}", digest)
(ROOT / f"{CFG['corto']}.html").write_bytes(html.encode("utf-8"))
print(f"encapsulados.html {programa.__version__}: {len(html) // 1024} KB · hash del script (CSP): {digest[:16]}…")
