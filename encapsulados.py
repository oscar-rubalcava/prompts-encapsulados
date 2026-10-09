#!/usr/bin/env python3
"""
Prompts Encapsulados v4: cada prompt en una etiqueta PNG, comprimido, cifrable y firmado.

Flujo de bytes (big-endian), guardado en los píxeles RGB de la zona de datos de la etiqueta:

  "PENC" | VERSION(1)=4 | FLAGS(1) | [SALT(16) NONCE(12) ITER(4)] | PUBLEN(2) | PUBLICO(PUBLEN)
        | LEN(4) | PAYLOAD(LEN) | [CLAVE_PUBLICA(32) FIRMA(64)] | CRC32(4)

  FLAGS   : bit0 = cifrada (AES-256-GCM), bit1 = firmada (Ed25519)
  PUBLICO : JSON UTF-8 sin cifrar (título, categoría, versión, autor, etiquetas).
            Sirve para indexar una biblioteca sin contraseña. Está cubierto por la firma
            y, si la tarjeta está cifrada, también autenticado por GCM (forma parte de AAD).
  PAYLOAD : JSON UTF-8 privado (prompt, sistema, variables) -> deflate crudo -> [AES-256-GCM]
  FIRMA   : cubre todos los bytes desde "PENC" hasta el final de PAYLOAD.

Geometría de la imagen (etiqueta): ancho W, alto H. La zona de datos es
x en [PADX, W-PADX), y en [TOP, H-BOT). Todo lo demás es decorativo y no es confiable.
"""
import argparse, colorsys, csv, getpass, glob, hashlib, json, math, os, random, re, struct, sys, unicodedata, zlib
from datetime import datetime, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
from cryptography.exceptions import InvalidSignature
from PIL import Image, ImageChops, ImageDraw, ImageFont

MAGIC = b"PENC"
VERSION = 4
__version__ = "0.9.0"      # versión del programa; el formato de tarjeta tiene la suya (VERSION)
FLAG_ENC, FLAG_SIGNED = 1, 2
SIG_TRAILER = 96
MAX_PUBLIC = 4096
PBKDF2_ITER = 600_000          # OWASP 2023 para PBKDF2-HMAC-SHA256; las tarjetas antiguas guardan sus propias iteraciones
W, TOP, BOT, PADX, MIN_ROWS, CUT = 360, 74, 18, 6, 10, 22     # geometría de la etiqueta
INK, NEUTRAL = (23, 32, 42), (74, 90, 110)
CAT_PALETTE = [0.60, 0.33, 0.75, 0.50, 0.00, 0.90, 0.17, 0.42]  # tonos bien separados entre sí
VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")


# ============================================================ utilidades
def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "tarjeta"


def hex_to_rgb(h):
    h = h.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"Color no válido: #{h} (usa el formato #RRGGBB).")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(c):
    return "#%02X%02X%02X" % tuple(c)


def _hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def deflate_raw(data):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(data) + c.flush()


def inflate_raw(data):
    return zlib.decompress(data, -15)


def derive_key(password, salt, iters):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters, dklen=32)


def fingerprint(pub):
    h = hashlib.sha256(pub).hexdigest().upper()[:24]
    return "-".join(h[i:i + 4] for i in range(0, 24, 4))


# ============================================================ identidad (firma)
def keygen(name, prefix, password=None, color=None, mark="auto"):
    if mark not in ("auto", "q"):
        raise ValueError("El sello debe ser 'auto' (emblema derivado de tu clave) o 'q' (monograma Q).")
    if color:
        hex_to_rgb(color)
    priv = Ed25519PrivateKey.generate()
    raw = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    brand = {"color": color.upper() if color else None, "mark": mark}
    ident = {"format": "encapsulados-key", "v": 1, "name": name, "public": pub.hex(), "brand": brand}
    if password:
        salt, nonce = os.urandom(16), os.urandom(12)
        ct = AESGCM(derive_key(password, salt, PBKDF2_ITER)).encrypt(nonce, raw, b"encapsulados-key")
        ident["enc"] = {"salt": salt.hex(), "nonce": nonce.hex(), "iters": PBKDF2_ITER, "ct": ct.hex()}
    else:
        ident["private"] = raw.hex()
    fd = os.open(prefix + ".pcid", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(ident, f, indent=2, ensure_ascii=False)
    with open(prefix + ".pub", "w", encoding="utf-8") as f:
        json.dump({"format": "encapsulados-pub", "v": 1, "name": name, "public": pub.hex(),
                   "fingerprint": fingerprint(pub), "brand": brand}, f, indent=2, ensure_ascii=False)
    write_pem(pub, prefix + ".pem")
    return pub


def write_pem(pub, path):
    """Clave pública en formato PEM estándar: OpenSSL la lee directamente (verificación independiente de Prompts Encapsulados)."""
    with open(path, "wb") as f:
        f.write(Ed25519PublicKey.from_public_bytes(pub).public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))


def load_identity(path, password=None):
    ident = json.load(open(path, encoding="utf-8"))
    if ident.get("format") != "encapsulados-key":
        raise ValueError("Ese archivo no es una identidad de Prompts Encapsulados (.pcid).")
    if "enc" in ident:
        if not password:
            password = getpass.getpass("Contraseña de la clave de firma: ")
        e = ident["enc"]
        try:
            raw = AESGCM(derive_key(password, bytes.fromhex(e["salt"]), e["iters"])).decrypt(
                bytes.fromhex(e["nonce"]), bytes.fromhex(e["ct"]), b"encapsulados-key")
        except Exception:
            raise ValueError("Contraseña de la clave de firma incorrecta.")
    else:
        raw = bytes.fromhex(ident["private"])
    priv = Ed25519PrivateKey.from_private_bytes(raw)
    pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    if pub.hex() != ident["public"]:
        raise ValueError("La identidad está dañada (la clave pública no coincide).")
    brand = ident.get("brand") or {}
    return {"priv": priv, "pub": pub, "name": ident.get("name", ""),
            "color": hex_to_rgb(brand["color"]) if brand.get("color") else None, "mark": brand.get("mark", "auto")}


def load_trusted(paths):
    t = {}
    for p in paths or []:
        d = json.load(open(p, encoding="utf-8"))
        pub = bytes.fromhex(d["public"])
        t[fingerprint(pub)] = d.get("name") or fingerprint(pub)
    return t


# ============================================================ formato
def build_public(title="", category="", version="1.0", author="", tags=None, model="", cat_hue=None, hide=False, emblem=None):
    if hide:
        p = {"title": "", "category": "", "version": "", "author": "", "tags": [], "model": ""}
        if emblem:
            p["emblem"] = {"h": emblem["h"], "g": emblem["g"]}
        return p
    p = {"title": title, "category": category, "version": version, "author": author,
         "tags": list(tags or []), "model": model}
    if cat_hue is not None:
        p["cat_hue"] = round(float(cat_hue), 3)
    if emblem:
        p["emblem"] = {"h": emblem["h"], "g": emblem["g"]}
    return p


