"""Prueba de que las pantallas cuadran (skill «pantallas-que-cuadran»).

Abre index.html en un navegador real a 13 anchos de pantalla y recorre TODAS las
pantallas, paneles laterales, formularios emergentes y el chat. Falla si:
  - la página se puede desplazar hacia los costados;
  - algún botón, campo o selector visible queda (aunque sea en parte) fuera de la ventana;
  - un campo de texto o número muestra su valor cortado;
  - un formulario emergente o panel lateral se sale de la ventana.

Uso:   python3 tests/pantallas_cuadran_test.py
Salida: 0 = todo cuadra, 1 = hay fallas (se listan una por una).
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = (RAIZ / "index.html").as_uri()

# 910 y 1093 equivalen a usar el navegador con zoom 150 % y 125 % en una notebook de 1366.
ANCHOS = [(360, 740), (390, 844), (412, 915), (768, 1024), (820, 1180), (910, 700), (1024, 768),
          (1093, 700), (1180, 820), (1280, 720), (1366, 768), (1536, 864), (1920, 1080)]

# Datos largos y realistas que la gente carga de verdad: si cuadra con esto, cuadra con lo normal.
PREPARAR = """() => {
  const L = document.getElementById('login'); if (L) L.style.display = 'none';
  S.clients[0].nombre = 'Establecimiento Agropecuario La Esperanza del Norte S.R.L.';
  S.clients[0].titular = 'María Fernanda Rodríguez de la Vega';
  S.clients[0].zona = 'General Pico, La Pampa';
  S.clients[0].honv = 12345678.9; S.clients[0].hon = 1234567;
  S.lotes[0].nombre = 'Recría a pasto con verdeo de invierno y terminación a corral';
  S.tasks.push({id: 90, txt: 'Llamar al veterinario para coordinar la vacunación y la sanidad de ingreso del lote completo', cid: 1, due: iso(0), done: false, resp: 'Yo'});
  S.chat.msgs.general.push({a: 'Yo', t: Date.now(), x: 'Mensaje largo '.repeat(12)});
  S.mercado.push({f: '2026-11', inv: 6200, gor: 4250, maiz: 287000, soja: 560000, gas: 2300, usd: 1517, nota: 'Fuente de ejemplo con un texto bastante largo para probar'});
  return true;
}"""

MEDIR = """async (nombre) => {
  const W = innerWidth, H = innerHeight, fallas = [];
  const nombreDe = e => (e.id || e.dataset.p || e.dataset.act || e.className || e.tagName).toString().slice(0, 30);
  // Zonas con scroll propio (tablas, línea de tiempo, tablero, menú): se miden aparte, no deben desplazar la página.
  const CON_SCROLL = '.tablewrap,.gantt,.kan,.seg,.ctabs,#msgs';
  window.scrollTo(9999, 0); const sx = window.scrollX; window.scrollTo(0, 0);
  if (sx > 0) fallas.push('la página se desplaza hacia los costados (' + sx + ' px)');
  const raiz = document.querySelector('dialog[open]') || document.querySelector('.dr.on') || document.querySelector('.chat.on') || document.body;
  const marco = raiz === document.body ? null : raiz.getBoundingClientRect();
  if (marco && (marco.left < -1 || marco.right > W + 1 || marco.top < -1 || marco.bottom > H + 1))
    fallas.push('el cuadro se sale de la ventana: ' + [marco.left, marco.top, marco.right, marco.bottom].map(Math.round).join(','));
  const lista = raiz === document.body ? '#main button,#main input,#main select,#seg button,header input,header button,header .bellb' : 'button,input,select,textarea';
  raiz.querySelectorAll(lista).forEach(e => {
    if (e.closest(CON_SCROLL) && raiz === document.body) return;
    const r = e.getBoundingClientRect(); if (!r.width || !r.height) return;
    if (r.left < -1 || r.right > W + 1) fallas.push('"' + nombreDe(e) + '" fuera de la ventana (' + Math.round(r.left) + ' a ' + Math.round(r.right) + ', ventana ' + W + ')');
  });
  raiz.querySelectorAll('input:not([type=checkbox]):not([type=range]):not([type=file]),textarea').forEach(i => {
    const r = i.getBoundingClientRect(); if (!r.width) return;
    if (i.value && i.scrollWidth > i.clientWidth + 1) fallas.push('campo "' + nombreDe(i) + '" corta su valor: ' + i.value.slice(0, 40));
  });
  return fallas;
}"""

PANTALLAS = [  # (nombre, preparación en la página, limpieza)
    ("Hoy", "UI.view='hoy';render()"),
    ("Ciclo · línea de tiempo", "UI.view='ciclo';UI.cview='tiempo';render()"),
    ("Ciclo · tablero", "UI.view='ciclo';UI.cview='tablero';render()"),
    ("Productores", "UI.view='gente';render()"),
    ("Mercado", "UI.view='mercado';render()"),
    ("Costos · forraje", "UI.view='costos';UI.ctab='forraje';render()"),
    ("Costos · dietas", "UI.view='costos';UI.ctab='dietas';render()"),
    ("Costos · biblioteca", "UI.view='costos';UI.ctab='biblioteca';render()"),
    ("Real vs modelo", "UI.view='real';render()"),
    ("Análisis · calendario", "UI.view='analisis';UI.atab='cal';render()"),
    ("Análisis · sensibilidad", "UI.view='analisis';UI.atab='sens';render()"),
    ("Análisis · comparador", "UI.view='analisis';UI.atab='comp';render()"),
    ("Análisis · curva", "UI.view='analisis';UI.atab='curva';render()"),
    ("Panel · productor", "UI.view='hoy';render();openDrawer('c',1)"),
    ("Panel · lote", "UI.view='hoy';render();openDrawer('l',1)"),
    ("Panel · pendientes", "UI.view='hoy';render();openDrawer('a')"),
    ("Formulario · nuevo productor", "UI.view='gente';render();newClient()"),
    ("Formulario · nueva tarea", "UI.view='hoy';render();newTask()"),
    ("Formulario · editar lote", "UI.view='ciclo';render();editLote(1)"),
    ("Formulario · lote cerrado", "UI.view='real';render();closeLote()"),
    ("Formulario · precios del mes", "UI.view='mercado';render();newPrecio()"),
    ("Chat", "UI.view='hoy';render();toggleChat(true)"),
]
CIERRA = "(()=>{const d=document.getElementById('dlg');if(d.open)d.close();closeDrawer();toggleChat(false)})()"


def main():
    fallas_total = []
    pruebas = 0
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for ancho, alto in ANCHOS:
            ctx = nav.new_context(viewport={"width": ancho, "height": alto})
            # Sin red: la prueba mide la pantalla, no la conexión con Supabase ni las tipografías.
            ctx.route("**/*", lambda ruta: ruta.continue_() if ruta.request.url.startswith("file:") else ruta.abort())
            pag = ctx.new_page()
            pag.goto(URL)
            pag.evaluate(PREPARAR)
            for nombre, preparar in PANTALLAS:
                pag.evaluate("() => {" + CIERRA + "}")
                pag.evaluate("() => {" + preparar + "}")
                # Los paneles y el chat se deslizan al abrir: se espera a que terminen antes de medir.
                pag.wait_for_timeout(550 if nombre.startswith(('Panel', 'Chat')) else 120)
                pruebas += 1
                for f in pag.evaluate(MEDIR, nombre):
                    fallas_total.append(f"{ancho}x{alto} · {nombre}: {f}")
            ctx.close()
        nav.close()
    print(f"{pruebas} combinaciones medidas ({len(ANCHOS)} anchos x {len(PANTALLAS)} pantallas).")
    if fallas_total:
        print(f"FALLAS: {len(fallas_total)}")
        vistas = {}
        for f in fallas_total:
            medida, resto = f.split(" · ", 1)
            pantalla, texto = resto.split(": ", 1)
            v = vistas.setdefault(texto, {"anchos": set(), "pantallas": set()})
            v["anchos"].add(medida.split(" ")[0]); v["pantallas"].add(pantalla)
        for texto, v in vistas.items():
            anchos = sorted(v["anchos"], key=lambda a: int(a.split("x")[0]))
            print(f"  - {texto}\n      pantallas: {', '.join(sorted(v['pantallas']))} | anchos: {len(anchos)} ({anchos[0]} a {anchos[-1]})")
        sys.exit(1)
    print("TODO CUADRA.")


if __name__ == "__main__":
    main()
