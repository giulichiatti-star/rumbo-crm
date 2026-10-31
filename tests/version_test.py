"""Prueba del aviso «hay una versión nueva» (skill aviso-version-nueva, receta B).

Reproduce el caso real con un servidor local y un navegador real:
  1. Con la misma versión publicada NO aparece ningún aviso.
  2. Se «publica» una versión nueva (se cambia version.json en disco) SIN recargar la pestaña, y se dispara
     el chequeo como lo hace el navegador: foco de la ventana, volver a la pestaña, y pageshow con persisted=true
     (pestaña recuperada de la memoria, el caso del celular).
  3. El aviso aparece, NO se recarga sola (lo que la persona estaba escribiendo sigue ahí) y no se puede descartar.
  4. Tocar «Actualizar» recarga de verdad, trae la versión nueva, y la sesión y los datos siguen (no pide login).
  5. La versión del repositorio es consistente: meta de index.html == version.json.

Uso: python3 tests/version_test.py
"""
import functools
import http.server
import json
import pathlib
import re
import shutil
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
INDEX = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else RAIZ / "index.html"
fallas, comprobaciones = [], 0


def comprobar(ok, texto):
    global comprobaciones
    comprobaciones += 1
    if not ok:
        fallas.append(texto)


def meta_de(html):
    m = re.search(r'<meta name="app-version" content="([^"]*)">', html)
    return m.group(1) if m else None


def publicar(carpeta, version, solo_json=False):
    (carpeta / "version.json").write_text(json.dumps({"v": version}))
    if not solo_json:
        h = (carpeta / "index.html").read_text(encoding="utf-8")
        (carpeta / "index.html").write_text(re.sub(r'(<meta name="app-version" content=")[^"]*(">)', rf"\g<1>{version}\g<2>", h), encoding="utf-8")


