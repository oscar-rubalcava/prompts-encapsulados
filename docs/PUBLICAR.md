# Publicar el proyecto en GitHub (primera vez)

Necesitas: **Git** (`git --version`; en macOS, `xcode-select --install`), una cuenta de GitHub y, opcionalmente, la **CLI de GitHub** (`brew install gh` y luego `gh auth login`), que resuelve la autenticación y crea el repositorio en un solo comando.

## 1. Revisión previa (en tu computadora)
Desde la carpeta del proyecto:
```bash
python3 tools/preparar_publicacion.py            # añade --pruebas para ejecutar también las pruebas (pip install cryptography pillow)
```
No sube nada. Vigila sobre todo que **ninguna clave privada** (`.pcid`, `.key`) acabe en el repositorio, que el remoto coincida con `tools/nombre.json` y que no falte ningún archivo. Si hay errores (✗), corrígelos antes de seguir.

## 2. Primer commit
```bash
git init -b main
git add -A && git status          # REVISA: no debe aparecer ningún .pcid ni .key
git commit -m "Prompts Encapsulados 0.9.0: primera versión pública (beta)"
```

## 3. Crear el repositorio

**Opción A: a mano.** En <https://github.com/new>: propietario = tu cuenta, nombre = `prompts-encapsulados`, **Public**, y **sin** README, sin .gitignore y sin licencia (ya los tienes). Descripción sugerida: `Prompts que se pueden verificar: etiquetas PNG firmadas y cifradas, con biblioteca y decodificador sin servidor.`

**Opción B: con la CLI de GitHub** (crea el repositorio y sube el código en un paso; salta al punto 6):
```bash
gh repo create prompts-encapsulados --public --source=. --remote=origin --push \
  --description "Prompts que se pueden verificar: etiquetas PNG firmadas y cifradas, con biblioteca y decodificador sin servidor."
```
> Si usas la opción B, el primer push dispara los flujos antes de que actives Pages: el flujo «Sitio y demo» fallará esa vez. No pasa nada: actívalo (punto 4) y vuelve a ejecutarlo.

## 4. Activar Pages (antes del primer push, si usas la opción A)
*Settings → Pages → Build and deployment → Source: **GitHub Actions**.* Sin esto, el flujo «Sitio y demo» no puede publicar.

## 5. Subir el código (opción A)
```bash
git remote add origin https://github.com/oscar-rubalcava/prompts-encapsulados.git
git push -u origin main
```
GitHub **no acepta la contraseña de tu cuenta** para `git push` por HTTPS: usa un *token personal* (Settings → Developer settings → Personal access tokens), una clave SSH, o `gh auth login`.

## 6. Ajustes del repositorio
- **About** (engranaje junto a «About»): la descripción, el sitio web (`https://oscar-rubalcava.github.io/prompts-encapsulados/`) y los topics: `prompt-engineering`, `prompts`, `llm`, `ai-security`, `prompt-injection`, `digital-signature`, `ed25519`, `encryption`, `privacy`, `python`, `open-format`.
- *Settings → General → Social preview:* sube `assets/social-preview.png`.
- *Settings → Security → Private vulnerability reporting:* **Enable** (lo usa `SECURITY.md`).
- Fija (pin) el repositorio en tu perfil.

## 7. Comprobar la primera corrida
Pestaña **Actions**. Deben pasar: **CI** (formato en Python 3.10 y 3.12, interfaz, construcción y renombrado) y **Sitio y demo**. Después abre la demo, `https://oscar-rubalcava.github.io/prompts-encapsulados/app/`, y arrastra una tarjeta de `ejemplos/`.

## Si algo falla
| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| «Sitio y demo» falla en `configure-pages` («Get Pages site failed») | Pages no estaba activado | Punto 4, y *Actions → Sitio y demo → Run workflow* |
| CI «construcción» falla con diferencias en `encapsulados.html` | otra versión de `fonttools` o de Python al generar el logo | `pip install -r tools/requirements-dev.txt`, `python3 tools/build_html.py`, `git add encapsulados.html`, commit y push. Si persiste, copia el diff del registro |
| CI «interfaz» falla al instalar Chromium | dependencias del sistema o versión de Playwright | revisa el registro; el trabajo usa `playwright install --with-deps chromium` |
| CI «formato (3.10)» falla y «(3.12)» pasa | el código usa algo de Python 3.12 | el proyecto declara 3.10+: corrige la sintaxis que indique el mensaje |
| CI «renombrado» falla o tarda mucho | ejecuta las pruebas del formato dentro de dos copias del proyecto | revisa cuál de sus pasos falla; suele ser el mismo error que en «formato» |
| `git push`: *Authentication failed* | GitHub no acepta la contraseña de la cuenta | token personal, SSH o `gh auth login` |
| `git push`: *rejected … fetch first* | creaste el repositorio con README o licencia | bórralo y créalo vacío, o `git pull --rebase origin main` |
| La rama se llama `master` | git antiguo | `git branch -M main` |
| Aparece un `.pcid` o `.key` en `git status` | `.gitignore` modificado o clave fuera de lugar | **no hagas commit**: saca la clave de la carpeta y ejecuta de nuevo la revisión previa |

## Después
Publica el primer **lanzamiento firmado** (`docs/LANZAMIENTOS.md`) y empieza la difusión (`GUIA_DE_PUBLICACION_Y_DIFUSION.md`, fuera del repositorio).
