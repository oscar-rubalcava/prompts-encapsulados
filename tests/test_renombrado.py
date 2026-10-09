"""Prueba que tools/renombrar.py cambia el nombre de verdad.

Copia el proyecto, lo renombra a un nombre inventado, regenera lo necesario y comprueba que todo sigue funcionando:
  A) modo normal: cambia el nombre y CONSERVA el formato (firma de bytes e identificadores)
  B) --cambiar-formato: cambia también la firma de bytes y los identificadores (solo válido antes de publicar)
Tarda un par de minutos: ejecuta el conjunto completo de pruebas del formato dentro de cada copia.
"""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD = json.loads((ROOT / "tools/nombre.json").read_text(encoding="utf-8"))
ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {detail}"))


def copiar(tmp, nombre):
    dst = tmp / nombre
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "_site", "__pycache__"))
    return dst


def py(dst, *args):
    return subprocess.run([sys.executable, *args], cwd=dst, capture_output=True, text=True)


def texto(dst):
    for f in sorted(dst.rglob("*")):
        rel = f.relative_to(dst)
        if f.is_file() and not (set(rel.parts) & {"fonts", "ejemplos", "ejemplos_tema_claro", "assets", "marca", "_site", "__pycache__"}) \
                and f.suffix in {".py", ".md", ".html", ".yml", ".json", ".txt"} and f.name not in {"renombrar.py", "LICENSE", "test_renombrado.py"}:
            yield f, f.read_text(encoding="utf-8")


NUEVO = ["--nombre", "Zeta Prueba", "--corto", "zetaprueba", "--slug", "zeta-prueba", "--usuario", "otro-usuario", "--corto-visible", "Zeta", "--extension", "zeta"]
tmp = Path(tempfile.mkdtemp(prefix="renombrado_"))
try:
    # ---------- A) modo normal
    a = copiar(tmp, "a")
    sim = py(a, "tools/renombrar.py", *NUEVO)
    check("A simulación: lista cambios y no toca nada", sim.returncode == 0 and "simulación" in sim.stdout and (a / f"{OLD['corto']}.py").exists(), sim.stdout + sim.stderr)
    check("A rechaza un identificador inválido", py(a, "tools/renombrar.py", "--nombre", "X", "--corto", "Con Espacios", "--slug", "x").returncode != 0)
    check("A rechaza --magic sin --cambiar-formato", py(a, "tools/renombrar.py", *NUEVO, "--magic", "ZETA").returncode != 0)
    ej = py(a, "tools/renombrar.py", *NUEVO, "--ejecutar")
    check("A ejecutar el renombrado", ej.returncode == 0, ej.stdout + ej.stderr)
    check("A archivos renombrados", (a / "zetaprueba.py").exists() and (a / "zetaprueba.html").exists() and not (a / f"{OLD['corto']}.py").exists())
    r1 = py(a, "tools/build_html.py"); r2 = py(a, "tools/make_examples.py", "ejemplos"); r3 = py(a, "tools/make_examples_claro.py")
    check("A regenerar decodificador y ejemplos", r1.returncode == 0 and r2.returncode == 0 and r3.returncode == 0, r1.stderr + r2.stderr + r3.stderr)
    src = (a / "zetaprueba.py").read_text(encoding="utf-8")
    check("A el formato se conserva (firma de bytes e identificadores)", f'b"{OLD["magic"]}"' in src and f'{OLD["formato_id"]}-key' in src)
    html = (a / "zetaprueba.html").read_text(encoding="utf-8")
    check("A decodificador: título, nombre corto y enlace nuevos", "<title>Zeta Prueba</title>" in html and "<b>Zeta</b>" in html and "otro-usuario/zeta-prueba" in html)
    check("A las tarjetas usan la extensión nueva", any(p.name.endswith(".zeta.png") for p in (a / "ejemplos").glob("*.png")))
    viejos = [str(f.relative_to(a)) for f, t in texto(a) if re.search(rf"import {OLD['corto']}\b|{OLD['corto']}\.(py|html)\b|{re.escape(OLD['slug'])}|{re.escape(OLD['nombre'])}", t)]
    check("A sin restos del nombre anterior", not viejos, ", ".join(viejos))
    t1 = py(a, "tests/test_formato.py")
    check("A el proyecto renombrado pasa todas las pruebas del formato", t1.returncode == 0 and "TODO PYTHON OK" in t1.stdout, t1.stdout[-400:] + t1.stderr[-400:])

    # ---------- B) también el formato
    b = copiar(tmp, "b")
    ej = py(b, "tools/renombrar.py", *NUEVO, "--cambiar-formato", "--magic", "ZETA", "--ejecutar")
    check("B ejecutar con --cambiar-formato", ej.returncode == 0, ej.stdout + ej.stderr)
    r1 = py(b, "tools/build_html.py"); r2 = py(b, "tools/make_examples.py", "ejemplos")
    check("B regenerar decodificador y ejemplos", r1.returncode == 0 and r2.returncode == 0, r1.stderr + r2.stderr)
    src = (b / "zetaprueba.py").read_text(encoding="utf-8")
    check("B firma de bytes e identificadores nuevos", 'b"ZETA"' in src and "zetaprueba-key" in src and f'{OLD["formato_id"]}-key' not in src)
    html = (b / "zetaprueba.html").read_text(encoding="utf-8")
    check("B el decodificador reconoce la firma nueva", "[0x5A, 0x45, 0x54, 0x41]" in html and "zetaprueba-pub" in html)
    t2 = py(b, "tests/test_formato.py")
    check("B el proyecto con el formato cambiado pasa todas las pruebas", t2.returncode == 0 and "TODO PYTHON OK" in t2.stdout, t2.stdout[-400:] + t2.stderr[-400:])

    # ---------- C) solo la cuenta de GitHub: no debe regenerar ni tocar los ejemplos
    c = copiar(tmp, "c")
    antes = {p.name: p.read_bytes() for p in (c / "ejemplos").glob("*")}
    ej = py(c, "tools/renombrar.py", "--usuario", "otro-usuario", "--ejecutar")
    check("C cambiar solo el usuario", ej.returncode == 0, ej.stdout + ej.stderr)
    despues = {p.name: p.read_bytes() for p in (c / "ejemplos").glob("*")}
    check("C los ejemplos y el nombre no se tocan", antes == despues and (c / f"{OLD['corto']}.py").exists())
    r1 = py(c, "tools/build_html.py")
    cfg = json.loads((c / "tools/nombre.json").read_text(encoding="utf-8"))
    check("C el usuario cambió en la configuración, el README y el decodificador",
          cfg["usuario"] == "otro-usuario" and f"otro-usuario/{OLD['slug']}" in (c / "README.md").read_text(encoding="utf-8")
          and f"otro-usuario/{OLD['slug']}" in (c / f"{OLD['corto']}.html").read_text(encoding="utf-8") and r1.returncode == 0)
    check("C no queda el usuario anterior", not any(OLD["usuario"] in t for f, t in texto(c)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nTODO RENOMBRADO OK" if ok else "\nHAY FALLOS")
sys.exit(0 if ok else 1)
