"""Prueba que tools/preparar_publicacion.py detecta lo peligroso antes de publicar: claves privadas, remotos equivocados, archivos que faltan."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "tools/nombre.json").read_text(encoding="utf-8"))
ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {detail}"))


if shutil.which("git") is None:
    print("git no está instalado: se omite esta prueba"); sys.exit(0)
tmp = Path(tempfile.mkdtemp(prefix="preparar_"))


def copia(nombre, dentro_de=None):
    base = dentro_de or tmp
    dst = base / nombre
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "_site", "__pycache__"))
    return dst


def run(d):
    return subprocess.run([sys.executable, "tools/preparar_publicacion.py"], cwd=d, capture_output=True, text=True)


def git(d, *a):
    return subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)


def iniciar(d):
    git(d, "init", "-q", "-b", "main"); git(d, "config", "user.email", "t@e.com"); git(d, "config", "user.name", "t"); git(d, "add", "-A"); git(d, "commit", "-q", "-m", "x")


try:
    d = copia("limpio"); r = run(d)
    check("proyecto limpio sin git: sin errores y explica el siguiente paso", r.returncode == 0 and "todavía no es un repositorio git" in r.stdout and "gh repo create" in r.stdout and "git init" in r.stdout, r.stdout)
    iniciar(d); (d / "mi.pcid").write_text("secreto"); r = run(d)
    check("una clave que git ignora: avisa que la saques de la carpeta", r.returncode == 0 and "mi.pcid" in r.stdout and "⚠" in r.stdout, r.stdout)
    d2 = copia("sin_ignore"); (d2 / ".gitignore").write_text("__pycache__/\n"); (d2 / "mi.pcid").write_text("secreto"); r = run(d2)
    check("una clave que git NO ignora: error", r.returncode == 1 and "git NO la ignora" in r.stdout, r.stdout)
    d3 = copia("versionada"); iniciar(d3); (d3 / "mi.pcid").write_text("secreto"); git(d3, "add", "-f", "mi.pcid"); git(d3, "commit", "-q", "-m", "mal"); r = run(d3)
    check("una clave versionada: error y dice cómo quitarla", r.returncode == 1 and "git rm --cached mi.pcid" in r.stdout, r.stdout)
    d4 = copia("remoto"); iniciar(d4); git(d4, "remote", "add", "origin", "https://github.com/otro/otro.git"); r = run(d4)
    check("remoto que no coincide con nombre.json: error", r.returncode == 1 and "origin" in r.stdout and "nombre.json" in r.stdout, r.stdout)
    d5 = copia("remoto_bien"); iniciar(d5); git(d5, "remote", "add", "origin", f"https://github.com/{CFG['usuario']}/{CFG['slug']}.git"); r = run(d5)
    check("remoto correcto: sin errores", r.returncode == 0 and "el remoto «origin»" in r.stdout, r.stdout)
    d6 = copia("sin_licencia"); (d6 / "LICENSE").unlink(); r = run(d6)
    check("falta un archivo obligatorio: error", r.returncode == 1 and "falta LICENSE" in r.stdout, r.stdout)
    fuera = tmp / "otro_repo"; fuera.mkdir(); git(fuera, "init", "-q", "-b", "main"); d7 = copia("proyecto", dentro_de=fuera); r = run(d7)
    check("carpeta dentro de otro repositorio git: avisa", r.returncode == 0 and "DENTRO de otro repositorio" in r.stdout, r.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nTODO PREPARAR OK" if ok else "\nHAY FALLOS")
sys.exit(0 if ok else 1)
