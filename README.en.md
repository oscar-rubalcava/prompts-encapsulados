<p align="center">
  <img src="marca/encapsulados_icono_256.png" alt="Prompts Encapsulados" width="96">
</p>

<h1 align="center">Prompts Encapsulados</h1>
<p align="center"><i>Encapsulated Prompts</i></p>
<p align="center"><b>Prompts you can verify.</b><br>
Store a prompt in a PNG label: compressed, password-encrypted, signed by its author and easy to find in your library. No server, no account.</p>

<p align="center">
  <a href="https://oscar-rubalcava.github.io/prompts-encapsulados/app/"><img alt="Live demo" src="https://img.shields.io/badge/demo-live-2ea44f"></a>
  <a href="https://github.com/oscar-rubalcava/prompts-encapsulados/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/oscar-rubalcava/prompts-encapsulados/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Status: beta" src="https://img.shields.io/badge/status-beta-orange">
</p>

<p align="center"><a href="README.md">Español</a> · <a href="https://oscar-rubalcava.github.io/prompts-encapsulados/">Website</a> · <a href="https://oscar-rubalcava.github.io/prompts-encapsulados/app/"><b>Try the demo</b></a> · <a href="docs/FORMATO.md">Format spec (ES)</a> · <a href="docs/SEGURIDAD.md">Security (ES)</a></p>

<p align="center"><img src="assets/demo.gif" alt="Prompts Encapsulados demo: open a card, verify its signature, fill variables, review risks and use the library" width="760"></p>

## What problem does it solve?

Prompts travel as loose text in chats and documents. You cannot tell **who** made one, whether someone **changed** it, or whether it hides **dangerous instructions or invisible characters** — and with hundreds of files it is hard to **find** the right one. Prompts Encapsulados packs a prompt into an image that can be sent like any file, and that the receiver can **verify** before using it.

## Try it in 30 seconds

1. Open the **[live demo](https://oscar-rubalcava.github.io/prompts-encapsulados/app/)** (everything runs in your browser; nothing is uploaded).
2. Download a card from [`ejemplos/`](ejemplos/) and drag it into the demo. The encrypted card's password is `demo1234`.
3. Import [`ejemplos/demo_appqia.pub`](ejemplos/demo_appqia.pub) and open it again: it goes from “unknown author” to “trusted”.
4. Try `resumen-de-correos-ejemplo-con-riesgos` and `actualizacion-de-precios` to see it flag hidden text and an imitation.

## What is included

- **Ed25519 signature** over all content and public data; trusted-authors list and a warning when someone impersonates a trusted author.
- **Optional encryption:** AES-256-GCM with PBKDF2-HMAC-SHA256 (600,000 iterations).
- **Signed public block** (title, category, tags): the library indexes even encrypted cards without a password.
- **Library** with search, filters, total size and optional local storage in the browser.
- **Text risk review:** reveals hidden characters, decodes invisible text and flags suspicious instructions.
- **Imitation detection:** checks that a card's look matches the key that signed it.
- **No network:** the decoder cannot connect to any address (CSP).
- **Signed releases**, verifiable with just `openssl` ([guide, ES](docs/LANZAMIENTOS.md)).
- **Open, documented format** ([spec, ES](docs/FORMATO.md)): write your own reader.

## Name
The official name is **Prompts Encapsulados** (Spanish for “encapsulated prompts”); the short name is **Encapsulados**. The command is `encapsulados` and cards are saved as `title_v1.0.encapsulado.png`.

## Install and use

Requires Python 3.10+.

```bash
git clone https://github.com/oscar-rubalcava/prompts-encapsulados.git && cd prompts-encapsulados
pip install cryptography pillow

# 1) your signing identity (once). Keep the .pcid secret; share the .pub
python3 encapsulados.py keygen MyBrand --color "#FBB43F"

# 2) create a card
python3 encapsulados.py encode ejemplo_prompt.json --sign mybrand.pcid --category Sales -o my_cards/
#    add --ask-password to encrypt it, or --hide-title for a private card

# 3) inspect and read it
python3 encapsulados.py inspect my_cards/asistente-de-punto-de-venta_v1.0.encapsulado.png --trusted mybrand.pub
python3 encapsulados.py decode  my_cards/asistente-de-punto-de-venta_v1.0.encapsulado.png --set nombre_negocio="My shop"

# 4) your library in the terminal (with total KB)
python3 encapsulados.py index my_cards/ --trusted mybrand.pub
```

To open cards with a UI, open `encapsulados.html` in your browser (or use the live demo). **Send cards as documents**, not as photos: messaging apps may recompress images and corrupt them.

> The command-line interface and the documentation are currently in Spanish. Translations and English docs are welcome.

## Security: what it does and what it does not

- An opened card **can be copied**: The tool does not prevent that. It makes a **forgery detectable** and a **dangerous prompt noticeable** before you use it.
- The signature proves nobody touched the card, **not who owns the key**: compare the fingerprint with the one the author published through another channel.
- The risk review is a **heuristic**: it can fail both ways.
- **Status: beta, no external audit.** It uses standard primitives (Ed25519, AES-GCM, PBKDF2), but review it before trusting it with anything critical.

Full threat model: [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) (Spanish). To report a vulnerability: [`SECURITY.md`](SECURITY.md).

## Roadmap

- [ ] Create cards in the browser (today creation is command-line only)
- [ ] Recipient-bound encryption (public key), no shared password
- [ ] Expiry and a signed revocation list
- [ ] Readers in other languages (JavaScript/Node, Rust, Go)
- [ ] External audit of the cryptography

## Contributing

Ideas, reports and tests are welcome: see [`CONTRIBUTING.md`](CONTRIBUTING.md). If you change the format, update [`docs/FORMATO.md`](docs/FORMATO.md) and bump the version.

## License and credits

- Code and documentation: **Apache-2.0** ([`LICENSE`](LICENSE), [`NOTICE`](NOTICE)).
- The **name “Prompts Encapsulados”, the logo and the visual identity** are not covered by that license: see [`marca/LEEME.md`](marca/LEEME.md).
- Typeface **IBM Plex Mono** © IBM Corp., SIL OFL 1.1 ([`fonts/IBMPlexMono-OFL.txt`](fonts/IBMPlexMono-OFL.txt)). “IBM Plex” is a reserved name of IBM.

Created by **Oscar Rubalcava** · [AppqIA](https://appqia.com) · [LinkedIn](https://www.linkedin.com/in/oscar-leonardo-rubalcava-0778a7415/)
