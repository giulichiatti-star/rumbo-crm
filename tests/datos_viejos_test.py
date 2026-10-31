"""Prueba de que una versión nueva de la app NO rompe los datos que alguien ya guardó con una versión vieja.

Arma «datos de una versión vieja» (les faltan campos y tablas que las versiones nuevas agregaron) con cosas que la
persona cargó (una tarea, un lote renombrado, un precio, otro campo) y verifica que, por cada camino por el que
pueden entrar a la app, queden completos SIN perder nada de lo cargado y sin errores en ninguna pantalla:
  1. guardados en el aparato (localStorage)   2. traídos del servidor   3. restaurados de una copia del servidor
  4. cargados desde un archivo descargado    5. datos dañados (no deben romper el arranque)
  6. cambios que no son «agregar» (renombrar, convertir): el mecanismo de migraciones por número de esquema.
Uso: python3 tests/datos_viejos_test.py [ruta/a/index.html]
"""
import json
import pathlib
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pantallas_cuadran_test as base  # noqa: E402
import sync_test as sy  # noqa: E402

URL, RAIZ = sy.URL, sy.RAIZ
fallas, comprobaciones = [], 0


def comprobar(ok, texto):
    global comprobaciones
    comprobaciones += 1
    if not ok:
        fallas.append(texto)


def datos_viejos(actual):
    """Lo que habría guardado una versión anterior: sin lo que se agregó después, y con lo que cargó la persona."""
    d = json.loads(json.dumps(actual))
    for k in ("cal", "curva", "comp", "esquema", "fdem", "resolved", "seen"):
        d.pop(k, None)
    d["cfg"].pop("desv", None)
    d["clients"][0].pop("hist", None); d["clients"][0].pop("notas", None); d["clients"][0].pop("hon", None)
    d["lotes"][0].pop("real", None); d["lotes"][0].pop("san", None); d["lotes"][0].pop("sis", None)
    d["bib"][0].pop("gmin", None); d["bib"][0].pop("dg", None)
    d["rec"][0].pop("perfil", None)
    d["mercado"][0].pop("soja", None); d["mercado"][0].pop("nota", None)
    # lo que cargó la persona
    d["tasks"].append({"id": 70, "txt": "Tarea del productor", "due": "2026-11-20"})      # sin cid, resp ni done
    d["lotes"][0]["nombre"] = "Mi lote editado"
    d["ins"][0]["mkt"] = False; d["ins"][0]["precio"] = 555
    d["clients"].append({"id": 9, "nombre": "Otro campo", "etapa": "Prospecto"})            # registro mínimo
    d["real"] = {"1": {"9": 0.77}}
    return d


