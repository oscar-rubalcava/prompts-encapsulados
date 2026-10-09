#!/usr/bin/env python3
"""Cambia el nombre del proyecto en un solo paso, sin tocar las palabras comunes del texto.

El nombre actual vive en tools/nombre.json:
  nombre         nombre oficial, tal como se ve (p. ej. «Nombre Nuevo»)
  corto_visible  nombre corto, tal como se ve en la interfaz
  corto          identificador: módulo de Python, comando, archivos (minúsculas, sin espacios)
  slug           nombre del repositorio y de las URLs (minúsculas con guiones)
  extension      extensión de los archivos de tarjeta: titulo_v1.0.<extension>.png
  magic          firma de 4 letras al inicio del formato binario
  formato_id     identificador del formato (claves .pcid/.pub, lanzamientos, almacenamiento local)
  usuario        cuenta de GitHub

Uso:
  python tools/renombrar.py --nombre "Nombre Nuevo" --corto nuevo --slug nombre-nuevo --extension nuevo
  python tools/renombrar.py --usuario otra-cuenta --ejecutar --regenerar     # solo cambia la cuenta de GitHub
  python tools/renombrar.py ... --ejecutar              # aplica los cambios (sin esto, solo simula)
  python tools/renombrar.py ... --ejecutar --regenerar  # además regenera lo que cambió (ejemplos, logo, GIF, imagen social, sitio)
  python tools/renombrar.py ... --ejecutar --cambiar-formato --magic ABCD   # SOLO antes de publicar: también la firma de bytes y los identificadores

Cambia: el nombre visible, las URLs y los nombres de archivo. La firma de bytes y los identificadores del formato (claves, lanzamientos,
almacenamiento local) se CONSERVAN: una firma de formato no debe cambiar con la marca. NO cambia la prosa ordinaria (una palabra como «encapsulado» en una frase sigue igual).
Revisa a mano después: el subtítulo en inglés del README.en.md y cualquier frase que use el nombre como sujeto.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFGP = ROOT / "tools/nombre.json"
TEXT_SUFFIX = {".py", ".md", ".html", ".yml", ".yaml", ".json", ".txt", ".svg"}
TEXT_NAMES = {".gitignore", ".gitattributes", "NOTICE"}
SKIP_DIRS = {".git", "fonts", "ejemplos", "ejemplos_tema_claro", "assets", "_site", "__pycache__"}
SKIP_FILES = {"LICENSE", "renombrar.py", "nombre.json"}


def hexbytes(m):
    return "[" + ", ".join(f"0x{ord(c):02X}" for c in m) + "]"


def reglas(old, new, cambiar_formato=False):
    """Lista de (patrón, función de reemplazo). El orden importa: lo más específico primero."""
    R = []
    slug = re.escape(old["slug"])
    R.append((re.compile(rf"(?<![\w-]){slug}(?![A-Za-z_])"), lambda m: new["slug"]))
    if old["usuario"] != new["usuario"]:
        R.append((re.compile(re.escape(old["usuario"])), lambda m: new["usuario"]))
    R.append((re.compile(re.escape(old["nombre"])), lambda m: new["nombre"]))
    R.append((re.compile(rf"\.{re.escape(old['extension'])}\.png"), lambda m: f".{new['extension']}.png"))
    c = re.escape(old["corto"])
    for pat in (rf"\b{c}(?=\.(?:py|html|template)\b)", rf"\bimport {c}\b", rf'prog="{c}"', rf"\b{c}(?= \{{__version__\}})",
                rf"\b{c}(?=_(?:test_|ui_|icono|nombre|prensa))"):
        R.append((re.compile(pat), lambda m, o=old["corto"], n=new["corto"]: m.group(0).replace(o, n)))
    if cambiar_formato:        # solo antes de publicar: después, las tarjetas y claves existentes dejarían de abrirse
        R.append((re.compile(rf"\b{re.escape(old['magic'])}\b"), lambda m: new["magic"]))
        R.append((re.compile(re.escape(hexbytes(old["magic"]))), lambda m: hexbytes(new["magic"])))
        f = re.escape(old["formato_id"])
        for pat in (rf"\b{f}(?=-(?:key|pub|release)\b)", rf"\b{f}(?=\.(?:persist|trusted)\b)", rf'indexedDB\.open\("{f}"'):
            R.append((re.compile(pat), lambda m, o=old["formato_id"], n=new["formato_id"]: m.group(0).replace(o, n)))
    return R


def archivos_de_texto():
    for f in sorted(ROOT.rglob("*")):
        rel = f.relative_to(ROOT)
        if not f.is_file() or f.name in SKIP_FILES:
            continue
        if set(rel.parts) & SKIP_DIRS:
            continue
        if "marca" in rel.parts and f.suffix != ".md":        # los SVG/PNG de la marca se regeneran
            continue
        if f.suffix in TEXT_SUFFIX or f.name in TEXT_NAMES:
            yield f


def main():
    old = json.loads(CFGP.read_text(encoding="utf-8"))
    ap = argparse.ArgumentParser(description="Cambia el nombre del proyecto (ver el encabezado del archivo).")
    ap.add_argument("--nombre"); ap.add_argument("--corto"); ap.add_argument("--slug")
    ap.add_argument("--corto-visible"); ap.add_argument("--extension"); ap.add_argument("--magic"); ap.add_argument("--usuario")
    ap.add_argument("--ejecutar", action="store_true"); ap.add_argument("--regenerar", action="store_true")
    ap.add_argument("--cambiar-formato", action="store_true", help="cambia también la firma de bytes y los identificadores del formato (SOLO antes de publicar: rompe las tarjetas y claves existentes)")
    a = ap.parse_args()
    corto = a.corto or old["corto"]
    new = {"nombre": a.nombre or old["nombre"], "corto": corto, "slug": a.slug or old["slug"], "usuario": a.usuario or old["usuario"],
           "corto_visible": a.corto_visible or (corto.capitalize() if a.corto else old["corto_visible"]), "extension": a.extension or old["extension"],
           "magic": (a.magic or (corto.upper() + "XXXX")[:4]) if a.cambiar_formato else old["magic"],
           "formato_id": corto if a.cambiar_formato else old["formato_id"]}
    if a.magic and not a.cambiar_formato:
        sys.exit("--magic solo se aplica con --cambiar-formato (cambiarlo después de publicar rompería las tarjetas existentes).")
    for k, rx, msg in (("corto", r"[a-z][a-z0-9_]*", "minúsculas, sin espacios ni guiones (es un módulo de Python)"), ("slug", r"[a-z0-9][a-z0-9-]*", "minúsculas con guiones"),
                       ("extension", r"[a-z][a-z0-9]*", "minúsculas sin espacios"), ("magic", r"[A-Z0-9]{4}", "exactamente 4 letras mayúsculas o dígitos")):
        if not re.fullmatch(rx, new[k]):
            sys.exit(f"--{k}: «{new[k]}» no es válido ({msg}).")
    if new == old:
        sys.exit("El nombre nuevo es igual al actual: no hay nada que cambiar.")

    R = reglas(old, new, a.cambiar_formato); cambios = []
    for f in archivos_de_texto():
        t = f.read_text(encoding="utf-8")
        n = t
        for rx, fn in R:
            n = rx.sub(fn, n)
        if n != t:
            cambios.append((f, t, n))
    print(f"{'Se cambiarían' if not a.ejecutar else 'Cambiando'} {len(cambios)} archivos de texto:")
    for f, t, n in cambios[:40]:
        print(f"  {f.relative_to(ROOT)}")
    if not a.ejecutar:
        print("\nEs una simulación. Añade --ejecutar para aplicar los cambios.")
        return

    for f, t, n in cambios:
        f.write_text(n, encoding="utf-8")
    for viejo, nuevo in ((f"{old['corto']}.py", f"{new['corto']}.py"), (f"{old['corto']}.html", f"{new['corto']}.html"),
                         (f"tools/{old['corto']}.template.html", f"tools/{new['corto']}.template.html")):
        if (ROOT / viejo).exists() and viejo != nuevo:
            (ROOT / viejo).rename(ROOT / nuevo)
    cambia_ejemplos = any(new[k] != old[k] for k in ("extension", "magic", "formato_id"))
    cambia_marca = any(new[k] != old[k] for k in ("nombre", "corto", "corto_visible"))
    if cambia_ejemplos:                                                  # llevan la extensión o la firma antiguas: se regeneran
        for d in ("ejemplos", "ejemplos_tema_claro"):
            for f in (ROOT / d).glob("*"):
                f.unlink()
    if new["corto"] != old["corto"]:
        for f in (ROOT / "marca").glob(f"{old['corto']}_*"):
            f.unlink()
    CFGP.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nnombre.json actualizado.")

    pasos = [["tools/build_html.py"]]
    if cambia_ejemplos:
        pasos += [["tools/make_examples.py", "ejemplos"], ["tools/make_examples_claro.py"]]
    if cambia_marca:
        pasos += [["tools/build_marca.py"], ["tools/make_demo_gif.py"]]
    pasos += [["tools/make_social.py"], ["tools/build_site.py"]]
    if a.regenerar:
        for p in pasos:
            print("→", " ".join(p)); subprocess.run([sys.executable, *p], cwd=ROOT, check=True)
    else:
        print("\nFalta regenerar lo que lleva el nombre. Ejecuta, en este orden:")
        for p in pasos:
            print("  python", " ".join(p))
    # restos del nombre anterior
    resto = 0
    for f in archivos_de_texto():
        t = f.read_text(encoding="utf-8")
        for rx, _ in reglas(old, new, a.cambiar_formato):
            if rx.pattern != re.escape(old["usuario"]) and rx.search(t):
                resto += 1; print("  resto del nombre anterior en", f.relative_to(ROOT)); break
    print(f"\nRestos de identificadores anteriores: {resto}. Revisa a mano el subtítulo en inglés del README.en.md y las frases donde el nombre es el sujeto.")


if __name__ == "__main__":
    main()
