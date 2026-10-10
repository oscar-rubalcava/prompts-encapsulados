#!/usr/bin/env python3
"""Revisión previa a publicar en GitHub. NO sube nada: comprueba y te dice qué comando sigue.

Vigila, sobre todo, que ninguna clave privada (.pcid, .key) acabe en el repositorio.
Uso, desde cualquier carpeta:  python3 tools/preparar_publicacion.py [--pruebas]
  --pruebas   además ejecuta las pruebas del formato (necesita: pip install cryptography pillow)
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "tools/nombre.json").read_text(encoding="utf-8"))
URL = f"https://github.com/{CFG['usuario']}/{CFG['slug']}"
DESCRIPCION = "Prompts que se pueden verificar: etiquetas PNG firmables y cifrables, con creador, biblioteca y decodificador sin servidor."
TOPICS = ["prompt-engineering", "prompts", "llm", "ai-security", "prompt-injection", "digital-signature", "ed25519", "encryption", "privacy", "python", "open-format"]
SKIP = {".git", "_site", "__pycache__", "node_modules"}
errores, avisos = 0, 0


def ok(m): print(f"  ✓ {m}")
def aviso(m):
    global avisos; avisos += 1; print(f"  ⚠ {m}")
def error(m):
    global errores; errores += 1; print(f"  ✗ {m}")


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)


def archivos():
    for f in sorted(ROOT.rglob("*")):
        if f.is_file() and not (set(f.relative_to(ROOT).parts) & SKIP):
            yield f


def main():
    pruebas = "--pruebas" in sys.argv
    print(f"Revisando «{CFG['nombre']}» antes de publicar en {URL}\n")
    hay_git = shutil.which("git") is not None
    en_repo = hay_git and git("rev-parse", "--is-inside-work-tree").stdout.strip() == "true"
    otro_repo = None
    if en_repo:
        top = git("rev-parse", "--show-toplevel").stdout.strip()
        if Path(top).resolve() != ROOT:
            otro_repo, en_repo = top, False          # esta carpeta vive dentro de OTRO repositorio: sus datos de git no son los del proyecto

    print("1) Claves privadas (lo más importante)")
    claves = [f for f in archivos() if f.suffix in (".pcid", ".key")]
    claves += [f for f in archivos() if f.suffix == ".json" and f"{CFG['formato_id']}-key" in f.read_text(encoding="utf-8", errors="ignore") and f not in claves]
    if not claves:
        ok("no hay claves privadas dentro de la carpeta del proyecto")
    for f in claves:
        rel = f.relative_to(ROOT).as_posix()
        if en_repo and git("check-ignore", "-q", rel).returncode == 0:
            aviso(f"{rel}: git la ignora, pero es una clave privada dentro del proyecto. Muévela FUERA de la carpeta (p. ej. ~/claves/).")
        else:
            error(f"{rel}: es una clave privada y git NO la ignora. Sácala de la carpeta antes de seguir.")
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    if "*.pcid" in gi and "*.key" in gi:
        ok(".gitignore bloquea *.pcid y *.key")
    else:
        error(".gitignore no bloquea *.pcid y *.key")
    if en_repo:
        seg = [l for l in git("ls-files").stdout.splitlines() if l.endswith((".pcid", ".key"))]
        ok("ninguna clave está versionada") if not seg else [error(f"{l}: está versionada. Quítala con: git rm --cached {l}") for l in seg]

    print("\n2) Archivos que debe tener un repositorio público")
    for rel in ("README.md", "LICENSE", "NOTICE", "SECURITY.md", "CONTRIBUTING.md", ".gitignore", ".github/workflows/ci.yml", ".github/workflows/pages.yml",
                f"{CFG['corto']}.py", f"{CFG['corto']}.html", "docs/FORMATO.md", "docs/SEGURIDAD.md", "assets/demo.gif", "assets/social-preview.png"):
        ok(rel) if (ROOT / rel).exists() else error(f"falta {rel}")

    print("\n3) Coherencia con tools/nombre.json")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    ok(f"el README apunta a {URL}") if URL in readme else error(f"el README no menciona {URL}. Si cambiaste de cuenta o de nombre: python3 tools/renombrar.py --usuario CUENTA --ejecutar --regenerar")

    print("\n4) Git")
    if not hay_git:
        error("git no está instalado (macOS: xcode-select --install)")
    elif otro_repo:
        aviso(f"esta carpeta está DENTRO de otro repositorio git ({otro_repo}). Ejecuta «git init -b main» aquí, o mueve el proyecto fuera, o git mezclará ambos.")
    elif not en_repo:
        aviso("todavía no es un repositorio git: es lo normal antes del primer commit (git init -b main)")
    else:
        rama = git("branch", "--show-current").stdout.strip()
        ok(f"rama actual: {rama or '(sin commits)'}")
        rem = git("remote", "get-url", "origin").stdout.strip()
        if not rem:
            aviso("no hay remoto «origin» todavía (se añade al crear el repositorio)")
        elif rem.rstrip("/").removesuffix(".git") in (URL, f"git@github.com:{CFG['usuario']}/{CFG['slug']}"):
            ok(f"el remoto «origin» es {rem}")
        else:
            error(f"el remoto «origin» es {rem}, pero nombre.json dice {URL}")

    if pruebas:
        print("\n5) Pruebas del formato")
        r = subprocess.run([sys.executable, "tests/test_formato.py"], cwd=ROOT, capture_output=True, text=True)
        ok("pasan todas") if r.returncode == 0 else error("fallan pruebas:\n" + r.stdout[-600:] + r.stderr[-300:])

    print(f"\nResultado: {errores} error(es), {avisos} aviso(s).")
    if errores:
        print("Corrige los errores (✗) antes de publicar."); sys.exit(1)
    m = re.search(r'__version__ = "([^"]+)"', (ROOT / f"{CFG['corto']}.py").read_text(encoding="utf-8")); v = m.group(1) if m else "0.1.0"
    print("\nSiguiente paso (desde esta carpeta):")
    print("  git init -b main                 # solo si todavía no es un repositorio")
    print("  git add -A && git status         # REVISA: no debe aparecer ningún .pcid ni .key")
    print(f'  git commit -m "{CFG["nombre"]} {v}: primera versión pública (beta)"')
    print("Después, con la CLI de GitHub (gh) se crea el repositorio y se sube el código de una vez:")
    print(f'  gh repo create {CFG["slug"]} --public --source=. --remote=origin --push --description "{DESCRIPCION}"')
    print(f"  gh repo edit {' '.join('--add-topic ' + t for t in TOPICS)}")
    print(f"O a mano: crea el repositorio vacío en https://github.com/new (sin README, sin .gitignore, sin licencia) y luego:")
    print(f"  git remote add origin {URL}.git && git push -u origin main")
    print("\nAntes del primer push, activa Pages: Settings → Pages → Source: «GitHub Actions». Pasos completos y solución de fallos: docs/PUBLICAR.md")


if __name__ == "__main__":
    main()
