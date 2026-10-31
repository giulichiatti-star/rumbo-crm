"""Prueba de sincronización, copias de seguridad y comentarios.

No usa Supabase de verdad: pone en su lugar un «servidor de mentira» en memoria que se comporta igual
en lo que la app necesita (una fila de datos por cuenta, copias, comentarios, y la regla «solo se
guarda si el servidor sigue como lo dejamos»). Dos pestañas hacen de «celular» y «computadora» y
comparten ese servidor. Se prueba:
  1. Dos aparatos: lo que carga uno aparece en el otro, sin pisar nada.
  2. Choque (los dos cambian a la vez): se pregunta, y elija lo que elija NO se pierde nada (queda como copia).
  3. Copia diaria (una por día), poda a las últimas 14, y restaurar una copia.
  4. Descargar una copia y volver a cargarla; un archivo que no es de Rumbo se rechaza.
  5. Comentarios: llegan con pantalla, versión y ancho de pantalla.
  6. Sin conexión: no se pierde lo cargado y se reintenta.
Uso: python3 tests/sync_test.py [ruta/a/index.html]
"""
import json
import pathlib
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = pathlib.Path(sys.argv[1]).resolve().as_uri() if len(sys.argv) > 1 else (RAIZ / "index.html").as_uri()
fallas, comprobaciones = [], 0


def comprobar(ok, texto):
    global comprobaciones
    comprobaciones += 1
    if not ok:
        fallas.append(texto)


# ---------------- servidor de mentira ----------------
class Servidor:
    def __init__(self):
        self.estado = {}        # user_id -> {"data":..., "updated_at":...}
        self.copias = []        # {"id","user_id","motivo","data","created_at"}
        self.comentarios = []
        self.sig = 1
        self.sin_conexion = False
        self.reloj = time.time()

    def ahora(self):
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.reloj)) + ".000+00:00"

    def atender(self, texto):
        q = json.loads(texto)
        if self.sin_conexion:
            return json.dumps({"data": None, "error": {"message": "Failed to fetch"}})
        t, act, uid = q["t"], q["act"], q["uid"]
        filtros = {(f[1]): f[2] for f in q["f"] if f[0] == "eq"}
        en = {(f[1]): f[2] for f in q["f"] if f[0] == "in"}
        if t == "rumbo_state":
            fila = self.estado.get(uid)
            if act == "select":
                return json.dumps({"data": fila, "error": None})
            if act == "insert":
                if fila:
                    return json.dumps({"data": None, "error": {"code": "23505", "message": "duplicate key value"}})
                self.estado[uid] = {"data": q["pl"]["data"], "updated_at": q["pl"]["updated_at"]}
                return json.dumps({"data": [{"updated_at": q["pl"]["updated_at"]}], "error": None})
            if act == "update":
                if not fila or fila["updated_at"] != filtros.get("updated_at"):
                    return json.dumps({"data": [], "error": None})
                self.estado[uid] = {"data": q["pl"]["data"], "updated_at": q["pl"]["updated_at"]}
                return json.dumps({"data": [{"updated_at": q["pl"]["updated_at"]}], "error": None})
        if t == "rumbo_backups":
            mias = [c for c in self.copias if c["user_id"] == uid]
            if act == "insert":
                self.reloj += 1
                self.copias.append({"id": self.sig, "user_id": uid, "motivo": q["pl"].get("motivo"), "data": q["pl"]["data"], "created_at": self.ahora()})
                self.sig += 1
                return json.dumps({"data": None, "error": None})
            if act == "select":
                mias = sorted(mias, key=lambda c: (c["created_at"], c["id"]), reverse=True)
                if "id" in filtros:
                    mias = [c for c in mias if c["id"] == filtros["id"]]
                if q["rg"]:
                    mias = mias[q["rg"][0]:q["rg"][1] + 1]
                if q["lim"]:
                    mias = mias[:q["lim"]]
                if q["single"]:
                    return json.dumps({"data": mias[0] if mias else None, "error": None})
                return json.dumps({"data": [{k: c[k] for k in ("id", "created_at", "motivo")} for c in mias], "error": None})
            if act == "delete":
                ids = set(en.get("id", []))
                self.copias = [c for c in self.copias if not (c["user_id"] == uid and c["id"] in ids)]
                return json.dumps({"data": None, "error": None})
        if t == "rumbo_feedback" and act == "insert":
            self.comentarios.append(q["pl"])
            return json.dumps({"data": None, "error": None})
        return json.dumps({"data": None, "error": {"message": f"no soportado: {t} {act}"}})


