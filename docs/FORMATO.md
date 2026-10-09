# Prompts Encapsulados v4: especificación del formato

Una tarjeta de Prompts Encapsulados es una imagen **PNG sin pérdida** (RGBA, 8 bits por canal) con forma de etiqueta. Guarda un prompt, sus datos públicos y, opcionalmente, cifrado con contraseña y firma digital. Un lector solo necesita este documento para abrirla.

Historial: **v2** añadió la firma Ed25519. **v3** cambió la imagen a cápsula. **v4** cambia la imagen a etiqueta, añade el **bloque público firmado** (para indexar bibliotecas sin contraseña) y renombra el formato a Prompts Encapsulados (firma de bytes `PENC`). Las versiones anteriores no se abren con el lector v4.

## 1. Geometría de la imagen (etiqueta)
El ancho del codificador de referencia es **W = 360** y el alto **H** crece con el contenido. Un lector solo necesita W y H.

| Zona | Posición | Uso |
|---|---|---|
| Zona de datos | x en [6, W−6), y en [74, H−18) | los bytes del flujo, en R,G,B de cada píxel, fila por fila, de izquierda a derecha |
| Cabecera | y < 74 | decorativa: emblema propio de la tarjeta (bloque de 72×72 arriba a la izquierda), título, categoría, versión, autor con su marca mini, iconos de estado |
| Pie | y ≥ H−18 | decorativo: ID, estado, nombre, tamaño; franja del color de la categoría |
| Márgenes | x < 6 y x ≥ W−6 | decorativos |
| Esquinas | silueta con la esquina superior izquierda cortada y esquinas redondeadas | transparentes (alfa 0) |

- Los píxeles de la zona de datos son siempre **opacos** (alfa 255), así que se leen exactos.
- Alto: `H = 74 + max(10, ceil(píxeles / 348)) + 18`, donde `píxeles = ceil(bytes / 3)`. Los píxeles después del final del flujo son relleno visual y se ignoran. El flujo se autodelimita con LEN.
- Cualquier compresión con pérdida (JPEG, recompresión de apps de mensajería, capturas reescaladas) destruye los datos. Las apps que convierten PNG transparente a JPEG al enviar «como foto» también lo rompen: envía siempre **como documento**.
- La etiqueta puede dibujarse en **tema oscuro** (por defecto) o **claro**; es solo decorativo y no altera la zona de datos.
- **Todo lo decorativo no es confiable.** Cualquiera puede dibujar un icono de «firmada», un sello o un nombre. Solo cuentan el CRC, la firma y el cifrado del flujo.

## 2. Flujo de bytes (big-endian)
| Campo | Tamaño | Notas |
|---|---|---|
| MAGIC | 4 | ASCII `PENC` |
| VERSION | 1 | `4` |
| FLAGS | 1 | bit 0 = cifrada, bit 1 = firmada |
| SALT | 16 | solo si cifrada |
| NONCE | 12 | solo si cifrada |
| ITER | 4 | solo si cifrada (PBKDF2), por defecto **600000** (OWASP 2023; las tarjetas antiguas guardan su propio valor, p. ej. 200000). Los lectores deben rechazar valores absurdos (> 5,000,000) |
| PUBLEN | 2 | largo del bloque público (máximo 4096) |
| PÚBLICO | PUBLEN | JSON UTF-8 sin cifrar (ver §3) |
| LEN | 4 | largo de PAYLOAD |
| PAYLOAD | LEN | ver §4 |
| CLAVE PÚBLICA | 32 | solo si firmada: Ed25519 |
| FIRMA | 64 | solo si firmada: Ed25519 |
| CRC32 | 4 | de todos los bytes anteriores (detecta daño accidental; **no** es seguridad) |

## 3. Bloque público
JSON UTF-8 con estos campos (todos opcionales): `title`, `category`, `version`, `author`, `tags` (lista), `model`, `cat_hue` (número 0 a 1, tono del color de la categoría) y `emblem`.
- `emblem` = `{"h": 0 a 1, "g": "8 dígitos 0-6"}`: el **emblema propio de la tarjeta**. `h` es el tono y `g` la figura (las 8 casillas de la mitad izquierda de una cuadrícula de 4×4; 0-3 = cuarto de disco en una esquina, 4 = disco, 5 = par de cuartos opuestos, 6 = vacía; la mitad derecha es el espejo). Es decorativo, pero queda firmado. Se conserva igual entre versiones del mismo prompt (`--emblem-from`) y el codificador elige uno distinto a los que ya hay en la carpeta. Si falta, el lector lo deriva de la huella o del título.
- Está **sin cifrar** a propósito: permite que una biblioteca indexe tarjetas cifradas sin conocer la contraseña.
- Está **protegido contra alteraciones**: lo cubre la firma (si hay) y, si la tarjeta está cifrada, forma parte de los datos autenticados de GCM (AAD). **Una tarjeta sin firma ni cifrado no protege nada.**
- Una tarjeta **privada** deja vacíos título, categoría, versión, autor y etiquetas.
- El título que un lector muestra debe ser el de este bloque, no el dibujado en la imagen.

