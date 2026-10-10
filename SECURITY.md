# Política de seguridad

Prompts Encapsulados es una herramienta de seguridad en **beta** y **no ha sido auditada por terceros**. Los reportes de vulnerabilidades son bienvenidos y se toman en serio.

## Versiones con soporte
Solo la última versión publicada (serie 0.x).

## Cómo reportar
**No abras un issue público.** Usa el reporte privado de GitHub: pestaña **Security → Report a vulnerability**
(<https://github.com/oscar-rubalcava/prompts-encapsulados/security/advisories/new>).

Incluye, si puedes:
- versión (`python3 encapsulados.py --version`) y sistema operativo o navegador;
- pasos para reproducirlo y el impacto que ves;
- una tarjeta o archivo de prueba (**sin datos reales**).

## Qué esperar
Es un proyecto personal: respondo lo antes posible y trato de hacerlo en una semana. Coordinamos la divulgación: te aviso cuando haya una corrección y, si quieres, te doy crédito.

## En alcance
- Verificación de firmas, del bloque público y de la coherencia visual.
- Cifrado, derivación de claves y manejo de contraseñas.
- El lector de tarjetas (formato): desbordes, archivos malformados, comportamientos inesperados.
- El decodificador, el creador y la biblioteca: XSS, salto de la política CSP, filtración de datos, almacenamiento local y manejo de la identidad de firma y de las contraseñas en el navegador.
- Lanzamientos firmados (`release` y `verify-release`).
- La revisión de riesgos, cuando una evasión sea trivial o rompa lo que la documentación promete.

## Fuera de alcance
- Copiar el texto de una tarjeta que ya fue abierta: no es un objetivo del proyecto (ver `docs/SEGURIDAD.md`).
- Ingeniería social, contraseñas débiles elegidas por el usuario, o ataques que requieren control del navegador o del equipo del usuario.
- Falsos negativos de la revisión de riesgos que ya estén descritos como límite en la documentación.

## Buenas prácticas para quien usa Prompts Encapsulados
Lee `docs/SEGURIDAD.md`. En especial: verifica el decodificador con su lanzamiento firmado (`docs/LANZAMIENTOS.md`), compara las huellas por un canal independiente y no pruebes prompts de autores desconocidos en un asistente con acceso a tus archivos o herramientas.
