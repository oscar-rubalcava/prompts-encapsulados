# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). El programa usa versionado semántico; el formato de tarjeta tiene su propia versión (hoy, v4).

## [0.9.0] - Primera versión pública (beta)

### Incluido
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
- Las tarjetas se crean solo desde la línea de comandos.
- La revisión de riesgos es una heurística.
- La interfaz y la documentación están en español.
