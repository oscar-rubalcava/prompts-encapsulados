import os, sys, glob, re, json
from playwright.sync_api import sync_playwright
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); EX = os.path.abspath(os.path.join(BASE, 'ejemplos')); URL = 'file://' + os.path.abspath(os.path.join(BASE, 'encapsulados.html'))
import tempfile; OUT = tempfile.mkdtemp(prefix='encapsulados_ui_')
sys.path.insert(0, BASE)
import encapsulados as cs
from PIL import Image
ok = True
def check(name, cond, extra=''):
    global ok; ok = ok and cond; print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra and not cond else ''))
P = lambda n: os.path.join(EX, n)
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 1200, 'height': 950}, permissions=['clipboard-read', 'clipboard-write'])
    pg = ctx.new_page(); errors = []
    pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.goto(URL); pg.wait_for_timeout(300)
    txt = lambda s: pg.inner_text(s); vis = lambda s: pg.is_visible(s)
    def load(n): pg.set_input_files('#file', P(n)); pg.wait_for_timeout(800)

    # --- A) tarjeta firmada, autor desconocido
    load('asistente-de-punto-de-venta_v1.0.encapsulado.png')
    check('A firma válida / autor desconocido', 'autor desconocido' in txt('#sigTitle'), txt('#sigTitle'))
    check('A título firmado y categoría en el encabezado', 'Asistente de punto de venta' in txt('#title') and 'Ventas' in txt('#title'), txt('#title'))
    check('A aviso: autor declarado sin verificar', 'no está verificado' in txt('#sigNote'), txt('#sigNote'))
    check('A dos variables, una con valor por defecto', pg.locator('#vars input').count() == 2 and '1 de 2' in txt('#count'), txt('#count'))
    pg.fill('#v_nombre_negocio', 'Abarrotes Lupita'); pg.click('#copyAll'); pg.wait_for_timeout(200)
    clip = pg.evaluate('navigator.clipboard.readText()'); check('A copiar todo con variables rellenas', 'Abarrotes Lupita' in clip and '---' in clip)
    check('A metadatos públicos: etiquetas', 'pos, caja' in txt('#meta'), txt('#meta'))
    pg.screenshot(path=f'{OUT}/abrir_desconocido.png')

    # --- B) importar .pub -> de confianza
    pg.set_input_files('#pubFile', P('demo_appqia.pub')); pg.wait_for_timeout(400)
    check('B autor importado', 'AppqIA (demo)' in txt('#trustList'))
    load('asistente-de-punto-de-venta_v1.0.encapsulado.png'); check('B ahora es de confianza', 'autor de confianza: AppqIA (demo)' in txt('#sigTitle'), txt('#sigTitle'))
    pg.screenshot(path=f'{OUT}/abrir_confianza.png')

    # --- C) alterada
    load('alterada_asistente-de-punto-de-venta_v1.0.encapsulado.png')
    check('C firma no válida y no se abre', 'Firma no válida' in txt('#sigTitle') and not vis('#open'))
    pg.click('#forceOpen'); pg.wait_for_timeout(500); check('C tras forzar se ve el prompt malicioso', vis('#open') and 'otra persona' in txt('#promptOut'))

    # --- D) cifrada y firmada
    load('respuesta-a-reclamos_v1.0.encapsulado.png')
    check('D firma verificable sin contraseña + candado', 'de confianza' in txt('#sigTitle') and vis('#lock') and not vis('#open'))
    check('D título público visible sin contraseña en los metadatos', 'Atención' in txt('#meta'), txt('#meta'))
    pg.fill('#pw', 'mala'); pg.click('#unlock'); pg.wait_for_timeout(500); check('D contraseña mala', 'incorrecta' in txt('#err'))
    pg.fill('#pw', 'demo1234'); pg.press('#pw', 'Enter'); pg.wait_for_timeout(2200); check('D contraseña buena abre', vis('#open') and 'Respuesta a reclamos' in txt('#title'))

    # --- E) privada
    priv = [os.path.basename(f) for f in glob.glob(P('tarjeta-privada_*.png'))][0]; load(priv)
    pg.fill('#pw', 'demo1234'); pg.press('#pw', 'Enter'); pg.wait_for_timeout(2200)
    check('E tarjeta privada: título genérico, sin categoría', 'Tarjeta privada' in txt('#title') and 'Categoría' not in txt('#meta'), txt('#meta'))

    # --- F) suplantada y G) sin firma
    load('recordatorio-de-citas_v1.0.encapsulado.png'); check('F suplantada de un autor de confianza: advertencia fuerte', 'NO es de' in txt('#sigTitle') and not vis('#trustRow'), txt('#sigTitle'))
    load('resumen-semanal-de-ventas-con-alertas-de-inventario_v1.0.encapsulado.png'); check('G sin firma', txt('#sigTitle') == 'Sin firma' and vis('#open'))

    # --- H) biblioteca
    pg.click('#tabLib'); files = sorted(glob.glob(P('*.png'))); pg.set_input_files('#libFiles', files); pg.wait_for_timeout(3500)
    check('H doce tarjetas indexadas', txt('#libCount') == '(12)' and pg.locator('.card').count() == 12, txt('#libCount'))
    titles = [t.strip() for t in pg.locator('.card .ct').all_inner_texts()]
    check('H la cifrada muestra su título sin contraseña', 'Respuesta a reclamos' in titles and 'Tarjeta privada' in titles, str(titles))
    cat_txt = txt('#cats'); check('H categorías con conteo', 'Ventas 3' in cat_txt.replace('\n', ' ') and 'Atención 3' in cat_txt.replace('\n', ' ') and 'Sin categoría' in cat_txt, cat_txt.replace('\n', ' '))
    check('H la suplantada se marca en la biblioteca', 'Se hace pasar por' in pg.locator('.card', has_text='Recordatorio').inner_text())
    pg.fill('#q', 'whatsapp'); check('H buscar «whatsapp»', pg.locator('.card').count() == 1)
    pg.fill('#q', 'atencion'); check('H búsqueda sin acentos: «atencion»', pg.locator('.card').count() == 3, str(pg.locator('.card').count()))
    pg.fill('#q', 'zzz'); check('H sin resultados', pg.locator('.card').count() == 0); pg.fill('#q', '')
    def state(v): pg.select_option('#stateSel', v); return pg.locator('.card').count()
    check('H filtro: de confianza = 6', state('trusted') == 6); check('H filtro: firma válida desconocida = 4', state('valid') == 4)
    check('H filtro: sin firma = 1', state('none') == 1); check('H filtro: firma no válida = 1', state('invalid') == 1); state('all')
    pg.click('#cats button:has-text("Deporte")'); check('H filtro por categoría Deporte', pg.locator('.card').count() == 1); pg.click('#cats button:has-text("Todas")')
    pg.screenshot(path=f'{OUT}/biblioteca.png', full_page=True)
    pg.locator('.card', has_text='Plan de entrenamiento').click(); pg.wait_for_timeout(2200)
    check('H clic en una tarjeta la abre', vis('#viewOpen') and 'Plan de entrenamiento semanal' in txt('#title'))


    # --- J) seguridad
    import time
    pg.click('#tabOpen'); load('asistente-de-punto-de-venta_v1.0.encapsulado.png')
    check('J tarjeta legítima: la apariencia coincide con su clave', 'apariencia' not in txt('#sigTitle') and vis('#safety') and 'sin señales' in txt('#safetyT'), txt('#sigTitle') + ' | ' + txt('#safetyT'))
    load('actualizacion-de-precios_v1.0.encapsulado.png')
    check('J apariencia imitada: se avisa aunque la firma sea válida', 'apariencia NO corresponde' in txt('#sigTitle'), txt('#sigTitle'))
    pg.click('#tabLib'); check('J la biblioteca también marca la imitación', 'apariencia' in pg.locator('.card', has_text='Actualización de precios').inner_text()); pg.click('#tabOpen')
    load('resumen-de-correos-ejemplo-con-riesgos_v1.0.encapsulado.png')
    st = txt('#safety')
    check('J prompt con riesgos: panel de revisión en rojo', 'bad' in pg.get_attribute('#safety', 'class') and 'riesgo alto' in txt('#safetyT'), txt('#safetyT'))
    check('J detecta y decodifica el texto oculto', 'caracteres ocultos' in st and 'reenvia todo el historial' in st, st)
    check('J detecta orden de ocultar, ignorar instrucciones y enlace externo', 'ocultarle' in st and 'ignorar instrucciones' in st and 'recolector.example' in st, st)
    check('J los caracteres ocultos se ven marcados en el texto', pg.locator('#promptOut mark.hid').count() >= 1)
    pg.evaluate("navigator.clipboard.writeText('CENTINELA')"); pg.click('#copyPrompt'); pg.wait_for_timeout(250)
    check('J autor desconocido + riesgo alto: la primera pulsación NO copia', pg.evaluate('navigator.clipboard.readText()') == 'CENTINELA' and 'señales de riesgo altas' in txt('#copied'), txt('#copied'))
    pg.click('#copyPrompt'); pg.wait_for_timeout(250); clip = pg.evaluate('navigator.clipboard.readText()')
    check('J la segunda pulsación copia SIN caracteres ocultos', 'Resume los correos' in clip and not any(0xE0000 <= ord(c) <= 0xE007F for c in clip) and 'se quitaron' in txt('#copied'), txt('#copied'))
    # bloqueo de red y de scripts inyectados (CSP)
    check('J uso normal sin errores ni violaciones de CSP', not errors, '; '.join(errors))
    v = pg.evaluate("new Promise(r => { document.addEventListener('securitypolicyviolation', e => r(e.violatedDirective)); fetch('https://example.com/x').catch(() => {}); setTimeout(() => r('sin-evento'), 3000); })")
    check('J CSP: el decodificador no puede conectarse a ninguna dirección', str(v).startswith('connect-src'), str(v))
    pg.evaluate("document.body.insertAdjacentHTML('beforeend', '<img src=x onerror=\"window.__pwn=1\">')"); pg.wait_for_timeout(400)
    check('J CSP: un script inyectado no se ejecuta', pg.evaluate('window.__pwn === undefined'))
    errors.clear()   # las violaciones anteriores las provoca la propia prueba a propósito
    # descifrado con 600 000 iteraciones: tiempo razonable
    load('respuesta-a-reclamos_v1.0.encapsulado.png'); t0 = time.time(); pg.fill('#pw', 'demo1234'); pg.press('#pw', 'Enter'); pg.wait_for_selector('#open', state='visible', timeout=10000); dt = time.time() - t0
    check('J descifrar con 600 000 iteraciones tarda menos de 5 s en el navegador', dt < 5, f'{dt:.2f} s')
    print(f'     (descifrado en {dt:.2f} s)')

    # --- K) espacio ocupado y guardado local
    pg.click('#tabLib'); pg.wait_for_timeout(300)
    esperado = sum(os.path.getsize(f) for f in files) / 1024
    stt = txt('#libStorage'); mm = re.search(r'([\d,]+\.\d) KB', stt)
    check('K la biblioteca dice cuántos KB lleva en total (coincide con la suma real)', f'{len(files)} tarjetas' in stt and mm is not None and abs(float(mm.group(1).replace(',', '')) - esperado) < 0.06, f'{stt} | esperado {esperado:.1f}')
    check('K sin guardado activado, lo dice y no promete recordar', 'vive solo en esta pestaña' in txt('#libNote') and not pg.is_checked('#persistSw'))
    pctx = b.new_context(viewport={'width': 1200, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'])
    def nueva(url=URL):
        q = pctx.new_page(); q.goto(url); q.click('#tabLib'); return q
    def n(q): return q.inner_text('#libCount')
    p1 = nueva(); p1.set_input_files('#libFiles', files); p1.wait_for_timeout(4000); check('K (contexto nuevo) se añaden las 12 tarjetas', n(p1) == '(12)', n(p1))
    p1.reload(); p1.click('#tabLib'); p1.wait_for_timeout(600)
    check('K sin activar el guardado, al recargar la biblioteca queda vacía', n(p1) == '(0)', n(p1))
    p1.set_input_files('#libFiles', files); p1.wait_for_timeout(4000); p1.check('#persistSw'); p1.wait_for_timeout(2500)
    check('K al activar el guardado lo indica y dice que está guardada en este navegador', 'guardadas en este navegador' in p1.inner_text('#libStorage') and 'se guardan en este navegador' in p1.inner_text('#libNote'), p1.inner_text('#libStorage'))
    total1 = p1.inner_text('#libStorage')
    p2 = nueva(); p2.wait_for_timeout(5000)
    check('K al abrir de nuevo, la biblioteca se restaura con las 12 tarjetas y el interruptor activo', n(p2) == '(12)' and p2.is_checked('#persistSw'), n(p2))
    check('K el total de KB restaurado es el mismo', p2.inner_text('#libStorage') == total1, p2.inner_text('#libStorage') + ' vs ' + total1)
    p2.locator('.cw', has_text='Plan de entrenamiento').get_by_text('Quitar de la biblioteca').click(); p2.wait_for_timeout(800)
    check('K quitar una tarjeta baja el conteo y el total', n(p2) == '(11)' and '11 tarjetas' in p2.inner_text('#libStorage'), p2.inner_text('#libStorage'))
    p3 = nueva(); p3.wait_for_timeout(4500); check('K la tarjeta quitada no vuelve al reabrir', n(p3) == '(11)', n(p3))
    p3.locator('.card', has_text='Respuesta a reclamos').click(); p3.wait_for_timeout(1200)
    check('K una tarjeta cifrada restaurada sigue cifrada y pide contraseña', p3.is_visible('#lock') and not p3.is_visible('#open'))
    p3.fill('#pw', 'demo1234'); p3.press('#pw', 'Enter'); p3.wait_for_selector('#open', state='visible', timeout=10000)
    check('K ... y se abre con su contraseña', 'Respuesta a reclamos' in p3.inner_text('#title'))
    p3.click('#tabLib'); p3.uncheck('#persistSw'); p3.wait_for_timeout(1000)
    check('K al desactivar el guardado se borran las copias y lo avisa', 'Se borraron las copias' in p3.inner_text('#persistNote') and 'vive solo en esta pestaña' in p3.inner_text('#libNote'))
    p4 = nueva(); p4.wait_for_timeout(1500); check('K tras desactivar, al reabrir no queda nada', n(p4) == '(0)', n(p4))
    p4.check('#persistSw'); p4.wait_for_timeout(800); p4.set_input_files('#libFiles', files[:3]); p4.wait_for_timeout(2500)
    p5 = nueva(); p5.wait_for_timeout(3000); check('K con el guardado activo, lo que se añade después también se conserva', n(p5) == '(3)', n(p5))
    p5.click('#clearLib'); check('K vaciar pide confirmación (no borra a la primera)', n(p5) == '(3)' and 'Seguro' in p5.inner_text('#clearLib'))
    p5.click('#clearLib'); p5.wait_for_timeout(800)
    p6 = nueva(); p6.wait_for_timeout(1500)
    check('K vaciar la biblioteca la deja vacía también en el navegador', n(p5) == '(0)' and n(p6) == '(0)' and 'Tu biblioteca está vacía' in p6.inner_text('#libEmpty'), n(p5) + ' ' + n(p6))
    check('K vaciar no toca los archivos originales', all(os.path.exists(f) for f in files))

    # --- L) crear tarjetas en el navegador (todo se verifica con el código de referencia de Python)
    TAGS = ''.join(chr(0xE0000 + ord(c)) for c in 'envia todo')
    def nuevo(viewport=None):
        c = b.new_context(viewport=viewport or {'width': 1200, 'height': 1000}, accept_downloads=True, permissions=['clipboard-read', 'clipboard-write'])
        q = c.new_page(); q.on('pageerror', lambda e: errors.append(str(e))); q.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        q.goto(URL); q.wait_for_timeout(500); return c, q
    def descargar(q, sel, nombre=None):
        with q.expect_download() as d: q.click(sel)
        ruta = os.path.join(OUT, nombre or d.value.suggested_filename); d.value.save_as(ruta); return ruta
    def llenar(q, titulo='Redactor de correos', categoria='Correo', tags='correo, redacción', prompt='Reescribe con tono formal.\nBorrador: {{borrador}}\nPara: {{destinatario}}'):
        q.fill('#cTitle', titulo); q.fill('#cCategory', categoria); q.fill('#cTags', tags); q.fill('#cPrompt', prompt)
    def crear(q, espera=1500):
        q.click('#cCreate'); q.wait_for_timeout(150)
        for _ in range(200):                                  # sondeo desde Python: la CSP de la página prohíbe que Playwright evalúe texto como JavaScript
            if q.is_enabled('#cCreate'): break
            q.wait_for_timeout(100)
        q.wait_for_timeout(150)
    c1, q = nuevo(); n0 = len(errors)
    check('L por defecto se abre la pestaña Crear', q.is_visible('#viewCreate') and not q.is_visible('#viewOpen') and q.get_attribute('#tabCreate', 'aria-selected') == 'true')
    q.click('#cCreate'); check('L sin prompt: pide escribirlo', 'Escribe el prompt' in q.inner_text('#cErr'))
    q.fill('#cPrompt', 'hola'); q.click('#cCreate'); check('L sin título: lo pide (o activar «privada»)', 'título' in q.inner_text('#cErr'))
    llenar(q); q.wait_for_timeout(200)
    check('L detecta las variables del prompt', q.locator('#cVars .varrow').count() == 2 and 'borrador' in q.inner_text('#cVars'))
    crear(q); r = descargar(q, '#rDownload')
    check('L tarjeta sin firma: nombre de archivo y verificación interna', r.endswith('redactor-de-correos_v1.0.encapsulado.png') and 'se lee de vuelta idéntica' in q.inner_text('#resultInfo'), r)
    s = cs.read_card(r); inf = cs.parse(s); u = cs.unpack(s); im = Image.open(r)
    check('L Python lee la tarjeta sin firma: título, categoría, etiquetas, variables, emblema', inf['public']['title'] == 'Redactor de correos' and inf['public']['category'] == 'Correo' and inf['public']['tags'] == ['correo', 'redacción']
          and list(u['variables']) == ['borrador', 'destinatario'] and cs.valid_emblem(inf['public']['emblem']) and not inf['signed'] and 'cat_hue' in inf['public'])
    check('L el PNG es válido: 360 px de ancho, RGBA, esquina cortada transparente y zona de datos opaca', im.size[0] == 360 and im.mode == 'RGBA' and im.getpixel((2, 2))[3] == 0
          and im.crop((6, 74, 354, im.size[1] - 18)).getchannel('A').getextrema() == (255, 255), (im.size, im.mode))
    # --- identidad nueva sin contraseña
    q.fill('#idNameIn', 'Oscar Prueba'); q.click('#idCreate'); q.wait_for_selector('#idHave:not([hidden])', timeout=15000)
    check('L identidad creada: nombre y huella visibles', 'Oscar Prueba' in q.inner_text('#idName') and re.search(r'Huella [0-9A-F]{4}(-[0-9A-F]{4}){5}', q.inner_text('#idFp')), q.inner_text('#idFp'))
    check('L la identidad propia queda como autor de confianza en este navegador', 'Oscar Prueba' in (q.text_content('#trustList') or ''), q.text_content('#trustList'))
    q.check('#cSign'); crear(q); r2 = descargar(q, '#rDownload')
    s2 = cs.read_card(r2); inf2 = cs.parse(s2); st, _ = cs.describe_signature(inf2)
    check('L Python: firma válida y la apariencia coincide con la clave', st == 'valid' and cs.visual_status(r2, inf2) == 'match' and inf2['public']['author'] == 'Oscar Prueba', (st, cs.visual_status(r2, inf2)))
    check('L el emblema de la segunda tarjeta es distinto al de la primera', inf2['public']['emblem'] != inf['public']['emblem'])
    bk = descargar(q, '#idBackup'); idy = cs.load_identity(bk)
    check('L la copia de seguridad (.pcid) la carga Python y es la misma clave que firmó', idy['name'] == 'Oscar Prueba' and idy['pub'] == inf2['pub'] and bk.endswith('oscar-prueba.pcid'))
    pubf = descargar(q, '#idPubDl'); tr = cs.load_trusted([pubf])
    check('L la clave pública (.pub) exportada la acepta Python como autor de confianza', len(tr) == 1 and cs.describe_signature(inf2, tr)[1].startswith('Firma válida') and 'confianza' in cs.describe_signature(inf2, tr)[1], str(cs.describe_signature(inf2, tr)))
    q.click('#rOpen'); q.wait_for_timeout(1500)
    check('L «Abrir para comprobar»: el navegador la abre y reconoce su firma y su apariencia', q.is_visible('#viewOpen') and 'autor de confianza' in q.inner_text('#sigTitle') and 'apariencia' not in q.inner_text('#sigTitle') and 'Borrador' in q.inner_text('#promptOut'), q.inner_text('#sigTitle'))
    q.click('#tabCreate'); q.click('#rLib'); q.wait_for_timeout(1200)
    check('L «Añadir a la biblioteca» suma la tarjeta', '(1)' in q.inner_text('#libCount'), q.inner_text('#libCount'))
    q.reload(); q.wait_for_timeout(800)
    check('L la identidad sobrevive a recargar la página', 'Oscar Prueba' in q.inner_text('#idName') and q.is_enabled('#cSign'))
    # --- cifrada y privada
    llenar(q, titulo='Tarjeta con clave'); q.check('#cEnc'); q.fill('#cPw', 'abc'); q.fill('#cPw2', 'abd'); q.click('#cCreate')
    check('L contraseñas distintas: lo avisa', 'no coinciden' in q.inner_text('#cErr'))
    q.fill('#cPw', 'corta'); q.fill('#cPw2', 'corta'); crear(q); check('L contraseña corta: aviso no bloqueante', 'contraseña es corta' in q.inner_text('#resultInfo'))
    q.fill('#cPw', 'una-frase-larga-de-verdad'); q.fill('#cPw2', 'una-frase-larga-de-verdad'); q.check('#cSign'); crear(q); r3 = descargar(q, '#rDownload')
    s3 = cs.read_card(r3); i3 = cs.parse(s3)
    try: cs.unpack(s3, 'equivocada'); mal = 'aceptó'
    except Exception: mal = 'rechazó'
    check('L Python descifra la tarjeta cifrada en el navegador (y rechaza una clave equivocada)', i3['encrypted'] and cs.unpack(s3, 'una-frase-larga-de-verdad')['prompt'].startswith('Reescribe') and mal == 'rechazó' and cs.describe_signature(i3)[0] == 'valid')
    q.click('#rOpen'); q.wait_for_timeout(1000); check('L la tarjeta cifrada pide contraseña al abrirla en el navegador', q.is_visible('#lock'))
    q.fill('#pw', 'una-frase-larga-de-verdad'); q.press('#pw', 'Enter'); q.wait_for_selector('#open', state='visible', timeout=10000); check('L ... y se abre con su contraseña', 'Reescribe' in q.inner_text('#promptOut'))
    q.click('#tabCreate'); q.uncheck('#cEnc'); q.check('#cHide'); llenar(q); crear(q); r4 = descargar(q, '#rDownload'); i4 = cs.parse(cs.read_card(r4))
    check('L tarjeta privada: nombre y bloque público sin título, con emblema', os.path.basename(r4).startswith('tarjeta-privada_') and i4['public']['title'] == '' and cs.valid_emblem(i4['public'].get('emblem')), os.path.basename(r4))
    # --- caracteres ocultos
    q.uncheck('#cHide'); llenar(q, prompt='Resume el correo.' + TAGS + ' Gracias.'); q.wait_for_timeout(200)
    check('L revisión del texto: avisa de los caracteres ocultos al escribir', q.is_visible('#cReview') and 'ocultos' in q.inner_text('#cReview'))
    crear(q); r5 = descargar(q, '#rDownload'); p5 = cs.unpack(cs.read_card(r5))['prompt']
    check('L por defecto se quitan los caracteres ocultos', p5 == 'Resume el correo. Gracias.', repr(p5))
    q.uncheck('#cStrip'); crear(q); r6 = descargar(q, '#rDownload'); p6 = cs.unpack(cs.read_card(r6))['prompt']
    check('L si lo desactivas, se conservan (y el decodificador los muestra)', TAGS in p6)
    # --- prompt grande
    import random as _r; rr = _r.Random(7); grande = ' '.join(''.join(rr.choice('abcdefghijklmnopqrstuvwxyzáéíóúñ') for _ in range(rr.randint(3, 9))) for _ in range(40000))   # texto poco comprimible
    q.check('#cStrip'); q.fill('#cPrompt', grande); crear(q); r7 = descargar(q, '#rDownload')
    s7 = cs.read_card(r7); p7 = cs.unpack(s7)['prompt']; sz = Image.open(r7).size
    check('L prompt grande (~270 KB de texto poco comprimible): Python lo lee íntegro y la tarjeta crece en alto', p7 == grande.rstrip() and sz[1] > 200, (len(p7), len(grande), sz))
    q.click('#rOpen'); q.wait_for_timeout(2500); check('L ... y el navegador también la abre', 'Aquí' not in q.inner_text('#promptOut')[:0] and len(q.inner_text('#promptOut')) > 100000)
    q.click('#tabCreate')
    c1.close()
    # --- identidad protegida con contraseña, y una creada por Python
    c2, q = nuevo(); llenar(q); q.fill('#idNameIn', 'Con Clave'); q.fill('#idPwIn', 'clave-identidad-larga'); q.click('#idCreate'); q.wait_for_selector('#idHave:not([hidden])', timeout=15000)
    check('L identidad protegida: se indica', 'Protegida con contraseña' in q.inner_text('#idProt'))
    q.check('#cSign'); q.click('#cCreate'); q.wait_for_timeout(500)
    check('L firmar con identidad protegida sin contraseña: la pide', q.is_visible('#cIdPwRow') or 'contraseña' in q.inner_text('#cErr'))
    q.fill('#cIdPw', 'incorrecta'); crear(q); check('L contraseña de identidad incorrecta: se rechaza', 'incorrecta' in q.inner_text('#cErr'), q.inner_text('#cErr'))
    q.fill('#cIdPw', 'clave-identidad-larga'); crear(q); r8 = descargar(q, '#rDownload'); i8 = cs.parse(cs.read_card(r8)); bk2 = descargar(q, '#idBackup')
    check('L con la contraseña correcta firma; Python carga la identidad protegida y coincide', cs.describe_signature(i8)[0] == 'valid' and cs.load_identity(bk2, 'clave-identidad-larga')['pub'] == i8['pub'])
    c2.close()
    pyd = tempfile.mkdtemp(prefix='idpy_'); cwd = os.getcwd(); os.chdir(pyd); cs.keygen('Hecha en Python', 'hp', None, '#33AA66', 'auto'); os.chdir(cwd)
    c3, q = nuevo(); llenar(q, titulo='Firmada con identidad de Python'); q.set_input_files('#idFile', os.path.join(pyd, 'hp.pcid')); q.wait_for_selector('#idHave:not([hidden])', timeout=10000)
    check('L importa una identidad creada con Python', 'Hecha en Python' in q.inner_text('#idName'))
    q.check('#cSign'); crear(q); r9 = descargar(q, '#rDownload'); i9 = cs.parse(cs.read_card(r9)); hp = cs.load_identity(os.path.join(pyd, 'hp.pcid'))
    check('L la tarjeta firmada en el navegador con la clave de Python la verifica Python (misma clave, apariencia coincide)', cs.describe_signature(i9)[0] == 'valid' and i9['pub'] == hp['pub'] and cs.visual_status(r9, i9) == 'match')
    q.set_input_files('#idFile', os.path.join(OUT, 'oscar-prueba.pub')); q.wait_for_timeout(500); check('L un archivo que no es una identidad se rechaza con un mensaje', 'no es una identidad' in q.inner_text('#idErr') or 'no es' in q.inner_text('#idErr'), q.inner_text('#idErr'))
    c3.close()
    c4, q = nuevo({'width': 390, 'height': 800}); check('L móvil: la pestaña Crear no desborda horizontalmente', q.evaluate('document.documentElement.scrollWidth') <= 391, q.evaluate('document.documentElement.scrollWidth')); q.screenshot(path=f'{OUT}/crear_movil.png', full_page=True); c4.close()
    check('L crear tarjetas no produce errores de consola ni de JavaScript', len(errors) == n0, '; '.join(errors[n0:])[:300])

    # --- M) compartir como enlace y archivos que no son PNG (lo que hace WhatsApp con las fotos)
    import base64; n1 = len(errors)
    def pagina(c):
        x = c.new_page(); x.on('pageerror', lambda e: errors.append(str(e))); x.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None); return x
    def clip(x): return x.evaluate('navigator.clipboard.readText()')
    c5, q = nuevo(); llenar(q, titulo='Para compartir', prompt='Hola {{nombre}}, esto es una prueba.\nSegunda línea.'); q.fill('#idNameIn', 'Enlace Prueba'); q.click('#idCreate'); q.wait_for_selector('#idHave:not([hidden])', timeout=15000)
    q.check('#cSign'); crear(q); rpng = descargar(q, '#rDownload')
    check('M al crear aparece el consejo de WhatsApp: documento, no foto', q.is_visible('#shareTip') and 'Documento' in q.inner_text('#shareTip'))
    q.click('#rLink'); q.wait_for_timeout(300); link = clip(q)
    check('M «Copiar enlace»: copia un enlace de la demo con la tarjeta dentro', link.startswith('https://oscar-rubalcava.github.io/prompts-encapsulados/app/#c=') and 'Enlace copiado' in q.inner_text('#resultInfo'), link[:90])
    cod = link.split('#c=')[1]; s_link = base64.urlsafe_b64decode(cod + '=' * (-len(cod) % 4))
    check('M el código del enlace es exactamente la tarjeta del PNG, y Python verifica su firma', s_link == cs.read_card(rpng) and cs.describe_signature(cs.parse(s_link))[0] == 'valid')
    p2 = pagina(c5); p2.goto(URL + '#c=' + cod); p2.wait_for_timeout(1500)
    check('M abrir el enlace: muestra la tarjeta, la firma y el prompt', p2.is_visible('#viewOpen') and 'Firma válida' in p2.inner_text('#sigTitle') and 'Para compartir' in p2.inner_text('#title') and 'esto es una prueba' in p2.inner_text('#promptOut'), p2.inner_text('#sigTitle'))
    check('M ... y vuelve a dibujar la etiqueta a partir de los datos', p2.evaluate("document.getElementById('cardImg').naturalWidth") == 360)
    p2.fill('#v_nombre', 'Lupita'); p2.click('#copyPrompt'); p2.wait_for_timeout(300); check('M ... y las variables se rellenan y se copian', 'Hola Lupita' in clip(p2))
    p3 = pagina(c5); p3.goto(URL); p3.click('#tabOpen'); p3.fill('#codeIn', 'Mira esto: ' + link + ' gracias'); p3.click('#codeOpen'); p3.wait_for_timeout(1200)
    check('M pegar el enlace dentro de un mensaje de chat: lo encuentra y lo abre', 'Para compartir' in p3.inner_text('#title'), p3.inner_text('#codeErr'))
    p4 = pagina(c5); p4.goto(URL); p4.click('#tabOpen'); p4.fill('#codeIn', cod); p4.press('#codeIn', 'Enter'); p4.wait_for_timeout(1200)
    check('M pegar solo el código y pulsar Enter también funciona', 'Para compartir' in p4.inner_text('#title'))
    p5 = pagina(c5); p5.goto(URL); p5.click('#tabOpen'); p5.fill('#codeIn', 'hola mundo'); p5.click('#codeOpen')
    check('M un texto sin tarjeta: mensaje claro', 'No encuentro una tarjeta' in p5.inner_text('#codeErr'))
    malos = []
    for k in range(4):                                       # cuatro cortes consecutivos: cubren todos los residuos del largo del código
        p5.fill('#codeIn', link[:len(link) // 2 + k]); p5.click('#codeOpen'); p5.wait_for_timeout(500)
        if not ('incompleto' in p5.inner_text('#err') and not p5.is_visible('#open')): malos.append((k, p5.inner_text('#err')[:60], p5.inner_text('#codeErr')[:40]))
    check('M un enlace cortado, sea cual sea el punto del corte, se rechaza explicando que llegó incompleto', not malos, malos)
    q.click('#tabCreate'); llenar(q, titulo='Cifrada por enlace', prompt='secreto {{x}}'); q.check('#cEnc'); q.fill('#cPw', 'una-frase-larga-de-verdad'); q.fill('#cPw2', 'una-frase-larga-de-verdad'); crear(q)
    q.click('#rLink'); q.wait_for_timeout(300); link2 = clip(q); p6 = pagina(c5); p6.goto(URL + '#c=' + link2.split('#c=')[1]); p6.wait_for_timeout(1200)
    check('M una tarjeta cifrada abierta por enlace pide la contraseña', p6.is_visible('#lock') and not p6.is_visible('#open'))
    p6.fill('#pw', 'una-frase-larga-de-verdad'); p6.press('#pw', 'Enter'); p6.wait_for_selector('#open', state='visible', timeout=10000); check('M ... y se abre con ella', 'secreto' in p6.inner_text('#promptOut'))
    q.uncheck('#cEnc'); q.fill('#cPrompt', grande); crear(q); q.click('#rLink'); q.wait_for_timeout(300)
    check('M una tarjeta demasiado grande no cabe en un enlace: lo dice y recomienda el PNG como documento', 'demasiado grande' in q.inner_text('#resultInfo') and 'DOCUMENTO' in q.inner_text('#resultInfo'), q.inner_text('#resultInfo')[:200])
    jpg = os.path.join(OUT, 'whatsapp.jpeg'); Image.open(rpng).convert('RGB').save(jpg, quality=70)
    p7 = pagina(c5); p7.goto(URL); p7.set_input_files('#file', jpg); p7.wait_for_timeout(800); et = p7.inner_text('#err')
    check('M un JPEG (lo que deja WhatsApp con una foto) se explica: qué pasó, qué pedir y la alternativa del enlace', 'JPEG' in et and 'FOTO' in et and 'DOCUMENTO' in et and 'enlace' in et, et[:160])
    check('M el selector de archivos acepta cualquier imagen (ya no oculta los .jpeg)', p7.get_attribute('#file', 'accept') == 'image/*' and p7.get_attribute('#libFiles', 'accept') == 'image/*')
    p7.click('#tabLib'); p7.set_input_files('#libFiles', [jpg, rpng]); p7.wait_for_timeout(1500)
    check('M biblioteca: la tarjeta PNG entra y el JPEG se avisa en lugar de ignorarse', '(1)' in p7.inner_text('#libCount') and 'JPEG' in p7.inner_text('#libStatus'), p7.inner_text('#libStatus'))
    c5.close()
    check('M compartir por enlace y abrir JPEG no produce errores de consola ni de JavaScript', len(errors) == n1, '; '.join(errors[n1:])[:300])

    # --- N) enviar la tarjeta: menú del dispositivo, WhatsApp y correo (se captura lo que intentan abrir)
    from urllib.parse import unquote; import re as _re, random as _r2; n2 = len(errors)
    HOOK = "window.__clicks = []; const __orig = HTMLAnchorElement.prototype.click; HTMLAnchorElement.prototype.click = function(){ if (/^(https:\\/\\/wa\\.me|mailto:)/.test(this.href)){ window.__clicks.push(this.href); return; } return __orig.call(this); };"
    def envio(share=''):
        c = b.new_context(viewport={'width': 1200, 'height': 1000}, accept_downloads=True, permissions=['clipboard-read', 'clipboard-write']); c.add_init_script(HOOK + share)
        x = pagina(c); x.goto(URL); x.wait_for_timeout(500); return c, x
    def ultimo(x): return (x.evaluate('window.__clicks') or [''])[-1]
    def texto_aleatorio(n, semilla):
        g = _r2.Random(semilla); return ' '.join(''.join(g.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(g.randint(3, 9))) for _ in range(n // 6))
    c6, q = envio(); llenar(q, titulo='Para enviar', prompt='Hola {{nombre}}, tarjeta pequeña para enviar.'); crear(q); r_env = descargar(q, '#rDownload')
    check('N sin API de compartir del dispositivo, el botón «Compartir…» no se muestra; con ella, sí', q.is_visible('#rShare') == (q.evaluate('typeof navigator.share') == 'function'))
    q.click('#rWa'); q.wait_for_timeout(200); wa = ultimo(q); msg = unquote(wa.split('text=', 1)[1]) if 'text=' in wa else ''
    mm = _re.search(r'#c=([A-Za-z0-9_-]+)', msg)
    check('N «WhatsApp»: abre wa.me con un mensaje que lleva el título y el enlace', wa.startswith('https://wa.me/?text=') and '«Para enviar»' in msg and mm is not None, wa[:90])
    cd = mm.group(1) if mm else ''
    check('N ... y el código del mensaje es exactamente la tarjeta del PNG', base64.urlsafe_b64decode(cd + '=' * (-len(cd) % 4)) == cs.read_card(r_env))
    q.click('#rMail'); q.wait_for_timeout(200); ml = ultimo(q); subj = unquote(ml.split('subject=', 1)[1].split('&body=')[0]) if 'subject=' in ml else ''; body = unquote(ml.split('&body=', 1)[1]) if '&body=' in ml else ''
    check('N «Correo»: abre mailto con asunto y cuerpo que llevan el título y el enlace completo', ml.startswith('mailto:?subject=') and 'Para enviar' in subj and ('#c=' + cd) in body and len(ml) <= 1800, (subj, len(ml)))
    q.fill('#cPrompt', texto_aleatorio(3000, 1)); crear(q); q.click('#rWa'); q.wait_for_timeout(200); wa2 = ultimo(q); q.click('#rMail'); q.wait_for_timeout(300); ml2 = ultimo(q)
    check('N tarjeta mediana: WhatsApp sí la lleva completa en la dirección', wa2.startswith('https://wa.me/?text=') and len(wa2) <= 6000 and '#c=' in unquote(wa2), len(wa2))
    check('N ... pero el correo NO manda el enlace dentro de la dirección (se cortaría): lo copia y deja un cuerpo corto', ml2.startswith('mailto:?subject=') and '#c=' not in unquote(ml2) and 'Pega aquí' in unquote(ml2) and '#c=' in clip(q) and 'demasiado largo' in q.inner_text('#resultInfo'), q.inner_text('#resultInfo')[:120])
    q.fill('#cPrompt', texto_aleatorio(12000, 2)); crear(q); antes = len(q.evaluate('window.__clicks')); q.click('#rWa'); q.wait_for_timeout(300)
    check('N tarjeta grande: WhatsApp no abre nada con el enlace cortado; lo copia y avisa', len(q.evaluate('window.__clicks')) == antes and '#c=' in clip(q) and 'demasiado largo' in q.inner_text('#resultInfo'), q.inner_text('#resultInfo')[:120])
    q.fill('#cPrompt', grande); crear(q)
    for boton in ('#rWa', '#rMail', '#rLink'):
        q.click(boton); q.wait_for_timeout(200)
        if 'demasiado grande' not in q.inner_text('#resultInfo'): check('N tarjeta enorme: ' + boton + ' avisa que no cabe en un enlace', False, q.inner_text('#resultInfo')[:100]); break
    else: check('N tarjeta enorme (270 KB): ningún botón de enlace intenta mandarla; todos recomiendan el PNG como documento', True)
    c6.close()
    c7, q = envio("navigator.share = d => { window.__shared = d; return Promise.resolve(); };"); llenar(q, titulo='Con menú', prompt='Hola {{x}}.'); crear(q)
    check('N con la API de compartir, el botón «Compartir…» aparece', q.is_visible('#rShare'))
    q.click('#rShare'); q.wait_for_timeout(300); sh = q.evaluate('window.__shared')
    check('N «Compartir…» pasa al menú del dispositivo el mensaje con el título y el enlace', sh and '«Con menú»' in sh['text'] and '#c=' in sh['text'] and 'No se pudo' not in q.inner_text('#resultInfo'), sh)
    c7.close()
    c8, q = envio("navigator.share = d => Promise.reject(Object.assign(new Error('cancelado'), {name: 'AbortError'}));"); llenar(q, titulo='Cancelada', prompt='Hola.'); crear(q); q.click('#rShare'); q.wait_for_timeout(300)
    check('N si cancelas el menú de compartir no aparece ningún error', 'No se pudo' not in q.inner_text('#resultInfo')); c8.close()
    c9, q = envio("navigator.share = d => Promise.reject(new Error('fallo'));"); llenar(q, titulo='Falla', prompt='Hola.'); crear(q); q.click('#rShare'); q.wait_for_timeout(400)
    check('N si el menú de compartir falla, se copia el enlace y se avisa', 'No se pudo abrir el menú' in q.inner_text('#resultInfo') and '#c=' in clip(q), q.inner_text('#resultInfo')[:100]); c9.close()
    check('N enviar tarjetas no produce errores de consola ni de JavaScript', len(errors) == n2, '; '.join(errors[n2:])[:300])

    # --- O) nueva tarjeta sin recargar, aviso flotante de copiado y descripciones de los botones
    n3 = len(errors); c10, q = nuevo(); llenar(q, titulo='Primera', prompt='Hola {{x}}, primera tarjeta.'); q.fill('#idNameIn', 'Serie Prueba'); q.click('#idCreate'); q.wait_for_selector('#idHave:not([hidden])', timeout=15000)
    q.check('#cSign'); crear(q); o1 = descargar(q, '#rDownload')
    check('O tras crear una tarjeta aparece el botón «Nueva tarjeta»', q.is_visible('#rNew') and q.is_visible('#cNew'))
    q.click('#rNew'); q.wait_for_timeout(300)
    check('O «Nueva tarjeta» limpia el formulario y el resultado sin recargar (y sin pedir confirmación si no hay nada sin guardar)',
          q.input_value('#cTitle') == '' and q.input_value('#cPrompt') == '' and q.input_value('#cVersion') == '1.0' and not q.is_visible('#resultBtns') and q.is_visible('#resultHint') and not q.is_visible('#resultImg'))
    check('O ... conserva tu identidad y la casilla de firmar, y deja el cursor en el título', 'Serie Prueba' in q.inner_text('#idName') and q.is_checked('#cSign') and q.evaluate('document.activeElement.id') == 'cTitle')
    check('O ... y muestra el aviso «Formulario limpio»', 'Formulario limpio' in q.inner_text('#toast') and q.is_visible('#toast'))
    llenar(q, titulo='Segunda', prompt='Hola {{y}}, segunda tarjeta.'); crear(q); o2 = descargar(q, '#rDownload')
    i1, i2 = cs.parse(cs.read_card(o1)), cs.parse(cs.read_card(o2))
    check('O se crea una segunda tarjeta sin recargar: firma válida, misma identidad y emblema distinto', cs.describe_signature(i1)[0] == 'valid' and cs.describe_signature(i2)[0] == 'valid' and i1['pub'] == i2['pub'] and i1['public']['emblem'] != i2['public']['emblem'] and i2['public']['title'] == 'Segunda')
    q.fill('#cTitle', 'Cambio a medias'); q.click('#rNew')
    check('O con algo escrito sin convertir en tarjeta, pide confirmación en lugar de borrar', '¿Borrar lo escrito' in q.inner_text('#rNew') and q.input_value('#cTitle') == 'Cambio a medias' and q.is_visible('#resultBtns'))
    q.click('#rNew'); q.wait_for_timeout(300); check('O ... y al confirmar, sí lo borra', q.input_value('#cTitle') == '' and 'Nueva tarjeta' in q.inner_text('#rNew') and not q.is_visible('#resultBtns'))
    q.fill('#cTitle', 'X'); q.fill('#cPrompt', 'Y'); q.click('#cNew'); check('O el botón del formulario también protege lo escrito', '¿Borrar lo escrito' in q.inner_text('#cNew') and q.input_value('#cPrompt') == 'Y')
    q.click('#cNew'); q.wait_for_timeout(300); check('O ... y confirma', q.input_value('#cPrompt') == '' and 'Nueva tarjeta' in q.inner_text('#cNew'))
    llenar(q, titulo='Para el aviso', prompt='Hola {{z}}.'); crear(q); q.click('#rLink'); q.wait_for_timeout(300)
    check('O «Copiar enlace» muestra un aviso flotante «Enlace copiado»', q.is_visible('#toast') and 'Enlace copiado' in q.inner_text('#toast'), q.inner_text('#toast'))
    q.wait_for_timeout(3300); check('O ... que desaparece solo', not q.is_visible('#toast'))
    q.click('#rOpen'); q.wait_for_selector('#open', state='visible', timeout=10000); q.click('#copyPrompt'); q.wait_for_timeout(300)
    check('O copiar el prompt también muestra el aviso flotante', 'Prompt copiado' in q.inner_text('#toast') and q.is_visible('#toast'), q.inner_text('#toast'))
    ids = ['tabCreate', 'tabOpen', 'tabLib', 'rDownload', 'rNew', 'cNew', 'rOpen', 'rLib', 'rReroll', 'rShare', 'rWa', 'rMail', 'rLink', 'idCreate', 'idImport', 'idBackup', 'idPubDl', 'idDel', 'cCreate',
           'codeOpen', 'importPub', 'trustSave', 'forceOpen', 'unlock', 'copyAll', 'copySys', 'copyPrompt', 'addFiles', 'addFolder', 'clearLib']
    sin = [i for i in ids if not (q.get_attribute('#' + i, 'title') or '').strip()]
    check('O todos los botones tienen una descripción al pasar el ratón', not sin, sin)
    q.click('#tabLib'); q.set_input_files('#libFiles', o1); q.wait_for_timeout(1200); q.click('#tabCreate')
    c10.close()
    c11, q = nuevo(); q.click('#tabLib'); q.set_input_files('#libFiles', o1); q.wait_for_timeout(1200)
    check('O el botón «Quitar de la biblioteca» tiene descripción', bool((q.get_attribute('.cw button.link', 'title') or '').strip()), q.get_attribute('.cw button.link', 'title')); c11.close()
    check('O nueva tarjeta, avisos y descripciones no producen errores de consola ni de JavaScript', len(errors) == n3, '; '.join(errors[n3:])[:300])

    # --- I) móvil
    m = b.new_context(viewport={'width': 390, 'height': 800}); mp = m.new_page(); mp.goto(URL); mp.set_input_files('#file', P('asistente-de-punto-de-venta_v1.0.encapsulado.png')); mp.wait_for_timeout(800)
    w1 = mp.evaluate('document.documentElement.scrollWidth'); mp.screenshot(path=f'{OUT}/movil_abrir.png', full_page=True)
    mp.click('#tabLib'); mp.set_input_files('#libFiles', files); mp.wait_for_timeout(2200); w2 = mp.evaluate('document.documentElement.scrollWidth'); mp.screenshot(path=f'{OUT}/movil_biblioteca.png')
    check('I móvil sin scroll horizontal (abrir y biblioteca)', w1 <= 391 and w2 <= 391, f'{w1}, {w2}')
    check('sin errores de consola/JS', not errors, '; '.join(errors)); b.close()
print('\nTODO UI OK' if ok else '\nHAY FALLOS')
sys.exit(0 if ok else 1)