FALSO_SUPABASE = """
window.supabase = {createClient: () => {
  class Q { constructor(t){this.t=t;this.f=[];this.o=null;this.lim=null;this.rg=null;this.act='select';this.pl=null;this.sel=false;this.single=false}
    select(){this.sel=true;return this} eq(k,v){this.f.push(['eq',k,v]);return this} in(k,v){this.f.push(['in',k,v]);return this}
    order(k,o){this.o=[k,o&&o.ascending===false?'desc':'asc'];return this} limit(n){this.lim=n;return this} range(a,b){this.rg=[a,b];return this}
    maybeSingle(){this.single=true;return this} update(p){this.act='update';this.pl=p;return this} insert(p){this.act='insert';this.pl=p;return this} delete(){this.act='delete';return this}
    then(res, rej){ return window.__srv(JSON.stringify({t:this.t,act:this.act,f:this.f,o:this.o,lim:this.lim,rg:this.rg,pl:this.pl,sel:this.sel,single:this.single,uid:window.__uid})).then(r=>JSON.parse(r)).then(res, rej) } }
  const sesion = () => ({user:{id: window.__uid, email: window.__email}});
  return { from: t => new Q(t),
    auth: { getSession: async () => ({data:{session: window.__uid ? sesion() : null}}), signOut: async () => ({}),
            signInWithPassword: async () => ({data:{session: sesion()}, error:null}), signUp: async () => ({data:{session: sesion()}, error:null}) } };
}};
"""


def abrir(ctx, uid="u1", email="productor@correo.com"):
    pag = ctx.new_page()
    pag.add_init_script(f"window.__uid='{uid}';window.__email='{email}';" + FALSO_SUPABASE)
    pag.goto(URL)
    pag.wait_for_function("() => typeof SYNC !== 'undefined' && SYNC.on && SYNC.lastIso", timeout=8000)
    return pag


def tareas(pag):
    return pag.evaluate("() => S.tasks.map(t => t.txt)")