## 4. PAYLOAD (privado)
1. JSON UTF-8 con `description`, `system`, `prompt`, `variables`, `created`.
2. Comprimido con **deflate crudo** (RFC 1951, sin cabecera zlib).
3. Si FLAGS&1: cifrado con **AES-256-GCM**. Clave = PBKDF2-HMAC-SHA256(contraseña UTF-8, SALT, ITER). AAD = todos los bytes desde MAGIC hasta LEN inclusive (incluye el bloque público). LEN incluye la etiqueta de 16 bytes.

## 5. Firma
- Algoritmo: **Ed25519** (RFC 8032). **Mensaje firmado:** todos los bytes desde MAGIC hasta el final de PAYLOAD (incluye FLAGS, el bloque público y el texto cifrado si lo hay). Se puede verificar **sin la contraseña**.
- **Huella** de una clave: `SHA-256(clave pública)` en hex mayúsculas, primeros 24 caracteres, en 6 grupos de 4 con guion. Ej.: `2A61-1E54-1DA8-79B7-FAC5-5DBF`.
- Un lector debe verificar la firma **antes** de mostrar el contenido y no abrir tarjetas con firma no válida sin una decisión explícita del usuario.

### Qué garantiza y qué no
- **Sí:** el contenido y los datos públicos no cambiaron desde que quien tiene esa clave privada los firmó.
- **No:** quién es el dueño de la clave. La clave viaja dentro de la tarjeta. La identidad se establece comparando la huella, o importando el archivo `.pub`, por un **canal independiente** de confianza.
- El campo `author` lo escribe el creador y **no está verificado**. Si declara el nombre de un autor de confianza pero la clave es otra, un lector debe advertir de una posible suplantación.
- No hay revocación ni caducidad: si una clave privada se filtra, debe abandonarse y comunicar la nueva huella.

## 6. Archivos de identidad (JSON)
- `*.pcid` (**secreto**): `{"format":"encapsulados-key","v":1,"name","public":hex,"brand":{"color":"#RRGGBB"|null,"mark":"auto"|"q"},"private":hex}`, o con `"enc":{"salt","nonce","iters","ct"}` en lugar de `private` si está protegida con contraseña (AES-256-GCM, AAD = `encapsulados-key`).
- `*.pem`: la misma clave pública en formato estándar PEM (SubjectPublicKeyInfo), para verificar con OpenSSL.
- `*.pub` (**se comparte**): `{"format":"encapsulados-pub","v":1,"name","public":hex,"fingerprint","brand":{...}}`.
- `brand.mark`: `auto` = emblema derivado de la clave; `q` = monograma Q. `brand.color` es el color del autor (si falta, sale de la clave).

## 7. Variables
Marcadores `{{nombre}}` (letras, números y guion bajo) en `system` y `prompt`. `variables` puede dar `label` y `default` por nombre.

## 8. Seguridad: resumen
- La confidencialidad depende de la contraseña: una débil se adivina por fuerza bruta. Sin contraseña no hay recuperación.
- El título, la categoría y el autor del bloque público son visibles para quien tenga el archivo, aunque esté cifrado. Usa una tarjeta privada si eso es sensible.
- La clave privada `.pcid` nunca debe compartirse ni subirse a repositorios.

## 9. Tipografía y licencias
Las etiquetas usan **IBM Plex Mono** (© IBM Corp., licencia SIL Open Font License 1.1, texto en `fonts/IBMPlexMono-OFL.txt`). El nombre «IBM Plex» está reservado por IBM: no lo uses como parte de tu marca. Los archivos de la fuente se incluyen sin modificar.

## 10. Recomendaciones para lectores
- Verificar la firma **antes** de mostrar el contenido.
- Tratar el texto como **no confiable**: mostrarlo, nunca ejecutarlo. Hacer visibles los caracteres ocultos (etiquetas Unicode U+E0000–E007F, ancho cero, controles bidireccionales U+202A–202E y U+2066–2069, guion blando) y quitarlos al copiar.
- No hacer ninguna conexión de red al abrir una tarjeta.
- **Coherencia visual (opcional):** la regla de huella dibujada debe corresponder a la clave firmante. Hay `n = floor((W − 12) / 6)` marcas; la marca `i` está en `x = 6 + 6·i`, mide 2 px de ancho y 3 px (bit 1) o 1 px (bit 0) de alto, terminando en la fila `y = 73`. El bit `i` es `(SHA-256(clave pública)[(i / 8) mod 32] >> (i mod 8)) & 1`. Se muestrea la fila `y = 72`: una marca alta difiere del fondo (píxel en `x + 3`) y una baja no. Si la línea base (`y = 73`) no se distingue del fondo, la comprobación no aplica.
