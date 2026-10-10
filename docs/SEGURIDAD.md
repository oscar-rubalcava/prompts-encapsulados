# Seguridad de Prompts Encapsulados

## La idea central
Una tarjeta que se puede abrir, se puede copiar: quien la lee ve el texto en pantalla y puede copiarlo o fotografiarlo. **Prompts Encapsulados no promete impedirlo.** Lo que sí hace:
1. Que una tarjeta **falsa o alterada se detecte**.
2. Que un **prompt peligroso se note** antes de usarlo.
3. Que el decodificador **no pueda filtrar nada** por la red.

## Amenazas y controles
| Amenaza | Control | Estado | Límite |
|---|---|---|---|
| Alterar una tarjeta firmada | Firma Ed25519 sobre todo el flujo, incluido el bloque público | Hecho | Prueba integridad, no quién es el dueño de la clave |
| Alterar título o categoría de una tarjeta cifrada | El bloque público es parte de los datos autenticados de AES-GCM | Hecho | Sin firma ni cifrado, no hay protección |
| Hacerse pasar por un autor | Lista de autores de confianza (`.pub` por un canal independiente) y aviso rojo si la tarjeta declara el nombre de un autor de confianza pero la clave es otra | Hecho | Requiere importar la clave pública una vez |
| Imitar el aspecto de un autor | El decodificador comprueba que la «regla de huella» dibujada corresponde a la clave que firmó | **Nuevo** | Solo se comprueba la regla. Emblema, colores e iconos son decorativos. Quien dibuje su propia regla pasa, pero sale como autor desconocido |
| Prompt con instrucciones maliciosas | Revisión automática del texto: caracteres ocultos (se muestran en rojo, se decodifican y se quitan al copiar), órdenes de ignorar instrucciones, ocultar algo al usuario, revelar el mensaje de sistema, enviar datos o credenciales, comandos, bloques codificados. Con riesgo alto y autor no confiable, hay que pulsar dos veces para copiar | **Nuevo** | Es una **heurística**: falla en ambos sentidos. Un prompt malicioso bien redactado en lenguaje natural pasa. Un autor de confianza tampoco garantiza que el texto sea seguro |
| Decodificador que filtra datos | Política de seguridad del contenido (CSP): sin conexiones de red y solo se ejecuta su propio script (por hash) | **Nuevo** | Protege al archivo oficial, no a una copia modificada |
| Decodificador falso que dice «firma válida» a todo | **Lanzamientos firmados** (`release` y `verify-release`): manifiesto con el SHA-256 de cada archivo, firmado; y verificación independiente con OpenSSL (ver `LANZAMIENTOS.md`) | **Nuevo** | Solo protege si publicas tu huella por canales independientes y quien descarga la compara. La firma prueba que los archivos son los que publicaste, no que el código sea seguro. El primer contacto sigue siendo un acto de confianza |
| Adivinar la contraseña sin conexión | PBKDF2-HMAC-SHA256 con **600 000 iteraciones** (recomendación OWASP 2023) y aviso si la contraseña es corta | Mejorado | PBKDF2 no consume memoria y una GPU lo acelera: la defensa real es una **frase larga**. Argon2id no está disponible en el navegador |
| Identidad de firma guardada en el navegador | Se crea y se guarda en este navegador; se puede proteger con contraseña (PBKDF2 con 600 000 iteraciones y AES-GCM, el mismo formato `.pcid` que la línea de comandos); mientras firma, la clave se usa en memoria como no extraíble (pero lo guardado en el navegador sí contiene la clave: cifrada con contraseña, o en claro si no la pones); copia de seguridad y borrado desde la interfaz | **Nuevo** | **Sin contraseña**, cualquiera que use ese navegador puede firmar como tú: la contraseña es opcional pero recomendada. Si se borran los datos del sitio, la identidad se pierde (solo sirve la copia de seguridad). No uses esta función en un equipo que no sea tuyo |
| Datos de las tarjetas alterados por el navegador al crearlas | El PNG se codifica en la propia página y los bytes de la zona de datos se escriben tal cual, sin pasar por la exportación del canvas (que algunos navegadores alteran como defensa anti-huella); cada tarjeta se verifica al crearla (se lee de vuelta idéntica) | **Nuevo** | La **lectura** de tarjetas sí usa el canvas para leer los píxeles: en navegadores con protección anti-huella activa puede fallar; no probado fuera de Chromium |
| Prompts legibles en un equipo compartido | La biblioteca **no guarda nada** salvo que actives el interruptor; con él activo, las copias quedan en el navegador de ese equipo (las cifradas siguen cifradas). Hay botones para quitar tarjetas, vaciar y desactivar (borra las copias) | Nuevo | El almacenamiento del navegador no está cifrado por Prompts Encapsulados: quien use tu navegador puede leer las tarjetas sin contraseña. Actívalo solo en un equipo personal |
| Copiar o filtrar el prompt | No se puede impedir | n/a | Ver pendientes |

## Candados posibles que aún no están
1. **Cifrado por destinatario** (clave pública X25519): sin contraseña compartida, solo esa persona puede abrirla. Límite: quien la abre puede recrear la tarjeta.
2. **Marca por destinatario**: permite rastrear quién filtró *la tarjeta*, pero no el texto copiado, salvo que se marque el propio texto (frágil).
3. **Caducidad y lista de revocación** firmada por el autor. Son «blandas»: un decodificador modificado puede ignorarlas, y la caducidad depende del reloj del equipo.
4. **Firmar también la lista de autores de confianza** que un autor pudiera repartir.

## Buenas prácticas
**Si creas tarjetas**
- Firma siempre y comparte tu `.pub` por un canal distinto al de las tarjetas.
- Usa una frase de 4 o más palabras como contraseña. Sin contraseña, una tarjeta cifrada no se recupera.
- Guarda tu `.pcid` en secreto; si se filtra, abandónala y comunica la nueva huella.
- Si pegaste texto de la web, revisa que no traiga caracteres ocultos: `encode` te avisa.

**Si recibes tarjetas**
- Descarga el decodificador solo de un canal oficial y verifícalo con `verify-release` (o con OpenSSL) usando la huella que el autor publicó por otro canal. Compararlo solo con un `SHA256SUMS.txt` sin firmar no protege.
- Mira el color del estado de la firma antes que el diseño: el diseño se puede imitar.
- Lee el prompt completo antes de pegarlo. No lo pruebes en un asistente con acceso a tus archivos, correo o herramientas si no conoces al autor.
- Ante una advertencia roja, no uses la tarjeta y consulta al autor por otro canal.