def revisar(pag, camino):
    """Todo lo cargado sigue ahí, todo lo nuevo se completó, y ninguna pantalla se rompe."""
    est = pag.evaluate("() => ({tarea: S.tasks.some(t => t.txt === 'Tarea del productor'), lote: lo(1).nombre, precio: S.ins[0].precio, otro: S.clients.some(c => c.nombre === 'Otro campo'),"
                       " gdpv: (S.real['1']||{})[9], cal: !!(S.cal && S.cal.pasto), curva: Array.isArray(S.curva) && S.curva.length > 0, comp: !!(S.comp && S.comp.A), esquema: S.esquema, desv: S.cfg.desv,"
                       " hist: Array.isArray(S.clients[0].hist), notas: Array.isArray(S.clients[0].notas), real: lo(1).real === null, gmin: typeof S.bib[0].gmin, perfil: Array.isArray(S.rec[0].perfil),"
                       " soja: typeof S.mercado[0].soja, minimo: Array.isArray(S.clients[1] && S.clients[1].hist) || Array.isArray(S.clients.find(c => c.nombre === 'Otro campo').hist),"
                       " tareaResp: S.tasks.find(t => t.txt === 'Tarea del productor').resp, tareaDone: S.tasks.find(t => t.txt === 'Tarea del productor').done})")
    comprobar(est["tarea"], f"[{camino}] Se perdió la tarea que cargó la persona")
    comprobar(est["lote"] == "Mi lote editado", f"[{camino}] Se perdió el nombre editado del lote ({est['lote']!r})")
    comprobar(est["precio"] == 555, f"[{camino}] Se perdió el precio cargado del maíz ({est['precio']!r})")
    comprobar(est["otro"], f"[{camino}] Se perdió el campo que cargó la persona")
    comprobar(est["gdpv"] == 0.77, f"[{camino}] Se perdió el GDPV medido ({est['gdpv']!r})")
    for k in ("cal", "curva", "comp", "hist", "notas", "real", "perfil", "minimo"):
        comprobar(est[k], f"[{camino}] No se completó «{k}»")
    comprobar(est["esquema"] == 1, f"[{camino}] No quedó marcado el esquema ({est['esquema']!r})")
    comprobar(est["desv"] == 0.15, f"[{camino}] No se completó el umbral nuevo ({est['desv']!r})")
    comprobar(est["gmin"] == "number" and est["soja"] == "number", f"[{camino}] Faltan campos nuevos de la biblioteca o del mercado")
    comprobar(est["tareaDone"] is False and est["tareaResp"], f"[{camino}] La tarea incompleta no se completó ({est['tareaDone']!r}, {est['tareaResp']!r})")
    con_sesion = pag.evaluate("() => SYNC.on")
    cierra = base.CIERRA.replace("SYNC.on=false;", "") if con_sesion else base.CIERRA
    for nombre, preparar in base.PANTALLAS:
        if con_sesion and "SYNC.on=true" in preparar + " ".join([base.CON_CUENTA] if "CON_CUENTA" in preparar else []):
            continue            # esa pantalla simula una sesión propia; con una sesión de verdad no hace falta
        if con_sesion and nombre.startswith("Formulario · mi cuenta y datos"):
            continue
        pag.evaluate("() => {" + cierra + "}")
        pag.evaluate("() => {" + preparar + "}")
        pag.wait_for_timeout(120)
        texto = pag.inner_text("body")
        for malo in ("NaN", "undefined", "Infinity", "null"):
            if malo in texto:
                comprobar(False, f"[{camino}] En «{nombre}» aparece «{malo}»")
        comprobar(True, "")
    pag.evaluate("() => {" + cierra + "}")