def main():
    srv = Servidor()
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True)
        ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
        ctx.expose_function("__srv", srv.atender)
        ctx.on("dialog", lambda d: d.accept())            # los «¿seguro?» del navegador se aceptan

        # 1) Dos aparatos
        celu = abrir(ctx)
        comprobar("u1" in srv.estado, "Al entrar por primera vez no se guardaron los datos en el servidor")
        comprobar(len(srv.estado["u1"]["data"]["lotes"]) == 6, "El servidor no recibió los 6 lotes del modelo")
        compu = abrir(ctx)
        comprobar(compu.evaluate("() => S.lotes.length") == 6, "El segundo aparato no recibió los datos")
        celu.evaluate("() => {S.tasks.push({id: 501, txt: 'Desde el celular', cid: 1, due: iso(2), done: false, resp: 'Yo'}); save()}")
        celu.wait_for_timeout(1700)
        comprobar("Desde el celular" in [t["txt"] for t in srv.estado["u1"]["data"]["tasks"]], "Lo cargado en el celular no llegó al servidor")
        compu.evaluate("() => pull(false)"); compu.wait_for_timeout(400)
        comprobar("Desde el celular" in tareas(compu), "Lo cargado en el celular no apareció en la computadora")
        comprobar(celu.evaluate("() => SYNC.conflicto") is False and compu.evaluate("() => SYNC.conflicto") is False, "Se detectó un choque donde no lo había")
        comprobar(compu.inner_text("#sync") == "Sincronizado", f"El estado no dice «Sincronizado»: «{compu.inner_text('#sync')}»")

        # 2) Choque: los dos cambian antes de sincronizar. Gana lo que elija la persona y lo otro queda como copia.
        for eleccion in ("cQuedar", "cTraer"):
            celu.evaluate("() => pull(false)"); compu.evaluate("() => pull(false)"); compu.wait_for_timeout(400)
            nombre_a, nombre_b = f"A-{eleccion}", f"B-{eleccion}"
            celu.evaluate("(n) => {S.tasks.push({id: Date.now(), txt: n, cid: 1, due: iso(2), done: false, resp: 'Yo'}); save()}", nombre_a)
            celu.wait_for_timeout(1700)                       # el celular guarda primero
            compu.evaluate("(n) => {S.tasks.push({id: Date.now() + 1, txt: n, cid: 1, due: iso(2), done: false, resp: 'Yo'}); save()}", nombre_b)
            compu.wait_for_timeout(1700)                      # la computadora intenta guardar con datos viejos
            comprobar(compu.evaluate("() => document.getElementById('dlg').open"), f"[{eleccion}] No apareció la pregunta del choque")
            en_servidor = [t["txt"] for t in srv.estado["u1"]["data"]["tasks"]]
            comprobar(nombre_a in en_servidor and nombre_b not in en_servidor, f"[{eleccion}] La computadora pisó lo del celular sin preguntar")
            if eleccion == "cQuedar":
                compu.click("#cQuedar"); compu.wait_for_timeout(1500)
                en_servidor = [t["txt"] for t in srv.estado["u1"]["data"]["tasks"]]
                comprobar(nombre_b in en_servidor and nombre_a not in en_servidor, "Conservar lo de este aparato no dejó lo de este aparato en el servidor")
                guardada = [c for c in srv.copias if c["motivo"] == "choque: lo del otro aparato"]
                comprobar(bool(guardada) and nombre_a in [t["txt"] for t in guardada[-1]["data"]["tasks"]], "Lo del otro aparato no quedó guardado como copia")
            else:
                compu.click("#cTraer"); compu.wait_for_timeout(600)
                comprobar(nombre_a in tareas(compu) and nombre_b not in tareas(compu), "Traer lo del otro aparato no dejó lo del otro aparato")
                guardada = [c for c in srv.copias if c["motivo"] == "choque: lo de este aparato"]
                comprobar(bool(guardada) and nombre_b in [t["txt"] for t in guardada[-1]["data"]["tasks"]], "Lo de este aparato no quedó guardado como copia")
            comprobar(compu.evaluate("() => SYNC.conflicto") is False, f"[{eleccion}] El choque quedó trabado")
        compu.close()

        # 3) Copia diaria, poda y restauración
        srv.copias.clear()
        celu.evaluate("() => copiaDiaria()"); celu.wait_for_timeout(500)
        comprobar(len([c for c in srv.copias if c["motivo"] == "diaria"]) == 1, "No se guardó la copia diaria")
        celu.evaluate("() => copiaDiaria()"); celu.wait_for_timeout(500)
        comprobar(len([c for c in srv.copias if c["motivo"] == "diaria"]) == 1, "Se guardó más de una copia el mismo día")
        for c in srv.copias:                                 # «pasó un día»: las copias existentes ahora tienen 25 horas
            c["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(srv.reloj - 25 * 3600)) + ".000+00:00"
        celu.evaluate("() => copiaDiaria()"); celu.wait_for_timeout(500)
        comprobar(len([c for c in srv.copias if c["motivo"] == "diaria"]) == 2, "No se guardó la copia del día siguiente")
        for i in range(20):
            celu.evaluate("() => guardarCopia('manual', S)")
        celu.wait_for_timeout(500)
        celu.evaluate("() => podarCopias()"); celu.wait_for_timeout(600)
        comprobar(len(srv.copias) == 14, f"La poda dejó {len(srv.copias)} copias y se esperaban 14")

        celu.evaluate("() => {S.tasks.push({id: 777, txt: 'Tarea para perder', cid: 1, due: iso(2), done: false, resp: 'Yo'}); save()}")
        celu.wait_for_timeout(1700)
        antes = srv.copias[-1]
        con_tarea = {"motivo": "con la tarea", "data": json.loads(json.dumps(srv.estado["u1"]["data"]))}
        sin_tarea = json.loads(json.dumps(srv.estado["u1"]["data"])); sin_tarea["tasks"] = [t for t in sin_tarea["tasks"] if t["txt"] != "Tarea para perder"]
        srv.copias.append({"id": 9999, "user_id": "u1", "motivo": "sin la tarea", "data": sin_tarea, "created_at": srv.ahora()})
        celu.evaluate("() => cuentaDialogo()"); celu.wait_for_timeout(600)
        comprobar(celu.locator("#cLista li").count() >= 2, "La lista de copias del servidor está vacía")
        celu.click("#cLista li:has-text('sin la tarea') button"); celu.wait_for_timeout(1800)
        comprobar("Tarea para perder" not in tareas(celu), "Restaurar la copia no devolvió los datos de esa copia")
        comprobar(any(c["motivo"] == "antes de restaurar" and "Tarea para perder" in [t["txt"] for t in c["data"]["tasks"]] for c in srv.copias), "Antes de restaurar no se guardó lo que había")
        comprobar("Tarea para perder" not in [t["txt"] for t in srv.estado["u1"]["data"]["tasks"]], "Lo restaurado no se sincronizó con el servidor")

        # 4) Descargar y volver a cargar
        celu.evaluate("() => {S.tasks.push({id: 888, txt: 'Tarea del archivo', cid: 1, due: iso(2), done: false, resp: 'Yo'}); save()}")
        celu.wait_for_timeout(1700)
        celu.evaluate("() => cuentaDialogo()"); celu.wait_for_timeout(300)
        with celu.expect_download() as d:
            celu.click("#cDesc")
        ruta = pathlib.Path(tempfile.mkdtemp()) / d.value.suggested_filename
        d.value.save_as(ruta)
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
        comprobar(contenido.get("app") == "rumbo" and len(contenido["datos"]["lotes"]) == 6, "El archivo descargado no tiene el formato esperado")
        comprobar("Tarea del archivo" in [t["txt"] for t in contenido["datos"]["tasks"]], "El archivo descargado no incluye lo último que se cargó")
        comprobar(d.value.suggested_filename.startswith("rumbo-copia-") and d.value.suggested_filename.endswith(".json"), f"Nombre de archivo inesperado: {d.value.suggested_filename}")
        celu.evaluate("() => {S.tasks = S.tasks.filter(t => t.txt !== 'Tarea del archivo'); save()}"); celu.wait_for_timeout(1700)
        comprobar("Tarea del archivo" not in tareas(celu), "No se pudo preparar la prueba de carga de archivo")
        celu.evaluate("() => cuentaDialogo()"); celu.wait_for_timeout(300)
        celu.set_input_files("#fileCopia", str(ruta)); celu.wait_for_timeout(1800)
        comprobar("Tarea del archivo" in tareas(celu), "Cargar la copia desde el archivo no devolvió los datos")
        malo = pathlib.Path(tempfile.mkdtemp()) / "otro.json"
        malo.write_text(json.dumps({"hola": "mundo"}))
        antes_n = len(tareas(celu))
        celu.set_input_files("#fileCopia", str(malo)); celu.wait_for_timeout(600)
        comprobar(len(tareas(celu)) == antes_n, "Un archivo que no es de Rumbo cambió los datos")
        comprobar("no es una copia de Rumbo" in celu.inner_text("#toasts"), "Un archivo que no es de Rumbo no fue rechazado con un aviso")

        # 5) Comentarios
        celu.evaluate("() => {UI.view='costos';UI.ctab='dietas';render();comentarDialogo()}")
        celu.select_option("dialog select[name=tipo]", "Algo no funciona")
        celu.fill("dialog textarea[name=texto]", "No me deja guardar el precio del maíz")
        celu.click("dialog button.pri"); celu.wait_for_timeout(600)
        c = srv.comentarios[-1] if srv.comentarios else {}
        comprobar(c.get("texto") == "No me deja guardar el precio del maíz", "El comentario no llegó")
        comprobar(c.get("tipo") == "Algo no funciona" and c.get("pantalla") == "costos/dietas", f"Faltan tipo o pantalla en el comentario: {c.get('tipo')!r}, {c.get('pantalla')!r}")
        comprobar(c.get("email") == "productor@correo.com" and c.get("user_id") == "u1" and c.get("ancho") == 1280 and c.get("version"), "Faltan datos de soporte (correo, usuario, ancho o versión) en el comentario")

        # 6) Sin conexión: no se pierde nada y se reintenta
        srv.sin_conexion = True
        celu.evaluate("() => {S.tasks.push({id: 999, txt: 'Cargada sin internet', cid: 1, due: iso(2), done: false, resp: 'Yo'}); save()}")
        celu.wait_for_timeout(1900)
        comprobar("Sin conexión" in celu.inner_text("#sync"), f"No avisa que no hay conexión: «{celu.inner_text('#sync')}»")
        comprobar("Cargada sin internet" in tareas(celu), "Se perdió lo cargado sin conexión")
        comprobar("Cargada sin internet" in (celu.evaluate("() => localStorage.getItem('rumbo_v3')") or ""), "Lo cargado sin conexión no quedó guardado en el aparato")
        srv.sin_conexion = False
        celu.evaluate("() => pushNow()"); celu.wait_for_timeout(900)
        comprobar("Cargada sin internet" in [t["txt"] for t in srv.estado["u1"]["data"]["tasks"]], "Al volver la conexión no se guardó lo pendiente")
        nav.close()

    print(f"{comprobaciones} comprobaciones.")
    if fallas:
        print(f"FALLAS: {len(fallas)}")
        for f in fallas:
            print("  -", f)
        sys.exit(1)
    print("SINCRONIZACIÓN, COPIAS Y COMENTARIOS FUNCIONAN.")


if __name__ == "__main__":
    main()
