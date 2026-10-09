"""Genera ejemplos_tema_claro/ a partir de ejemplos/: las mismas tarjetas, dibujadas con el tema claro.
Uso, después de make_examples.py:  python tools/make_examples_claro.py"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import encapsulados as cs
EXT = json.loads((ROOT / "tools/nombre.json").read_text(encoding="utf-8"))["extension"]

AUTOR_DEMO = {"color": (0xFB, 0xB4, 0x3F), "mark": "q"}      # el sello de la clave demo (monograma Q, ámbar)
NOMBRES = ["asistente-de-punto-de-venta_v1.0", "atencion-a-clientes-por-whatsapp_v1.0", "plan-de-entrenamiento-semanal_v1.0",
           "respuesta-a-reclamos_v1.0", "redactor-de-correos-formales_v1.0"]
out = ROOT / "ejemplos_tema_claro"; out.mkdir(exist_ok=True)
for f in out.glob("*.png"): f.unlink()
for n in NOMBRES:
    stream = cs.read_card(str(ROOT / f"ejemplos/{n}.{EXT}.png"))
    ident = None if n.startswith("redactor") else AUTOR_DEMO           # ese ejemplo es de otra persona (emblema de su clave)
    cs.save_card(stream, str(out / f"{n}.{EXT}.png"), ident, "light")
    assert cs.read_card(str(out / f"{n}.{EXT}.png")) == stream    # los datos son idénticos a los de la versión oscura
print(f"{len(NOMBRES)} tarjetas en {out.name}/")
