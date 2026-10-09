# Cambiar el nombre del proyecto

El nombre vive en **`tools/nombre.json`** y la herramienta **`tools/renombrar.py`** lo cambia en todo el proyecto: archivos, comandos, URLs, interfaz, documentación, logo, imagen social y sitio. Una prueba automática (`tests/test_renombrado.py`) comprueba que el proyecto renombrado sigue pasando todas sus pruebas.

| Campo | Qué es | Ejemplo actual |
|---|---|---|
| `nombre` | nombre oficial, tal como se ve | Prompts Encapsulados |
| `corto_visible` | nombre corto, en la interfaz | Encapsulados |
| `corto` | identificador: módulo, comando, archivos | `encapsulados` |
| `slug` | repositorio y URLs | `prompts-encapsulados` |
| `extension` | extensión de las tarjetas (`titulo_v1.0.<extension>.png`) | `encapsulado` |
| `magic` | firma de 4 letras al inicio del formato binario | `PENC` |
| `formato_id` | identificador del formato (claves, lanzamientos, almacenamiento local) | `encapsulados` |
| `usuario` | cuenta de GitHub | `oscar-rubalcava` |

## Antes de elegir un nombre nuevo
Búscalo en GitHub (también `github.com/NOMBRE`), PyPI (`pip index versions NOMBRE`), npm (`npm view NOMBRE`), tu registrador de dominios y bases de marcas (IMPI, USPTO, EUIPO). Prefiere una palabra inventada, de 5 a 8 letras, que se pronuncie igual en español e inglés.

## Pasos
```bash
# 1) simulación: muestra qué archivos cambiarían, sin tocar nada
python3 tools/renombrar.py --nombre "Nombre Nuevo" --corto nuevo --slug nombre-nuevo --extension nuevo

# 2) aplicarlo y regenerar lo que lleva el nombre (ejemplos, logo, GIF, imagen social, sitio)
python3 tools/renombrar.py --nombre "Nombre Nuevo" --corto nuevo --slug nombre-nuevo --extension nuevo --ejecutar --regenerar

# 3) pruebas
python3 tests/test_formato.py && python3 tests/test_interfaz.py
```
Para cambiar **solo la cuenta de GitHub**: `python3 tools/renombrar.py --usuario otra-cuenta --ejecutar --regenerar`.

## El formato se conserva por defecto
La firma de bytes (`magic`) y los identificadores del formato (`formato_id`) **no cambian** con la marca, igual que la firma de PNG no cambió nunca. Si ya hay tarjetas, claves o lanzamientos en circulación, cambiarlos los dejaría de abrir. Solo **antes de publicar** puedes cambiarlos, de forma explícita:
```bash
python3 tools/renombrar.py --nombre "Nombre Nuevo" --corto nuevo --slug nombre-nuevo --cambiar-formato --magic NUEV --ejecutar --regenerar
```

## Qué revisar a mano
- El subtítulo en inglés de `README.en.md` y las frases donde el nombre es el sujeto.
- `marca/LEEME.md` y, si el nombre tiene una sola palabra, el aspecto del logo (se dibuja en dos líneas cuando hay dos palabras).
- Lo que está fuera del repositorio: el dominio, los registros de paquetes y la marca registrada.

## Si ya publicaste
1. Cambia el nombre del repositorio en GitHub (*Settings → General → Repository name*): GitHub redirige el nombre anterior.
2. La URL de Pages cambia con el slug: actualiza los enlaces que hayas difundido.
3. Publica un **lanzamiento firmado nuevo** (`docs/LANZAMIENTOS.md`): el manifiesto incluye el nombre.
4. Actualiza la descripción, los topics y la imagen social del repositorio, y avisa en los canales donde lo anunciaste.
