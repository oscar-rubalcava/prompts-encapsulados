# Contribuir a Prompts Encapsulados

¡Gracias por el interés! Ideas, reportes de errores, pruebas y mejoras de documentación son bienvenidos. Sé amable y respetuoso: aquí se discute con argumentos y se agradece la crítica constructiva.

## Configuración
```bash
git clone https://github.com/oscar-rubalcava/prompts-encapsulados.git && cd prompts-encapsulados
python3 -m venv .venv && source .venv/bin/activate
pip install -r tools/requirements-dev.txt
playwright install chromium        # solo para las pruebas de interfaz
```

## Antes de abrir un pull request
```bash
python3 tests/test_formato.py      # formato, firma, cifrado, seguridad, lanzamientos
python3 tests/test_interfaz.py     # decodificador y biblioteca en un navegador real
python3 tools/build_html.py        # si tocaste tools/encapsulados.template.html: reconstruye encapsulados.html
python3 tests/test_renombrado.py   # solo si tocaste tools/renombrar.py o el nombre (tarda un par de minutos)
```
`encapsulados.html` es un archivo **generado**: edita `tools/encapsulados.template.html` y reconstruye. El CI comprueba que ambos coincidan.

## Reglas del proyecto
- **No escribas el nombre del proyecto a mano** en código nuevo: sale de `tools/nombre.json` (ver `docs/RENOMBRAR.md`).
- **Un cambio, una prueba.** Todo comportamiento nuevo o corregido lleva su prueba. Si arreglas un error, añade la prueba que lo habría detectado.
- **Cambios de formato:** actualiza `docs/FORMATO.md`, sube `VERSION` en `encapsulados.py` y `SUPPORTED_VERSION` en el decodificador, y explica la compatibilidad con tarjetas anteriores.
- **Seguridad:** no inventes criptografía. Usa primitivas estándar y explica el modelo de amenaza del cambio. Los cambios que tocan firma, cifrado o CSP reciben una revisión más cuidadosa.
- **Sin dependencias nuevas** salvo que aporten mucho: hoy solo se usan `cryptography` y `Pillow`.
- **Honestidad en los mensajes:** la interfaz no debe prometer más de lo que la revisión puede garantizar.
- **Idioma:** el proyecto está en español; las traducciones y la documentación en inglés son muy bienvenidas.

## Buenas primeras contribuciones
- Traducir la CLI y `docs/` al inglés.
- Ampliar las palabras clave de la revisión de riesgos (con pruebas de falsos positivos).
- Un lector del formato en otro lenguaje (JavaScript/Node, Rust, Go) a partir de `docs/FORMATO.md`.
- Mejoras de accesibilidad del decodificador.

## Reportar vulnerabilidades
No uses issues públicos: sigue [`SECURITY.md`](SECURITY.md).
