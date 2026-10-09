# Lanzamientos firmados

## Para qué sirven
El decodificador (`encapsulados.html`) es quien decide si una tarjeta es de fiar. Si alguien reparte una copia modificada que diga «firma válida» a todo, las demás protecciones no sirven de nada. Un lanzamiento firmado permite comprobar que lo que descargaste es **exactamente lo que su autor publicó**.

## Qué contiene
| Archivo | Para qué |
|---|---|
| `MANIFEST.json` | versión, fecha, firmante y la lista de archivos con su SHA-256 y su tamaño |
| `MANIFEST.json.sig` | firma Ed25519 del manifiesto (64 bytes) |
| `SHA256SUMS.txt` y `SHA256SUMS.txt.sig` | la misma lista en el formato clásico, también firmada (para verificar solo con `openssl` y `sha256sum`) |

## Publicar (si eres el autor)
1. **Crea una identidad solo para lanzamientos**, distinta de la que firma tus tarjetas, protegida con contraseña y guardada **fuera** de la carpeta que publicas:
   `python3 encapsulados.py keygen "AppqIA Lanzamientos" -o lanzamientos --ask-password`
   Genera `lanzamientos.pcid` (secreta), `lanzamientos.pub` y `lanzamientos.pem` (públicas).
2. **Prepara la carpeta** con lo que vas a publicar. `release` se niega a continuar si encuentra una clave privada (`.pcid`) dentro.
3. **Firma:** `python3 encapsulados.py release prompts-encapsulados/ --sign lanzamientos.pcid --version 1.0.0 --name "Prompts Encapsulados"`
4. **Publica** los archivos y tu `lanzamientos.pem`, y **publica la huella en varios canales independientes** del que reparte los archivos: tu sitio con HTTPS, el README del repositorio, tu perfil profesional, una tarjeta de presentación, en persona. Sin eso, la firma no prueba quién eres.
5. Cada cambio se firma de nuevo con una versión nueva.

## Verificar (si descargas)
Primero, consigue la **huella o el `.pem` del autor por un canal distinto al de la descarga**. Después, cualquiera de estas vías:

**A. Con Prompts Encapsulados**
```
python3 encapsulados.py verify-release carpeta_descargada/ --trusted lanzamientos.pub --require-trusted
```
Comprueba la firma del manifiesto, la de la lista de sumas, que ambas coincidan, y el SHA-256 de cada archivo. Avisa de archivos añadidos que la firma no respalda (`--strict` los trata como error).

**B. Independiente de Prompts Encapsulados (solo `openssl` y `sha256sum`)**
```
openssl pkeyutl -verify -pubin -inkey lanzamientos.pem -rawin -in SHA256SUMS.txt -sigfile SHA256SUMS.txt.sig
sha256sum -c SHA256SUMS.txt          # en macOS: shasum -a 256 -c SHA256SUMS.txt
```
Debe decir `Signature Verified Successfully` y luego `OK` en cada archivo. Para comprobar que el `.pem` corresponde a la huella publicada:
```
openssl pkey -pubin -in lanzamientos.pem -outform DER | tail -c 32 | sha256sum | cut -c1-24 | tr a-f A-F | sed 's/\(....\)/\1-/g; s/-$//'
```
La salida debe ser igual a la huella (por ejemplo `9F8F-A864-F3B9-2D55-56BD-2755`).

> **No verifiques solo con `sha256sum -c`.** Si alguien cambia un archivo y reescribe también `SHA256SUMS.txt`, `sha256sum` dirá que todo está bien. Lo que protege es la **firma** de esa lista.
> La vía B se probó con OpenSSL 3.0. El `openssl` del sistema en macOS es LibreSSL y puede no soportar Ed25519 con `-rawin`: instala OpenSSL 3 o usa la vía A. En Windows, usa Git Bash o WSL.

## Qué garantiza y qué no
- **Sí:** los archivos son los que firmó quien tiene esa clave privada, sin cambios, ni faltantes.
- **No:** que el código sea seguro (solo que es el que se publicó), ni quién es el dueño de la clave. La identidad se establece comparando la **huella** por varios canales independientes. El primer contacto con un autor sigue siendo un acto de confianza.
- **No:** protege si obtienes a la vez los archivos, el `.pem` y la «huella» del mismo canal comprometido.

## Si se compromete la clave de lanzamientos
Deja de firmar con ella, genera una nueva, y publica la **nueva huella** y el aviso en todos los canales. No hay revocación automática: los usuarios que ya tenían la clave vieja como de confianza deben cambiarla a mano.