def main():
    with sync_playwright() as p:
        nav = p.chromium.launch()

        # Datos de ejemplo actuales -> datos «viejos»
        c0 = nav.new_context(); c0.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
        p0 = c0.new_page(); p0.goto(URL)
        actual = p0.evaluate("() => JSON.parse(JSON.stringify(S))"); c0.close()
        viejo = datos_viejos(actual)
        viejo_txt = json.dumps(viejo)

        # 1) Guardados en el aparato
        errores = []
        ctx = nav.new_context(viewport={"width": 1280, "height": 800})
        ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
        ctx.add_init_script("localStorage.setItem('rumbo_v3', " + json.dumps(viejo_txt) + ");")
        pag = ctx.new_page(); pag.on("pageerror", lambda e: errores.append(str(e)))
        pag.goto(URL); pag.evaluate("() => document.getElementById('login').style.display='none'")
        revisar(pag, "aparato")
        comprobar(not errores, f"[aparato] Errores en la página: {errores[:2]}")
        ctx.close()

        # 5) Datos dañados
        for nombre, valor in (("texto que no es JSON", "esto no es json {"), ("JSON de otra cosa", '{"hola": 1}'), ("lista vacía", "[]")):
            errores = []
            ctx = nav.new_context(); ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
            ctx.add_init_script("localStorage.setItem('rumbo_v3', " + json.dumps(valor) + ");")
            pag = ctx.new_page(); pag.on("pageerror", lambda e: errores.append(str(e)))
            pag.goto(URL); pag.wait_for_timeout(300)
            comprobar(not errores and pag.evaluate("() => S.lotes.length") == 6, f"[dañado: {nombre}] La app no arrancó con los datos de ejemplo ({errores[:1]})")
            ctx.close()

        # 2) Traídos del servidor, 3) restaurados de una copia, 4) cargados desde un archivo
        srv = sy.Servidor()
        srv.estado["u1"] = {"data": json.loads(viejo_txt), "updated_at": "2026-10-30T10:00:00.000+00:00"}
        ctx = nav.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True)
        ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
        ctx.expose_function("__srv", srv.atender); ctx.on("dialog", lambda d: d.accept())
        errores = []
        celu = ctx.new_page()
        celu.add_init_script("window.__uid='u1';window.__email='p@correo.com';" + sy.FALSO_SUPABASE)
        celu.on("pageerror", lambda e: errores.append(str(e)))
        celu.goto(URL); celu.wait_for_function("() => typeof SYNC !== 'undefined' && SYNC.on && SYNC.lastIso", timeout=8000)
        revisar(celu, "servidor")
        # tras abrir y mirar todo, no se escribió nada en el servidor por el solo hecho de completar
        comprobar(srv.estado["u1"]["updated_at"] == "2026-10-30T10:00:00.000+00:00", "[servidor] Completar datos viejos modificó el servidor sin que la persona cambiara nada")

        srv.copias.append({"id": 500, "user_id": "u1", "motivo": "vieja", "data": json.loads(viejo_txt), "created_at": srv.ahora()})
        celu.evaluate("() => {S.tasks = []; S.clients = S.clients.slice(0,1); save()}"); celu.wait_for_timeout(1700)
        celu.evaluate("() => restaurarCopia(500)"); celu.wait_for_timeout(1800)
        revisar(celu, "copia del servidor")

        archivo = pathlib.Path(tempfile.mkdtemp()) / "vieja.json"
        archivo.write_text(json.dumps({"app": "rumbo", "version": "vieja", "datos": viejo}))
        celu.evaluate("() => {S.tasks = []; S.clients = S.clients.slice(0,1); save()}"); celu.wait_for_timeout(1700)
        celu.evaluate("() => cuentaDialogo()"); celu.wait_for_timeout(300)
        celu.set_input_files("#fileCopia", str(archivo)); celu.wait_for_timeout(1800)
        revisar(celu, "archivo")
        comprobar(not errores, f"[servidor/copia/archivo] Errores en la página: {errores[:2]}")
        ctx.close()

        # 6) Migraciones: un cambio que no es «agregar» (acá: tel -> telefono) con ESQUEMA 2.
        #    Quien renombra un campo también actualiza REG_DEFECTO, igual que hace esta prueba.
        mod = pathlib.Path(tempfile.mkdtemp()) / "index.html"
        html = (pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else RAIZ / "index.html").read_text(encoding="utf-8")
        html = html.replace("const ESQUEMA=1;", "const ESQUEMA=2;").replace("email:'',tel:'',hist:[],notas:[]}", "email:'',telefono:'',hist:[],notas:[]}").replace("const MIGRACIONES={};", "const MIGRACIONES={2:d=>{d.clients.forEach(c=>{c.telefono=c.tel;delete c.tel});return d}};")
        comprobar("const ESQUEMA=2;" in html and "MIGRACIONES={2:" in html, "No pude preparar la prueba de migraciones (no encontré ESQUEMA o MIGRACIONES)")
        mod.write_text(html, encoding="utf-8")
        for esq, esperado in ((1, "351 555-0141"), (2, None)):
            d = json.loads(viejo_txt); d["esquema"] = esq; d["clients"][0]["tel"] = "351 555-0141"
            if esq == 2:
                d["clients"][0]["telefono"] = "ya convertido"; d["clients"][0].pop("tel")
            ctx = nav.new_context(); ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
            ctx.add_init_script("localStorage.setItem('rumbo_v3', " + json.dumps(json.dumps(d)) + ");")
            pag = ctx.new_page(); pag.goto(mod.as_uri()); pag.wait_for_timeout(300)
            r = pag.evaluate("() => ({tel: S.clients[0].tel, telefono: S.clients[0].telefono, esquema: S.esquema})")
            if esq == 1:
                comprobar(r["telefono"] == esperado and r["tel"] is None and r["esquema"] == 2, f"La migración 1 -> 2 no convirtió el dato: {r}")
            else:
                comprobar(r["telefono"] == "ya convertido" and r["esquema"] == 2, f"La migración se volvió a aplicar a datos que ya estaban convertidos: {r}")
            ctx.close()
        nav.close()

    print(f"{comprobaciones} comprobaciones.")
    if fallas:
        print(f"FALLAS: {len(fallas)}")
        for f in dict.fromkeys(fallas):
            print("  -", f)
        sys.exit(1)
    print("LOS DATOS VIEJOS SIGUEN FUNCIONANDO.")


if __name__ == "__main__":
    main()
