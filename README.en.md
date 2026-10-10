<p align="center">
  <img src="marca/encapsulados_icono_256.png" alt="Prompts Encapsulados" width="96">
</p>

<h1 align="center">Prompts Encapsulados</h1>
<p align="center"><i>Encapsulated Prompts</i></p>
<p align="center"><b>Prompts you can verify.</b><br>
Create a PNG label with your prompt: compressed, optionally password-encrypted, signed by its author and easy to find in your library. No server, no account.</p>

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

1. Open the **[live demo](https://oscar-rubalcava.github.io/prompts-encapsulados/app/)**. Everything runs in your browser: nothing is uploaded.
2. In the **Crear** (Create) tab, type a title and a prompt (anything between `{{double braces}}` becomes a variable) and press **Crear tarjeta**. You get a PNG you can download and send.
3. To sign it, create your identity (a name and a color; it stays in your browser) and tick “Firmar con mi identidad”. Download the backup.
4. Press **Abrir para comprobar**: you see who signed it, fill in the variables and copy the prompt.
5. For the hard cases, open the cards in [`ejemplos/`](ejemplos/): `resumen-de-correos-ejemplo-con-riesgos` (hidden text) and `actualizacion-de-precios` (an imitation). The encrypted card's password is `demo1234`.

<p align="center"><img src="assets/crear.png" alt="Create tab of Prompts Encapsulados" width="760"></p>

## What is included

- **Browser creator:** type the prompt and get the PNG card, with optional signature and encryption; nothing to install, no server.
- **Ed25519 signature** over all content and public data; trusted-authors list and a warning when someone impersonates a trusted author.
- **Optional encryption:** AES-256-GCM with PBKDF2-HMAC-SHA256 (600,000 iterations).
- **Signed public block** (title, category, tags): the library indexes even encrypted cards without a password.
- **Library** with search, filters, total size and optional local storage in the browser.
- **Text risk review:** reveals hidden characters, decodes invisible text and flags suspicious instructions.
- **Imitation detection:** checks that a card's look matches the key that signed it.
- **No network:** the decoder cannot connect to any address (CSP).
- **Signed releases**, verifiable with just `openssl` ([guide, ES](docs/LANZAMIENTOS.md)).
- **Open, documented format** ([spec, ES](docs/FORMATO.md)): write your own reader.

## How to share a card

| Channel | What to do |
|---|---|
| **WhatsApp, Telegram and chats** | Under “Enviar la tarjeta” (Send the card), press **WhatsApp** (opens the app with the message and link ready), **Compartir…** (your phone's share menu) or **Copiar enlace** (Copy link) and paste it anywhere. The card travels inside the link, as text, safe from image conversions. Whoever opens it sees the card in the browser, with its signature. |
| **Email** | The **Correo** button opens your mail app with the message ready. If the link is long and would be cut off, it copies it and tells you; you can also attach the PNG. |
| **AirDrop, Drive** | Send the PNG as a file. |
| **WhatsApp, sending the PNG** | Send it as a **Document**, never as a **Photo**. |

**Why a photo breaks it:** the card's data lives in the pixels of a lossless PNG. If an app converts the image to JPEG (WhatsApp does this to photos), that data is destroyed and cannot be recovered. The decoder recognizes this and explains it, but that copy can no longer be opened: ask for another one as a link or a document. **Link limit:** about 44 KB of card (around 60,000 characters); larger ones go as PNG. The WhatsApp and email buttons never send a truncated link: if it does not fit, they copy it and tell you. (WhatsApp's exact limit for long links is not verified.)

## Name
The official name is **Prompts Encapsulados** (Spanish for “encapsulated prompts”); the short name is **Encapsulados**. The command is `encapsulados` and cards are saved as `title_v1.0.encapsulado.png`.

## Command line (optional)

To automate or create many cards from the terminal. Requires Python 3.10+. The cards and identities it creates are the same as the browser's, and they open each other.

```bash
git clone https://github.com/oscar-rubalcava/prompts-encapsulados.git && cd prompts-encapsulados
pip install cryptography pillow

# 1) your signing identity (once). Keep the .pcid secret; share the .pub
python3 encapsulados.py keygen MyBrand --color "#FBB43F"

# 2) create a card from a .txt or .json
python3 encapsulados.py encode my_prompt.txt --title "My prompt" --category Sales --sign mybrand.pcid -o my_cards/
#    add --ask-password to encrypt it, or --hide-title for a private card

# 3) inspect and read it
python3 encapsulados.py inspect my_cards/my-prompt_v1.0.encapsulado.png --trusted mybrand.pub
python3 encapsulados.py decode  my_cards/my-prompt_v1.0.encapsulado.png

# 4) your library in the terminal (with total KB)
python3 encapsulados.py index my_cards/ --trusted mybrand.pub
```

**Send cards as documents**, not as photos: messaging apps may recompress images and corrupt them. The web interface and the documentation are in Spanish for now.

## Security: what it does and what it does not

- An opened card **can be copied**: The tool does not prevent that. It makes a **forgery detectable** and a **dangerous prompt noticeable** before you use it.
- The signature proves nobody touched the card, **not who owns the key**: compare the fingerprint with the one the author published through another channel.
- The risk review is a **heuristic**: it can fail both ways.
- **Status: beta, no external audit.** It uses standard primitives (Ed25519, AES-GCM, PBKDF2), but review it before trusting it with anything critical.

Full threat model: [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) (Spanish). To report a vulnerability: [`SECURITY.md`](SECURITY.md).

## Roadmap

- [ ] Test the creator in more browsers (today, Chromium only) and with several identities
- [ ] Create a new version from an existing card
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