def main():
    # 5) Consistencia en el repositorio
    v_meta = meta_de(INDEX.read_text(encoding="utf-8"))
    v_json = json.loads((RAIZ / "version.json").read_text())["v"]
    comprobar(v_meta == v_json, f"index.html dice «{v_meta}» y version.json dice «{v_json}»: hay que estampar la versión (python3 scripts/estampar_version.py)")
    comprobar(bool(v_meta) and re.fullmatch(r"\d{8}-\d{6}", v_meta) is not None, f"la versión «{v_meta}» no tiene el formato aaaammdd-hhmmss")

    tmp = pathlib.Path(tempfile.mkdtemp())
    shutil.copy(INDEX, tmp / "index.html")
    shutil.copy(RAIZ / "version.json", tmp / "version.json")
    publicar(tmp, "20260101-000000")                      # versión «instalada» en el navegador
    class Callado(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass
    handler = functools.partial(Callado, directory=str(tmp))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

    visible = "() => document.getElementById('nueva').classList.contains('on')"
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={"width": 1280, "height": 800})
        ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("http://127.0.0.1") else r.abort())
        pag = ctx.new_page()
        pag.goto(url)
        pag.evaluate("() => document.getElementById('login').style.display='none'")

        # 1) Misma versión: sin aviso
        pag.evaluate("() => window.dispatchEvent(new Event('focus'))"); pag.wait_for_timeout(400)
        comprobar(not pag.evaluate(visible), "Apareció el aviso aunque la versión publicada es la misma")

        # Lo que la persona está haciendo, a medio escribir, y su sesión
        pag.evaluate("() => {UI.view='hoy';render();newTask()}")
        pag.fill("dialog input[name=txt]", "Texto a medio escribir")
        pag.evaluate("() => {window.__marca = 'pestaña vieja'; localStorage.setItem('sb-prueba-auth-token', JSON.stringify({access_token:'abc', user:{email:'a@b.com'}}))}")

        # 2) Se publica una versión nueva, sin recargar la pestaña
        publicar(tmp, "20260102-000000", solo_json=True)
        pag.evaluate("() => window.dispatchEvent(new Event('focus'))"); pag.wait_for_timeout(500)
        comprobar(pag.evaluate(visible), "No apareció el aviso al volver el foco a la ventana")

        # 3) No se recarga sola, no se puede descartar, y no pisa lo escrito
        pag.wait_for_timeout(3000)
        comprobar(pag.evaluate("() => window.__marca") == "pestaña vieja", "La página se recargó sola")
        comprobar(pag.input_value("dialog input[name=txt]") == "Texto a medio escribir", "Se perdió lo que se estaba escribiendo")
        comprobar(pag.locator("#nueva button").count() == 1, "El aviso tiene más de un botón: no debe poder descartarse")
        comprobar("Actualizar" in pag.inner_text("#nueva button"), "El botón del aviso no dice «Actualizar»")
        # Con el formulario abierto la página de atrás está bloqueada: el aviso tiene que estar también adentro y poder tocarse
        comprobar(pag.locator("dialog .nueva-dentro button").count() == 1, "Con un formulario abierto el aviso no aparece dentro del formulario")

        # 4) Actualizar: llega la versión nueva (el sitio ya la sirve) y la sesión sigue
        publicar(tmp, "20260102-000000")
        pag.click("dialog .nueva-dentro button")       # con el formulario todavía abierto
        pag.wait_for_load_state("load"); pag.wait_for_timeout(600)
        comprobar(pag.evaluate("() => window.__marca") is None, "Tocar Actualizar no recargó la página")
        comprobar(pag.evaluate("() => document.querySelector('meta[name=app-version]').content") == "20260102-000000", "Tras actualizar no quedó la versión nueva")
        comprobar(not pag.evaluate(visible), "El aviso quedó visible después de actualizar")
        sesion = pag.evaluate("() => localStorage.getItem('sb-prueba-auth-token')")
        comprobar(sesion is not None and "a@b.com" in sesion, "Actualizar tocó la sesión: se perdió el acceso")
        comprobar(pag.evaluate("() => !!localStorage.getItem('rumbo_v3')"), "Actualizar borró los datos guardados")

        # 4b) Sin formulario abierto, el botón de arriba también actualiza
        publicar(tmp, "20260102-500000", solo_json=True)
        pag.evaluate("() => window.dispatchEvent(new Event('focus'))"); pag.wait_for_timeout(500)
        comprobar(pag.evaluate(visible), "No apareció el aviso (sin formulario abierto)")
        publicar(tmp, "20260102-500000")
        pag.evaluate("() => {window.__marca = 'otra'}")
        pag.click("#nbtn"); pag.wait_for_load_state("load"); pag.wait_for_timeout(600)
        comprobar(pag.evaluate("() => window.__marca") is None and not pag.evaluate(visible), "El botón de arriba no actualizó")
        comprobar("a@b.com" in (pag.evaluate("() => localStorage.getItem('sb-prueba-auth-token')") or ""), "El botón de arriba tocó la sesión: se perdió el acceso")

        # 2b) Pestaña recuperada de la memoria del navegador (bfcache): pageshow con persisted=true
        publicar(tmp, "20260103-000000", solo_json=True)
        pag.evaluate("() => window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))"); pag.wait_for_timeout(500)
        comprobar(pag.evaluate(visible), "No apareció el aviso al recuperar la pestaña de la memoria (pageshow persisted)")

        # 2c) Volver a la pestaña (visibilitychange)
        pag.goto(url); publicar(tmp, "20260104-000000", solo_json=True)
        pag.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))"); pag.wait_for_timeout(500)
        comprobar(pag.evaluate(visible), "No apareció el aviso al volver a la pestaña")

        # Con el chequeo apagado por la propia página (sin servidor de versión): no debe romper nada
        publicar(tmp, "20260104-000000")
        (tmp / "version.json").unlink()
        pag.goto(url); pag.evaluate("() => window.dispatchEvent(new Event('focus'))"); pag.wait_for_timeout(400)
        comprobar(not pag.evaluate(visible), "Sin version.json apareció un aviso falso")
        ctx.close(); nav.close()
    srv.shutdown(); shutil.rmtree(tmp, ignore_errors=True)

    print(f"{comprobaciones} comprobaciones.")
    if fallas:
        print(f"FALLAS: {len(fallas)}")
        for f in fallas:
            print("  -", f)
        sys.exit(1)
    print("EL AVISO DE VERSIÓN NUEVA FUNCIONA.")


if __name__ == "__main__":
    main()
