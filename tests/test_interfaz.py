import os, sys, glob, re
from playwright.sync_api import sync_playwright
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); EX = os.path.abspath(os.path.join(BASE, 'ejemplos')); URL = 'file://' + os.path.abspath(os.path.join(BASE, 'encapsulados.html'))
import tempfile; OUT = tempfile.mkdtemp(prefix='encapsulados_ui_')
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

    # --- I) móvil
    m = b.new_context(viewport={'width': 390, 'height': 800}); mp = m.new_page(); mp.goto(URL); mp.set_input_files('#file', P('asistente-de-punto-de-venta_v1.0.encapsulado.png')); mp.wait_for_timeout(800)
    w1 = mp.evaluate('document.documentElement.scrollWidth'); mp.screenshot(path=f'{OUT}/movil_abrir.png', full_page=True)
    mp.click('#tabLib'); mp.set_input_files('#libFiles', files); mp.wait_for_timeout(2200); w2 = mp.evaluate('document.documentElement.scrollWidth'); mp.screenshot(path=f'{OUT}/movil_biblioteca.png')
    check('I móvil sin scroll horizontal (abrir y biblioteca)', w1 <= 391 and w2 <= 391, f'{w1}, {w2}')
    check('sin errores de consola/JS', not errors, '; '.join(errors)); b.close()
print('\nTODO UI OK' if ok else '\nHAY FALLOS')
sys.exit(0 if ok else 1)
