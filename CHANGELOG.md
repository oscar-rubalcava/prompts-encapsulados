# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). El programa usa versionado semántico; el formato de tarjeta tiene su propia versión (hoy, v4).

## [0.9.0] - Primera versión pública (beta)

### Incluido
- **Botones de envío** (Compartir…, WhatsApp, Correo): abren la app con el mensaje y el enlace listos, y si el enlace es largo y se cortaría lo copian y avisan en lugar de mandarlo dañado.
- **Compartir por enlace** (botón «Copiar enlace»): la tarjeta viaja como texto y se abre pegando el enlace o el código, a salvo de las apps que convierten las fotos a JPEG. Un JPEG ya no se ignora: la app explica qué pasó y qué pedir.
- **Creador de tarjetas en el navegador** (pestaña Crear): escribes el prompt y obtienes el PNG, con firma Ed25519 y cifrado opcionales; identidad de firma guardada en el navegador y exportable como el mismo `.pcid` de la línea de comandos. Lo que crea el navegador lo abre y verifica Python, y al revés (pruebas cruzadas).
- Formato de tarjeta v4: etiqueta PNG con bloque público firmado, payload comprimido y cifrado opcional (AES-256-GCM, PBKDF2 con 600 000 iteraciones) y firma Ed25519.
- CLI: `keygen`, `encode`, `inspect`, `verify`, `decode`, `index`, `emblemas`, `release`, `verify-release`, `pem`.
- Decodificador y biblioteca en un solo archivo (`encapsulados.html`): autores de confianza, aviso de suplantación, coherencia visual, revisión de riesgos del texto, guardado local opcional y total de KB.
- Emblema y color propios de cada tarjeta, elegidos para no repetirse en la carpeta.
- Lanzamientos firmados verificables con OpenSSL.
- Sitio de presentación y demo en línea.
- Revisión previa a publicar (`tools/preparar_publicacion.py`) y guía de primera publicación (`docs/PUBLICAR.md`).
- Nombre configurable en un solo archivo y herramienta de renombrado probada (`tools/renombrar.py`); el formato se conserva al cambiar la marca.

### Limitaciones conocidas
- No ha sido auditado por terceros.
- El creador y el decodificador se han probado solo en Chromium; la firma Ed25519 del navegador exige una versión reciente.
- La identidad de firma vive en el navegador: si se borran los datos del sitio, solo la copia de seguridad la recupera.
- La revisión de riesgos es una heurística.
- La interfaz y la documentación están en español.