def build_payload(prompt, system="", description="", variables=None):
    return {"format": "encapsulados", "v": VERSION, "description": description, "system": system, "prompt": prompt,
            "variables": variables or {}, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def pack(payload, public, password=None, signer=None):
    pub_bytes = json.dumps(public, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(pub_bytes) > MAX_PUBLIC:
        raise ValueError(f"El bloque público (título, categoría, etiquetas) pesa {len(pub_bytes)} bytes; el máximo es {MAX_PUBLIC}.")
    body = deflate_raw(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    flags = (FLAG_ENC if password else 0) | (FLAG_SIGNED if signer else 0)
    head = MAGIC + bytes([VERSION, flags])
    salt = nonce = None
    if password:
        salt, nonce = os.urandom(16), os.urandom(12)
        head += salt + nonce + struct.pack(">I", PBKDF2_ITER)
    head += struct.pack(">H", len(pub_bytes)) + pub_bytes
    head += struct.pack(">I", len(body) + (16 if password else 0))
    if password:
        body = AESGCM(derive_key(password, salt, PBKDF2_ITER)).encrypt(nonce, body, head)
    raw = head + body
    if signer:
        pk = signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        raw += pk + signer.sign(raw)
    return raw + struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF)


def parse(stream):
    if len(stream) < 16 or stream[:4] != MAGIC:
        raise ValueError("No es una tarjeta de Prompts Encapsulados (firma del formato incorrecta).")
    ver, flags = stream[4], stream[5]
    if ver != VERSION:
        raise ValueError(f"Versión de formato no soportada: {ver}")
    enc, signed = bool(flags & FLAG_ENC), bool(flags & FLAG_SIGNED)
    pos, salt, nonce, iters = 6, None, None, 0
    if enc:
        salt, nonce = stream[6:22], stream[22:34]
        iters = struct.unpack(">I", stream[34:38])[0]
        pos = 38
    publen = struct.unpack(">H", stream[pos:pos + 2])[0]
    pos += 2
    if publen > MAX_PUBLIC or pos + publen + 4 > len(stream):
        raise ValueError("La tarjeta está dañada (bloque público incompleto).")
    pub_bytes = stream[pos:pos + publen]
    pos += publen
    length = struct.unpack(">I", stream[pos:pos + 4])[0]
    pos += 4
    end_payload = pos + length
    crc_pos = end_payload + (SIG_TRAILER if signed else 0)
    if crc_pos + 4 > len(stream):
        raise ValueError("La tarjeta está dañada (datos incompletos).")
    if zlib.crc32(stream[:crc_pos]) & 0xFFFFFFFF != struct.unpack(">I", stream[crc_pos:crc_pos + 4])[0]:
        raise ValueError("La tarjeta está dañada (checksum no coincide).")
    try:
        public = json.loads(pub_bytes.decode("utf-8"))
        if not isinstance(public, dict):
            raise ValueError
    except ValueError:
        raise ValueError("La tarjeta está dañada (bloque público ilegible).")
    info = dict(encrypted=enc, signed=signed, salt=salt, nonce=nonce, iters=iters, public=public,
                head=stream[:pos], body=stream[pos:end_payload], signed_bytes=stream[:end_payload],
                pub=None, sig=None, end=crc_pos + 4)
    if signed:
        info["pub"], info["sig"] = stream[end_payload:end_payload + 32], stream[end_payload + 32:end_payload + 96]
    return info


def signature_status(info):
    """'none' | 'valid' | 'invalid'"""
    if not info["signed"]:
        return "none"
    try:
        Ed25519PublicKey.from_public_bytes(info["pub"]).verify(info["sig"], info["signed_bytes"])
        return "valid"
    except (InvalidSignature, ValueError):
        return "invalid"


def describe_signature(info, trusted=None):
    st = signature_status(info)
    if st == "none":
        return st, "Sin firma: no se puede comprobar quién creó esta tarjeta."
    fp = fingerprint(info["pub"])
    if st == "invalid":
        return st, f"FIRMA NO VÁLIDA (huella {fp}): la tarjeta fue modificada o la firma está dañada."
    if trusted and fp in trusted:
        return st, f"Firma válida. Autor de confianza: {trusted[fp]} (huella {fp})."
    return st, f"Firma válida, pero autor desconocido (huella {fp}). Confirma la huella con el autor por otro canal."


def unpack(stream, password=None):
    info = parse(stream)
    body = info["body"]
    if info["encrypted"]:
        if not password:
            raise ValueError("La tarjeta está cifrada: falta la contraseña.")
        try:
            body = AESGCM(derive_key(password, info["salt"], info["iters"])).decrypt(info["nonce"], body, info["head"])
        except Exception:
            raise ValueError("Contraseña incorrecta o tarjeta modificada.")
    return json.loads(inflate_raw(body).decode("utf-8"))


def is_encrypted(stream):
    return stream[:4] == MAGIC and bool(stream[5] & FLAG_ENC)



# ============================================================ revisión de seguridad del texto
HIDDEN_RE = re.compile("[\U000E0000-\U000E007F\u200B\u2060\uFEFF\u202A-\u202E\u2066-\u2069\u00AD]")
_SEV = {"alta": 3, "media": 2, "baja": 1}


def strip_hidden(text):
    """Quita caracteres que no se ven (etiquetas Unicode, ancho cero, controles bidireccionales, guion blando)."""
    return HIDDEN_RE.sub("", text or "")


def _decode_tags(text):
    return "".join(chr(ord(c) - 0xE0000) for c in text if 0xE0020 <= ord(c) <= 0xE007E)


_PHRASES = [
    ("alta", "Ordena ignorar instrucciones anteriores", r"ignor\w* (todas? )?(las |tus |sus |the )?(instrucciones|reglas|indicaciones|instructions|rules) (anteriores|previas|previous|prior)|ignore (all |any )?(the )?(previous|prior|above) (instructions|rules)|olvida (todo|tus instrucciones)"),
    ("alta", "Pide ocultarle algo al usuario", r"no (le )?(digas|menciones|informes|avises|reveles) (nada )?(al|a el|a la) (usuario|persona)|do not (tell|inform|mention)[^.]{0,30}user|sin que (el|la) usuari[oa] (lo )?sepa"),
    ("alta", "Pide revelar el mensaje de sistema", r"(revela|muestra|imprime|repite|reveal|show|print|repeat)[^.]{0,30}(prompt|mensaje|instrucciones|instructions) (del |de |of the )?(sistema|interno|system)"),
    ("alta", "Pide enviar datos a una dirección externa", r"(envia|manda|sube|publica|reenvia|post|send|upload|forward)[^.]{0,80}https?://"),
    ("alta", "Pide enviar credenciales o secretos", r"(envia|manda|comparte|send|share|forward)[^.]{0,50}(contrasena|password|token|api[ _-]?key|credencial|credential|clave privada|frase semilla|seed phrase)"),
    ("alta", "Contiene una orden que descarga y ejecuta código", r"(curl|wget)\s+[^|\n]+\|\s*(sh|bash|zsh|python)|powershell[^.\n]{0,40}(-enc|downloadstring|iex)|base64 -d[^\n]*\|\s*(sh|bash)"),
    ("media", "Contiene comandos de terminal", r"\b(rm -rf|sudo |chmod \+x|curl |wget |eval\(|exec\(|os\.system|subprocess)"),
    ("media", "Menciona contraseñas, tokens o claves", r"(contrasena|password|token|api[ _-]?key|clave privada|frase semilla|seed phrase|credencial)"),
]


def review_text(text):
    """Heurísticas de riesgo sobre un prompt. NO es un antivirus: señala cosas que conviene leer con atención."""
    text = text or ""
    findings = []
    hidden = HIDDEN_RE.findall(text)
    if hidden:
        decoded = _decode_tags(text)
        msg = f"Contiene {len(hidden)} caracteres ocultos (no se ven al leer)."
        if decoded:
            msg += f" Texto oculto decodificado: «{decoded[:200]}»"
        findings.append({"sev": "alta", "msg": msg, "count": len(hidden), "hidden_text": decoded})
    n = unicodedata.normalize("NFD", text.lower()); n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    for sev, label, rx in _PHRASES:
        hits = re.findall(rx, n)
        if hits:
            findings.append({"sev": sev, "msg": label + ".", "count": len(hits)})
    urls = re.findall(r"https?://[^\s)>\]\"']+", text)
    if urls:
        doms = sorted({re.sub(r"^https?://", "", u).split("/")[0].lower() for u in urls})
        findings.append({"sev": "media", "msg": f"Contiene {len(urls)} enlace(s): {', '.join(doms[:6])}.", "count": len(urls)})
    if re.search(r"[A-Za-z0-9+/=]{200,}", text):
        findings.append({"sev": "media", "msg": "Contiene un bloque largo codificado (base64 o similar) que no se puede leer a simple vista.", "count": 1})
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        findings.append({"sev": "baja", "msg": "Contiene direcciones de correo.", "count": 1})
    findings.sort(key=lambda f: -_SEV[f["sev"]])
    return findings


def max_severity(findings):
    return max((f["sev"] for f in findings), key=lambda s: _SEV[s], default=None)


def weak_password(pw):
    """Aviso (no bloqueo) para contraseñas cortas: la fuerza bruta contra una tarjeta cifrada se hace sin conexión."""
    if len(pw) < 12:
        return "La contraseña es corta (menos de 12 caracteres). Quien tenga el archivo puede probar contraseñas sin límite: usa una frase larga (4 o más palabras)."
    return None


def visual_status(path, info=None):
    """Compara la 'regla de huella' dibujada en la imagen con la que corresponde a la clave que firmó.
    'match' | 'mismatch' | 'na' (sin firma, o el color de la regla no se distingue del fondo)."""
    info = info or parse(read_card(path))
    if not info["signed"]:
        return "na"
    img = Image.open(path).convert("RGBA"); w, _ = img.size
    px = lambda x, y: img.getpixel((x, y))[:3]
    diff = lambda a, b: sum(abs(p - q) for p, q in zip(a, b))
    y, base = TOP - 2, TOP - 1          # fila 72: las marcas altas la cubren y el bloque del emblema (filas 0-71) no
    if diff(px(PADX + 3, base), px(PADX + 3, y)) < 60:
        return "na"
    digest = hashlib.sha256(info["pub"]).digest()
    for i in range((w - 2 * PADX) // 6):
        x = PADX + 6 * i
        tall = diff(px(x, y), px(x + 3, y)) > 90
        if tall != bool((digest[(i // 8) % 32] >> (i % 8)) & 1):
            return "mismatch"
    return "match"


# ============================================================ variables
def find_variables(*texts):
    seen = []
    for t in texts:
        for m in VAR_RE.finditer(t or ""):
            if m.group(1) not in seen:
                seen.append(m.group(1))
    return seen


def fill(text, values):
    return VAR_RE.sub(lambda m: str(values.get(m.group(1), m.group(0))), text)


# ============================================================ etiqueta (imagen)
def F(size, bold=False):
    """IBM Plex Mono (licencia SIL OFL, incluida en fonts/). Si falta, usa DejaVu Sans Mono."""
    p = os.path.join(FONT_DIR, "IBMPlexMono-Bold.ttf" if bold else "IBMPlexMono-Regular.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    try:
        return ImageFont.truetype("DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def _fit(d, text, font, maxw):
    if d.textlength(text, font=font) <= maxw:
        return text
    while text and d.textlength(text + "…", font=font) > maxw:
        text = text[:-1]
    return text + "…"


def _balanced2(d, text, f, maxw):
    words, best = text.split(), None
    for i in range(1, len(words)):
        l1, l2 = " ".join(words[:i]), " ".join(words[i:])
        w1, w2 = d.textlength(l1, font=f), d.textlength(l2, font=f)
        if w1 <= maxw and w2 <= maxw and (best is None or max(w1, w2) < best[0]):
            best = (max(w1, w2), [l1, l2])
    return best[1] if best else None


def fit_title(d, text, maxw):
    """22 px en una línea si cabe; si no, dos líneas balanceadas a 18/16/14 px; si aún no cabe, trunca la segunda."""
    if d.textlength(text, font=F(22, True)) <= maxw:
        return [text], F(22, True), 22, 46
    for size, step in ((18, 22), (16, 20), (14, 18)):
        f = F(size, True)
        lines = _balanced2(d, text, f, maxw)
        if lines:
            return lines, f, step, 52
    f = F(14, True)
    words, l1, i = text.split(), "", 0
    while i < len(words) and d.textlength((l1 + " " + words[i]).strip(), font=f) <= maxw:
        l1, i = (l1 + " " + words[i]).strip(), i + 1
    return [l1 or _fit(d, text, f, maxw), _fit(d, " ".join(words[i:]), f, maxw)], f, 18, 52


def _identicon_cell(d, kind, x, y, t, ink):
    if kind in (0, 5): d.pieslice([x - t, y - t, x + t, y + t], 0, 90, fill=ink)
    if kind in (1, 7): d.pieslice([x, y - t, x + 2 * t, y + t], 90, 180, fill=ink)
    if kind in (2, 5): d.pieslice([x, y, x + 2 * t, y + 2 * t], 180, 270, fill=ink)
    if kind in (3, 7): d.pieslice([x - t, y, x + t, y + 2 * t], 270, 360, fill=ink)
    if kind == 4: d.ellipse([x + 6, y + 6, x + t - 6, y + t - 6], fill=ink)


_MIRROR = {0: 1, 1: 0, 2: 3, 3: 2, 4: 4, 5: 7, 6: 6, 7: 5}


def emblem_cells(cells, accent, size=72):
    """Emblema 4x4 de cuartos de disco, simétrico. `cells` = 8 valores 0-6 (mitad izquierda; la derecha es el espejo)."""
    S = 4; N = size * S; t = 11 * size * S // 72; off = (N - 4 * t) // 2
    im = Image.new("RGB", (N, N), accent); d = ImageDraw.Draw(im)
    for r in range(4):
        for c in range(2):
            k = int(cells[r * 2 + c])
            _identicon_cell(d, k, off + c * t, off + r * t, t, INK)
            _identicon_cell(d, _MIRROR[k], off + (3 - c) * t, off + r * t, t, INK)
    return im.resize((size, size), Image.LANCZOS)


def emblem(digest, accent, size=72):
    """Emblema derivado de una huella (se usa como sello mini del autor)."""
    return emblem_cells([digest[1 + i] % 7 for i in range(8)], accent, size)


# --- emblema propio de cada tarjeta: forma (g) + tono (h). Se guarda en el bloque público y se mantiene entre versiones.
def emblem_code(e):
    return f"{e['h']:.3f}:{e['g']}"


def parse_emblem_code(code):
    m = re.fullmatch(r"([01](?:\.\d+)?):([0-6]{8})", code.strip())
    if not m or not 0 <= float(m.group(1)) <= 1:
        raise ValueError("Código de emblema no válido: usa el formato tono:figura, p. ej. 0.412:31640253.")
    return {"h": round(float(m.group(1)), 3), "g": m.group(2)}


def valid_emblem(e):
    return isinstance(e, dict) and isinstance(e.get("h"), (int, float)) and 0 <= e["h"] <= 1 and isinstance(e.get("g"), str) and re.fullmatch(r"[0-6]{8}", e["g"])


def random_emblem(rng, hue=None):
    while True:
        g = "".join(str(rng.randrange(7)) for _ in range(8))
        if g.count("6") <= 2:                      # 6 = casilla vacía; evita emblemas casi en blanco
            break
    return {"h": round(rng.random() if hue is None else hue, 3), "g": g}


def emblem_distance(a, b):
    dh = abs(a["h"] - b["h"]); dh = min(dh, 1 - dh) * 2            # 0 a 1, circular
    ds = sum(x != y for x, y in zip(a["g"], b["g"])) / 8
    return 0.65 * dh + 0.35 * ds


def choose_emblem(existing, rng, hue=None, tries=300):
    """Entre muchos candidatos, el más distinto de los emblemas que ya existen (tono y figura)."""
    best, bd = None, -1.0
    for _ in range(tries):
        c = random_emblem(rng, hue)
        dist = min((emblem_distance(c, e) for e in existing), default=1.0)
        if dist > bd:
            best, bd = c, dist
    return best


def scan_emblems(folder):
    found = []
    for f in glob.glob(os.path.join(folder or ".", "**", "*.png"), recursive=True):
        try:
            e = parse(read_card(f))["public"].get("emblem")
        except (ValueError, OSError):
            continue
        if valid_emblem(e):
            found.append({"h": float(e["h"]), "g": e["g"]})
    return found


def q_monogram(accent, size=72):
    """Monograma Q: anillo con cola. Sello elegido por el autor (no depende de la clave)."""
    S = 4; N = size * S; c = N // 2; u = N / 72
    R, r = 19 * u, 10 * u
    im = Image.new("RGB", (N, N), accent); d = ImageDraw.Draw(im)
    d.ellipse([c - R, c - R, c + R, c + R], fill=INK); d.ellipse([c - r, c - r, c + r, c + r], fill=accent)
    a = math.radians(45); w = 4.5 * u
    x0, y0 = c + (r - 2 * u) * math.cos(a), c + (r - 2 * u) * math.sin(a)
    x1, y1 = c + (R + 5 * u) * math.cos(a), c + (R + 5 * u) * math.sin(a)
    dx, dy = -math.sin(a) * w, math.cos(a) * w
    d.polygon([(x0 + dx, y0 + dy), (x1 + dx, y1 + dy), (x1 - dx, y1 - dy), (x0 - dx, y0 - dy)], fill=INK)
    return im.resize((size, size), Image.LANCZOS)


def _ticks(d, digest, x0, x1, base, color):
    """Regla de huella: marcas de 3 px o 1 px de alto según los bits de la huella."""
    for i in range((x1 - x0) // 6):
        h = 3 if (digest[(i // 8) % 32] >> (i % 8)) & 1 else 1
        d.rectangle([x0 + 6 * i, base - h + 1, x0 + 6 * i + 1, base], fill=color)
    d.rectangle([x0, base, x1 - 1, base], fill=color)


def _icon_seal(d, cx, cy, c):
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], outline=c, width=2)
    d.line([cx - 4, cy, cx - 1, cy + 3, cx + 4, cy - 3], fill=c, width=2)


def _icon_lock(d, cx, cy, c):
    d.rounded_rectangle([cx - 6, cy - 1, cx + 6, cy + 8], radius=2, fill=c)
    d.arc([cx - 4, cy - 9, cx + 4, cy + 1], 180, 360, fill=c, width=2)


def _place(img, box, stream, pal, T=6):
    x0, y0, x1, y1 = box
    dw, rows = x1 - x0, y1 - y0
    px = math.ceil(len(stream) / 3)
    assert dw * rows >= px, "no cabe"
    d = ImageDraw.Draw(img); rng = random.Random(zlib.crc32(stream))
    for ty in range(y0, y1, T):
        for tx in range(x0, x1, T):
            d.rectangle([tx, ty, min(tx + T, x1) - 1, min(ty + T, y1) - 1], fill=pal[rng.randrange(5)])
    padded = stream + b"\0" * (px * 3 - len(stream))
    full, rem = px // dw, px % dw
    if full:
        img.paste(Image.frombytes("RGB", (dw, full), padded[:full * dw * 3]), (x0, y0))
    if rem:
        img.paste(Image.frombytes("RGB", (rem, 1), padded[full * dw * 3:]), (x0, y0 + full))


def _darken(c, k=0.72):
    h, sat, v = colorsys.rgb_to_hsv(*[x / 255 for x in c])
    return _hsv(h, min(1.0, sat * 1.15), v * k)


def _lum(c):
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = [f(x / 255) for x in c]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _block_light(h, bg=(248, 250, 252), target=2.4):
    """Color del emblema sobre fondo claro: el más vivo del tono que aún contrasta lo suficiente con el fondo."""
    for v in [i / 100 for i in range(90, 44, -3)]:
        for sat in (.62, .72, .82):
            c = _hsv(h, sat, v)
            if _contrast(c, bg) >= target:
                return c
    return _hsv(h, .82, .45)


THEMES = {
    "dark": dict(bg=INK, title=(240, 244, 248), sub=(170, 182, 196), foot=(150, 164, 180), foot_band=(238, 242, 246), border=NEUTRAL,
                 block=lambda h: _hsv(h, .6, .95), chip_sv=(.45, .95), lock=(240, 200, 110), unsigned=(140, 152, 166),
                 pal=lambda h: [_hsv(h + i * .035, .32, .22 + .045 * i) for i in range(5)], band=lambda h: _hsv(h, .50, .40), ui=lambda c: c),
    "light": dict(bg=(248, 250, 252), title=INK, sub=(84, 96, 110), foot=(92, 104, 118), foot_band=INK, border=(170, 181, 194),
                  block=_block_light, chip_sv=(.50, .93), lock=(160, 105, 10), unsigned=(112, 124, 138),
                  pal=lambda h: [_hsv(h + i * .035, .10 + .025 * i, .95 - .02 * i) for i in range(5)], band=lambda h: _hsv(h, .30, .93), ui=_darken),
}


def render_card(stream, identity=None, theme="dark"):
    """Dibuja la etiqueta a partir de un flujo ya empaquetado. `identity` aporta el color y el sello del autor.
    `theme` ('dark' o 'light') solo cambia los colores decorativos; la zona de datos no se toca."""
    T = THEMES[theme]
    info = parse(stream); pub = info["public"]; signed = info["signed"]
    title = pub.get("title") or ""; hidden = not title
    category, version, author = pub.get("category", ""), pub.get("version", ""), pub.get("author", "")
    px = math.ceil(len(stream) / 3); dw = W - 2 * PADX
    rows = max(MIN_ROWS, math.ceil(px / dw)); H = TOP + rows + BOT
    box = (PADX, TOP, W - PADX, TOP + rows)

    # autor: color y sello mini (regla, icono de firma y marca junto al nombre)
    brand_color = identity.get("color") if identity else None
    mark = identity.get("mark", "auto") if identity else "auto"
    if signed:
        digest = hashlib.sha256(info["pub"]).digest()
        accent = brand_color or _hsv(digest[0] / 255, .6, .95)
    else:
        digest = hashlib.sha256(title.encode("utf-8")).digest(); mark = "auto"; accent = T["unsigned"]
    ui_accent = T["ui"](accent) if signed else accent                    # en fondo claro, el color del autor se oscurece para que se lea

    # emblema propio de la tarjeta (bloque grande). Si la tarjeta no lo trae, se deriva de la huella o del título.
    emb = pub.get("emblem")
    if not valid_emblem(emb):
        emb = {"h": digest[0] / 255, "g": "".join(str(digest[1 + i] % 7) for i in range(8))}
    block = T["block"](emb["h"])
    pal = T["pal"](emb["h"])                                             # el relleno de datos toma el tono de la tarjeta

    img = Image.new("RGB", (W, H), T["bg"])
    _place(img, box, stream, pal)
    img.paste(emblem_cells(emb["g"], block), (0, 0))
    d = ImageDraw.Draw(img)

    x0, maxw = 84, W - 84 - 12
    lines, tf, step, sub_y = fit_title(d, title if not hidden else "Tarjeta privada", maxw)
    y = 12 if len(lines) == 1 else 5
    for ln in lines:
        d.text((x0, y), ln, font=tf, fill=T["title"]); y += step
    hue_c = pub.get("cat_hue")
    if category and hue_c is None:
        hue_c = CAT_PALETTE[zlib.crc32(category.encode()) % len(CAT_PALETTE)]
    x = x0
    if category:
        cf = F(10, True); cw = d.textlength(category, font=cf)
        d.rounded_rectangle([x, sub_y, x + cw + 12, sub_y + 17], radius=8, fill=_hsv(hue_c, *T["chip_sv"]))
        d.text((x + 6, sub_y + 3), category, font=cf, fill=INK); x += cw + 12 + 8
    n_icons = (1 if signed else 0) + (1 if info["encrypted"] else 0)
    limit = W - 12 - 24 * n_icons
    f11 = F(11)
    ver_txt = (f"v{version}" if version else "") + ("  ·" if version and author else "")
    if ver_txt:
        d.text((x, sub_y + 2), ver_txt, font=f11, fill=T["sub"]); x += d.textlength(ver_txt, font=f11) + 8
    if author:
        if signed:                                           # marca mini del autor (Q o emblema de su clave)
            mm = (q_monogram(accent, 72) if mark == "q" else emblem(digest, accent, 72)).resize((14, 14), Image.LANCZOS)
            img.paste(mm, (int(x), sub_y + 2)); x += 14 + 6
        d.text((x, sub_y + 2), _fit(d, author, f11, max(limit - x, 20)), font=f11, fill=T["sub"])
    rx = W - 22
    if signed:
        _icon_seal(d, rx, sub_y + 9, ui_accent); rx -= 24
    if info["encrypted"]:
        _icon_lock(d, rx, sub_y + 8, T["lock"])
    _ticks(d, digest, PADX, W - PADX, TOP - 1, ui_accent)

    ff = F(10); cid = hashlib.sha256(stream).hexdigest()[:8].upper(); fcol = T["foot"]
    if category:                                   # franja inferior con el color de la categoría
        d.rectangle([0, H - BOT, W, H], fill=T["band"](hue_c)); fcol = T["foot_band"]
    status = " · ".join((["firmada"] if signed else []) + (["cifrada"] if info["encrypted"] else [])) or "sin firma"
    left_txt = f"ID {cid[:4]}-{cid[4:]}  ·  {status}"
    d.text((PADX + 2, H - BOT + 4), left_txt, font=ff, fill=fcol)
    r = f"{len(stream):,} bytes"; rw = d.textlength(r, font=ff)
    d.text((W - PADX - 2 - rw, H - BOT + 4), r, font=ff, fill=fcol)

    # silueta (esquina cortada) + hilo fino; la zona de datos queda intacta y opaca
    K = 4
    big = Image.new("L", (W * K, H * K), 0); bd = ImageDraw.Draw(big)
    bd.rounded_rectangle([0, 0, W * K - 1, H * K - 1], radius=12 * K, fill=255)
    bd.polygon([(0, 0), (CUT * K, 0), (0, CUT * K)], fill=0)
    rg = Image.new("L", (W * K, H * K), 0); rd = ImageDraw.Draw(rg)
    rd.rounded_rectangle([0, 0, W * K - 1, H * K - 1], radius=12 * K, outline=255, width=K)
    rd.line([(0, CUT * K), (CUT * K, 0)], fill=255, width=2 * K)
    rg = ImageChops.darker(rg, big)
    mask = big.resize((W, H), Image.LANCZOS); ring = rg.resize((W, H), Image.LANCZOS)
    mask.paste(255, box); ring.paste(0, box)
    img.paste(T["border"], (0, 0, W, H), ring)
    out = img.convert("RGBA"); out.putalpha(mask)
    return out, box


def save_card(stream, path, identity=None, theme="dark"):
    img, _ = render_card(stream, identity, theme)
    img.save(path, format="PNG", optimize=False)
    return img.size


def read_card(path):
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    if h <= TOP + BOT or w <= 2 * PADX:
        raise ValueError("La imagen no tiene las proporciones de una etiqueta de Prompts Encapsulados.")
    raw = img.crop((PADX, TOP, w - PADX, h - BOT)).convert("RGB").tobytes()
    return raw[:parse(raw)["end"]]


# ============================================================ categorías
def category_hue(category, cat_file=None, override=None):
    if override:
        return colorsys.rgb_to_hsv(*[c / 255 for c in hex_to_rgb(override)])[0]
    cf = cat_file or ("categorias.json" if os.path.exists("categorias.json") else None)
    if cf and os.path.exists(cf):
        m = json.load(open(cf, encoding="utf-8"))
        if category in m:
            return colorsys.rgb_to_hsv(*[c / 255 for c in hex_to_rgb(m[category])])[0]
    return CAT_PALETTE[zlib.crc32(category.encode()) % len(CAT_PALETTE)] if category else None



# ============================================================ lanzamientos firmados
def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def release_files(folder):
    """Archivos que forman un lanzamiento (rutas relativas con /). Se omiten los generados por `release` y la basura del sistema."""
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git", "node_modules"))
        for f in sorted(files):
            p = os.path.join(root, f)
            if os.path.islink(p) or f in (".DS_Store", "Thumbs.db"):
                continue
            rel = os.path.relpath(p, folder).replace(os.sep, "/")
            if rel in ("MANIFEST.json", "MANIFEST.json.sig", "SHA256SUMS.txt", "SHA256SUMS.txt.sig"):
                continue
            out.append(rel)
    return sorted(out)


def _safe_rel(path):
    return bool(path) and not path.startswith(("/", "\\")) and ".." not in path.split("/") and ":" not in path


def cmd_release(a):
    if not os.path.isdir(a.folder):
        raise ValueError("Esa carpeta no existe.")
    rels = release_files(a.folder)
    if not rels:
        raise ValueError("La carpeta no tiene archivos que publicar.")
    priv = [r for r in rels if r.lower().endswith(".pcid")]
    if priv:
        raise ValueError(f"Hay una clave privada (.pcid) dentro de la carpeta: {', '.join(priv)}. Sácala antes de publicar: una clave privada nunca debe viajar en un lanzamiento.")
    ident = load_identity(a.sign, a.key_password)
    files = [{"path": r, "sha256": _sha256_file(os.path.join(a.folder, r)), "size": os.path.getsize(os.path.join(a.folder, r))} for r in rels]
    manifest = {"format": "encapsulados-release", "v": 1, "name": a.name or os.path.basename(os.path.abspath(a.folder)), "version": a.version,
                "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "signer": {"name": ident["name"], "public": ident["pub"].hex(), "fingerprint": fingerprint(ident["pub"])}, "files": files}
    data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with open(os.path.join(a.folder, "MANIFEST.json"), "wb") as f:
        f.write(data)
    with open(os.path.join(a.folder, "MANIFEST.json.sig"), "wb") as f:
        f.write(ident["priv"].sign(data))
    sums = "".join(f"{x['sha256']}  {x['path']}\n" for x in files).encode("utf-8")
    with open(os.path.join(a.folder, "SHA256SUMS.txt"), "wb") as f:
        f.write(sums)
    with open(os.path.join(a.folder, "SHA256SUMS.txt.sig"), "wb") as f:      # también firmada: así se verifica con solo openssl + sha256sum
        f.write(ident["priv"].sign(sums))
    print(f"Lanzamiento {manifest['name']} {a.version} firmado: {len(files)} archivos, {sum(x['size'] for x in files) / 1024:,.1f} KB.")
    print(f"  MANIFEST.json + MANIFEST.json.sig, y SHA256SUMS.txt + SHA256SUMS.txt.sig (ambos firmados con la misma clave).")
    print(f"  Huella del firmante: {fingerprint(ident['pub'])}")
    print("  Publica esa huella (y tu .pem) por canales independientes del que reparte los archivos: sin eso, la firma no prueba quién eres.")


def cmd_verify_release(a):
    mp, sp = os.path.join(a.folder, "MANIFEST.json"), os.path.join(a.folder, "MANIFEST.json.sig")
    if not (os.path.exists(mp) and os.path.exists(sp)):
        raise ValueError("Faltan MANIFEST.json o MANIFEST.json.sig: esta carpeta no es un lanzamiento firmado.")
    data, sig = open(mp, "rb").read(), open(sp, "rb").read()
    try:
        man = json.loads(data.decode("utf-8"))
        assert man.get("format") == "encapsulados-release"
        pub = bytes.fromhex(man["signer"]["public"]); files = man["files"]
        assert len(pub) == 32 and isinstance(files, list)
    except (ValueError, KeyError, AssertionError, TypeError):
        raise ValueError("MANIFEST.json está dañado o no es un manifiesto de Prompts Encapsulados.")
    problems = 0
    fp = fingerprint(pub)
    try:
        assert len(sig) == 64
        Ed25519PublicKey.from_public_bytes(pub).verify(sig, data)
        print(f"[OK] Firma válida sobre el manifiesto de «{man.get('name')}» versión {man.get('version')} ({man.get('created')}).")
    except (AssertionError, InvalidSignature, ValueError):
        print("[!!] La firma del manifiesto NO es válida: el manifiesto fue modificado o la firma no corresponde a esa clave. No uses estos archivos.")
        problems += 1
    if man["signer"].get("fingerprint") != fp:
        print("[!!] La huella declarada en el manifiesto no coincide con su clave pública."); problems += 1
    trusted = load_trusted(a.trusted)
    if fp in trusted:
        print(f"[OK] Firmante de confianza: {trusted[fp]} (huella {fp}).")
    else:
        print(f"[--] Firmante desconocido: «{man['signer'].get('name')}» (huella {fp}). Que la firma sea válida no prueba quién es: compara esa huella con la que el autor publicó por un canal independiente.")
        if a.require_trusted:
            problems += 1
    sp2 = os.path.join(a.folder, "SHA256SUMS.txt"); sg2 = sp2 + ".sig"
    if os.path.exists(sp2):
        sums = open(sp2, "rb").read()
        esperado = "".join(f"{x.get('sha256')}  {x.get('path')}\n" for x in files).encode("utf-8")
        try:
            assert os.path.exists(sg2)
            Ed25519PublicKey.from_public_bytes(pub).verify(open(sg2, "rb").read(), sums)
            if sums != esperado:
                print("[!!] SHA256SUMS.txt tiene la firma pero no coincide con el manifiesto."); problems += 1
            else:
                print("[OK] SHA256SUMS.txt está firmado y coincide con el manifiesto.")
        except (AssertionError, InvalidSignature, ValueError):
            print("[!!] SHA256SUMS.txt NO tiene una firma válida (fue modificado o falta su .sig). No confíes en él."); problems += 1
    listed, bad, missing, ok = {}, [], [], 0
    for x in files:
        path = x.get("path", "")
        if not _safe_rel(path):
            print(f"[!!] Ruta no permitida en el manifiesto: {path!r}"); problems += 1; continue
        listed[path] = x
        full = os.path.join(a.folder, path)
        if not os.path.isfile(full):
            missing.append(path)
        elif os.path.getsize(full) != x.get("size") or _sha256_file(full) != x.get("sha256"):
            bad.append(path)
        else:
            ok += 1
    for p in missing:
        print(f"[!!] Falta: {p}")
    for p in bad:
        print(f"[!!] Modificado (no coincide con el manifiesto): {p}")
    extras = [r for r in release_files(a.folder) if r not in listed]
    if extras:
        print(f"[--] {len(extras)} archivo(s) que NO están en el manifiesto y no están respaldados por la firma: {', '.join(extras[:8])}" + (" ..." if len(extras) > 8 else ""))
        if a.strict:
            problems += 1
    if not (bad or missing):
        print(f"[OK] {ok} archivos íntegros: coinciden con el manifiesto firmado.")
    sys.exit(0 if problems == 0 and not bad and not missing else 1)


def cmd_pem(a):
    d = json.load(open(a.pub, encoding="utf-8"))
    if d.get("format") != "encapsulados-pub":
        raise ValueError("Ese archivo no es una clave pública de Prompts Encapsulados (.pub).")
    pub = bytes.fromhex(d["public"])
    out = a.output or os.path.splitext(a.pub)[0] + ".pem"
    write_pem(pub, out)
    print(f"Clave pública en formato PEM: {out}   (huella {fingerprint(pub)})")


# ============================================================ línea de comandos
def cmd_keygen(a):
    prefix = a.output or slug(a.name).replace("-", "_")
    pw = None
    if a.ask_password:
        pw = getpass.getpass("Contraseña para proteger la clave privada: ")
        if pw != getpass.getpass("Repite la contraseña: "):
            sys.exit("Las contraseñas no coinciden.")
    try:
        pub = keygen(a.name, prefix, pw, a.color, a.mark)
    except FileExistsError:
        sys.exit(f"Ya existe {prefix}.pcid; no lo sobrescribo. Elige otro nombre con -o.")
    print(f"Identidad creada para «{a.name}»")
    print(f"  Privada (SECRETA): {prefix}.pcid   -> no la compartas ni la subas a ningún lado")
    print(f"  Pública:           {prefix}.pub    -> esta sí se comparte, por un canal de confianza")
    print(f"  Pública (PEM):     {prefix}.pem    -> la misma clave, para verificar con OpenSSL")
    print(f"  Huella:            {fingerprint(pub)}")
    print(f"  Sello:             {'monograma Q' if a.mark == 'q' else 'emblema derivado de tu clave'}" + (f", color {a.color.upper()}" if a.color else ""))


def pick_emblem(a, out_dir):
    """Emblema de la tarjeta: uno indicado, el de una versión anterior, o el más distinto de los que ya hay en la carpeta."""
    if a.emblem:
        return parse_emblem_code(a.emblem)
    if a.emblem_from:
        e = parse(read_card(a.emblem_from))["public"].get("emblem")
        if not valid_emblem(e):
            raise ValueError("Esa tarjeta no trae emblema (es anterior a esta versión).")
        return {"h": round(float(e["h"]), 3), "g": e["g"]}
    rng = random.Random(a.seed) if a.seed is not None else random.Random()
    hue = colorsys.rgb_to_hsv(*[c / 255 for c in hex_to_rgb(a.emblem_color)])[0] if a.emblem_color else None
    return choose_emblem(scan_emblems(a.library or out_dir), rng, hue)


def cmd_emblemas(a):
    rng = random.Random(a.seed) if a.seed is not None else random.Random()
    existing = scan_emblems(a.library) if a.library else []
    cands = []
    for _ in range(a.n):
        cands.append(choose_emblem(existing + cands, rng))
    per, cw, ch = 6, 116, 150
    rows = math.ceil(len(cands) / per)
    sheet = Image.new("RGB", (per * cw + 16, rows * ch + 16), (236, 239, 243)); d = ImageDraw.Draw(sheet)
    for i, e in enumerate(cands):
        x, y = 16 + (i % per) * cw - 8, 16 + (i // per) * ch - 8
        sheet.paste(emblem_cells(e["g"], _hsv(e["h"], .6, .95), 96), (x, y))
        d.text((x, y + 102), f"{i + 1}", font=F(14, True), fill=INK); d.text((x + 24, y + 106), emblem_code(e), font=F(9), fill=(91, 102, 115))
    out = a.output or "candidatos.png"; sheet.save(out)
    print(f"{len(cands)} candidatos en {out}" + (f" (distintos de los {len(existing)} emblemas de {a.library})" if a.library else ""))
    for i, e in enumerate(cands):
        print(f"  {i + 1:>2}: --emblem {emblem_code(e)}")


def cmd_encode(a):
    if a.input.endswith(".json"):
        cfg = json.load(open(a.input, encoding="utf-8"))
    else:
        cfg = {"prompt": open(a.input, encoding="utf-8").read()}
    if a.system_file:
        cfg["system"] = open(a.system_file, encoding="utf-8").read()
    for k in ("title", "version", "author", "description", "model", "category"):
        v = getattr(a, k)
        if v is not None:
            cfg[k] = v
    if a.tags is not None:
        cfg["tags"] = [t.strip() for t in a.tags.split(",") if t.strip()]
    title = cfg.get("title") or cfg.get("name") or os.path.splitext(os.path.basename(a.input))[0]
    password = a.password
    if a.ask_password:
        password = getpass.getpass("Contraseña de la tarjeta: ")
        if password != getpass.getpass("Repite la contraseña: "):
            sys.exit("Las contraseñas no coinciden.")
    ident, signer = None, None
    if a.sign:
        ident = load_identity(a.sign, a.key_password); signer = ident["priv"]
        cfg.setdefault("author", ident["name"])
    category = cfg.get("category", "")
    out_dir = a.output if (a.output and (a.output.endswith(("/", os.sep)) or os.path.isdir(a.output))) else (os.path.dirname(a.output) if a.output else "") or "."
    emb = pick_emblem(a, out_dir)
    public = build_public(title, category, cfg.get("version", "1.0"), cfg.get("author", ""), cfg.get("tags"),
                          cfg.get("model", ""), category_hue(category, a.categorias, a.category_color) if category else None, a.hide_title, emb)
    payload = build_payload(cfg["prompt"], cfg.get("system", ""), cfg.get("description", ""), cfg.get("variables"))
    for f in review_text((payload["system"] or "") + "\n" + payload["prompt"]):          # higiene del autor: avisa antes de firmar
        if f["sev"] != "baja":
            print(f"AVISO al crear [{f['sev']}]: {f['msg']}", file=sys.stderr)
    if password and weak_password(password):
        print("AVISO: " + weak_password(password), file=sys.stderr)
    stream = pack(payload, public, password, signer)
    cid = hashlib.sha256(stream).hexdigest()[:8].lower()
    fname = (f"tarjeta-privada_{cid}" if a.hide_title else f"{slug(title)}_v{public['version']}") + ".encapsulado.png"
    out = a.output or fname
    if out.endswith(("/", os.sep)) or os.path.isdir(out):       # -o es una carpeta: se crea si falta
        os.makedirs(out, exist_ok=True)
        out = os.path.join(out, fname)
    w, h = save_card(stream, out, ident, a.theme)
    txt = len((payload["system"] or "") + payload["prompt"])
    print(f"OK  {out}  {w}x{h} px  |  {len(stream):,} bytes  |  {txt:,} caracteres de prompt")
    print("Cifrada: " + ("sí" if password else "no") + "   Firmada: " + (f"sí (huella {fingerprint(parse(stream)['pub'])})" if signer else "no"))
    print(f"Emblema: {emblem_code(emb)}   (para otra versión de este prompt: --emblem-from {out})")
    vs = find_variables(payload["system"], payload["prompt"])
    if vs:
        print("Variables detectadas:", ", ".join(vs))


def cmd_inspect(a):
    stream = read_card(a.card); info = parse(stream)
    st, msg = describe_signature(info, load_trusted(a.trusted))
    p = info["public"]
    print(f"Título:     {p.get('title') or '(privado)'}")
    print(f"Categoría:  {p.get('category') or '-'}   Versión: {p.get('version') or '-'}   Autor declarado: {p.get('author') or '-'}")
    print(f"Etiquetas:  {', '.join(p.get('tags') or []) or '-'}")
    print(f"Cifrada:    {'sí' if info['encrypted'] else 'no'}   Tamaño: {len(stream):,} bytes")
    print(("[OK] " if st == "valid" else "[!!] " if st == "invalid" else "[--] ") + msg)
    vs = visual_status(a.card, info)
    if vs != "na":
        print(("[OK] Apariencia: coincide con la clave que firmó." if vs == "match" else "[!!] Apariencia: NO coincide con la clave que firmó (posible imitación)."))


def cmd_verify(a):
    info = parse(read_card(a.card))
    st, msg = describe_signature(info, load_trusted(a.trusted))
    print(("[OK] " if st == "valid" else "[!!] " if st == "invalid" else "[--] ") + msg)
    vs = visual_status(a.card, info)
    if vs == "mismatch":
        print("[!!] Apariencia: NO coincide con la clave que firmó (posible imitación).")
    sys.exit(0 if st == "valid" and vs != "mismatch" else 1)


def cmd_decode(a):
    stream = read_card(a.card); info = parse(stream)
    st, msg = describe_signature(info, load_trusted(a.trusted))
    print(msg, file=sys.stderr)
    if st == "invalid" and not a.force:
        sys.exit("No abro tarjetas con firma no válida (usa --force si sabes lo que haces).")
    pw = a.password
    if is_encrypted(stream) and not pw:
        pw = getpass.getpass("Contraseña: ")
    p = unpack(stream, pw); pubm = info["public"]
    vs = visual_status(a.card, info)
    if vs == "mismatch":
        print("AVISO: la apariencia de la tarjeta no coincide con la clave que la firmó (posible imitación).", file=sys.stderr)
    rev = review_text((p.get("system") or "") + "\n" + (p.get("prompt") or ""))
    for f in rev:
        print(f"REVISIÓN [{f['sev']}]: {f['msg']}", file=sys.stderr)
    values = dict(kv.split("=", 1) for kv in (a.set or []))
    for k in find_variables(p["system"], p["prompt"]):
        values.setdefault(k, p.get("variables", {}).get(k, {}).get("default") or "{{%s}}" % k)
    if a.json:
        print(json.dumps({"public": pubm, **p}, ensure_ascii=False, indent=2)); return
    print(f"# {pubm.get('title') or 'Tarjeta privada'}  (v{pubm.get('version', '')})  {pubm.get('author', '')}")
    if p["system"]:
        print("\n--- SISTEMA ---\n" + fill(p["system"], values))
    print("\n--- PROMPT ---\n" + fill(p["prompt"], values))


def cmd_index(a):
    files = sorted(glob.glob(os.path.join(a.folder, "**", "*.png"), recursive=True)); trusted = load_trusted(a.trusted); rows = []
    for f in files:
        try:
            info = parse(read_card(f))
        except (ValueError, OSError):
            continue
        p = info["public"]; st = signature_status(info)
        who = "-"
        if info["signed"]:
            fp = fingerprint(info["pub"]); who = trusted.get(fp, f"desconocido ({fp[:9]})")
        rows.append({"archivo": os.path.relpath(f, a.folder), "bytes": os.path.getsize(f), "titulo": p.get("title") or "(privado)", "categoria": p.get("category", ""),
                     "version": p.get("version", ""), "autor": who, "firma": {"valid": "válida", "invalid": "NO VÁLIDA", "none": "sin firma"}[st],
                     "cifrada": "sí" if info["encrypted"] else "no", "etiquetas": ", ".join(p.get("tags") or []),
                     "emblema": emblem_code(p["emblem"]) if valid_emblem(p.get("emblem")) else ""})
    rows.sort(key=lambda r: (r["categoria"].lower(), r["titulo"].lower()))
    if not rows:
        print("No encontré tarjetas de Prompts Encapsulados en esa carpeta."); return
    cols = ["titulo", "categoria", "version", "autor", "firma", "cifrada"]
    wd = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print("  ".join(c.upper().ljust(wd[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r[c]).ljust(wd[c]) for c in cols))
    total = sum(r["bytes"] for r in rows)
    print(f"\n{len(rows)} tarjetas · {total / 1024:,.1f} KB en total" + (f" ({total / 1048576:.2f} MB)" if total >= 1048576 else ""))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        print(f"Índice guardado en {a.csv}")


def main():
    ap = argparse.ArgumentParser(prog="encapsulados", description="Prompts Encapsulados: cada prompt en una etiqueta PNG, comprimido, cifrable y firmado")
    ap.add_argument("--version", action="version", version=f"encapsulados {__version__} (formato v{VERSION})")
    sub = ap.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("keygen", help="crear tu identidad de firma (.pcid privada + .pub pública)")
    k.add_argument("name", help="nombre del autor, p. ej. AppqIA")
    k.add_argument("-o", "--output", help="prefijo de los archivos (por defecto, el nombre)")
    k.add_argument("--color", metavar="#RRGGBB", help="color de tu marca (si no, sale de tu clave)")
    k.add_argument("--mark", choices=["auto", "q"], default="auto", help="sello: 'auto' (emblema de tu clave) o 'q' (monograma Q)")
    k.add_argument("--ask-password", action="store_true", help="proteger la clave privada con contraseña")
    k.set_defaults(fn=cmd_keygen)

    e = sub.add_parser("encode", help="crear una tarjeta")
    e.add_argument("input", help="archivo .txt/.md con el prompt, o .json con todos los campos")
    e.add_argument("-o", "--output", help="archivo o carpeta de salida (por defecto: titulo_vX.png)")
    e.add_argument("--system-file")
    for f in ("title", "version", "author", "description", "model", "category"):
        e.add_argument(f"--{f}")
    e.add_argument("--tags", help="etiquetas separadas por comas")
    e.add_argument("--category-color", metavar="#RRGGBB", help="color de esta categoría (si no, paleta fija o categorias.json)")
    e.add_argument("--categorias", metavar="ARCHIVO.json", help="mapa {categoría: #color} para mantener colores estables")
    e.add_argument("--password", help="cifrar la tarjeta con esta contraseña")
    e.add_argument("--ask-password", action="store_true", help="pedir la contraseña sin mostrarla")
    e.add_argument("--sign", metavar="CLAVE.pcid", help="firmar con tu identidad")
    e.add_argument("--key-password", help="contraseña de la clave de firma (si la protegiste)")
    e.add_argument("--hide-title", action="store_true", help="tarjeta privada: sin título, categoría ni autor visibles")
    e.add_argument("--theme", choices=["dark", "light"], default="dark", help="colores de la etiqueta: oscuro (por defecto) o claro. Solo cambia el aspecto")
    e.add_argument("--emblem", metavar="TONO:FIGURA", help="usar este emblema (lo imprime encode y lo lista el comando 'emblemas')")
    e.add_argument("--emblem-from", metavar="TARJETA.png", help="mismo emblema que otra tarjeta (para una nueva versión del mismo prompt)")
    e.add_argument("--emblem-color", metavar="#RRGGBB", help="fijar el tono del emblema (la figura se elige distinta a las existentes)")
    e.add_argument("--library", metavar="CARPETA", help="carpeta con tus tarjetas, para no repetir emblemas (por defecto, la carpeta de salida)")
    e.add_argument("--seed", type=int, help="semilla para que la elección del emblema sea reproducible")
    e.set_defaults(fn=cmd_encode)

    m = sub.add_parser("emblemas", help="generar una hoja de candidatos de emblema para elegir a ojo")
    m.add_argument("-n", type=int, default=12, help="cuántos candidatos (por defecto 12)")
    m.add_argument("-o", "--output", help="imagen de salida (por defecto candidatos.png)")
    m.add_argument("--library", metavar="CARPETA", help="evitar parecerse a los emblemas de esta carpeta")
    m.add_argument("--seed", type=int)
    m.set_defaults(fn=cmd_emblemas)

    i = sub.add_parser("inspect", help="ver los datos públicos y el estado de la firma sin abrir el contenido")
    i.add_argument("card"); i.add_argument("--trusted", action="append", metavar="AUTOR.pub")
    i.set_defaults(fn=cmd_inspect)

    v = sub.add_parser("verify", help="comprobar la firma")
    v.add_argument("card"); v.add_argument("--trusted", action="append", metavar="AUTOR.pub")
    v.set_defaults(fn=cmd_verify)

    d = sub.add_parser("decode", help="leer una tarjeta")
    d.add_argument("card")
    d.add_argument("--password")
    d.add_argument("--set", action="append", metavar="VAR=valor")
    d.add_argument("--trusted", action="append", metavar="AUTOR.pub")
    d.add_argument("--force", action="store_true", help="abrir aunque la firma no sea válida")
    d.add_argument("--json", action="store_true")
    d.set_defaults(fn=cmd_decode)

    rl = sub.add_parser("release", help="firmar un lanzamiento: manifiesto con las sumas de todos los archivos + firma")
    rl.add_argument("folder", help="carpeta con los archivos a publicar")
    rl.add_argument("--sign", required=True, metavar="CLAVE.pcid", help="tu identidad de firma")
    rl.add_argument("--version", required=True, help="versión, p. ej. 1.0.0")
    rl.add_argument("--name", help="nombre del producto (por defecto, el de la carpeta)")
    rl.add_argument("--key-password", help="contraseña de la clave de firma (si la protegiste)")
    rl.set_defaults(fn=cmd_release)

    vr = sub.add_parser("verify-release", help="verificar un lanzamiento firmado: firma, firmante y sumas de cada archivo")
    vr.add_argument("folder")
    vr.add_argument("--trusted", action="append", metavar="AUTOR.pub", help="clave pública del autor, obtenida por un canal independiente")
    vr.add_argument("--require-trusted", action="store_true", help="fallar si el firmante no es uno de los de --trusted")
    vr.add_argument("--strict", action="store_true", help="fallar también si hay archivos que no están en el manifiesto")
    vr.set_defaults(fn=cmd_verify_release)

    pm = sub.add_parser("pem", help="convertir un .pub de Prompts Encapsulados a PEM (para verificar con OpenSSL)")
    pm.add_argument("pub"); pm.add_argument("-o", "--output")
    pm.set_defaults(fn=cmd_pem)

    x = sub.add_parser("index", help="listar las tarjetas de una carpeta (título, categoría, autor, firma)")
    x.add_argument("folder"); x.add_argument("--trusted", action="append", metavar="AUTOR.pub")
    x.add_argument("--csv", metavar="INDICE.csv", help="guardar también como CSV")
    x.set_defaults(fn=cmd_index)

    a = ap.parse_args()
    try:
        a.fn(a)
    except (ValueError, OSError, KeyError) as ex:
        sys.exit(f"Error: {ex}")


if __name__ == "__main__":
    main()
