"""Prueba del formato de fechas: todas las fechas se muestran y se escriben como aaaa/mm/dd.

1. Recorre todas las pantallas, paneles y formularios y busca fechas escritas de otra forma
   (2026-10-30, 30/10/2026, «Oct 26»).
2. Escribe una fecha en un formulario TECLEANDO carácter por carácter y comprueba que se guarda
   la fecha exacta (resultado === esperado); una fecha con otro formato debe ser rechazada.

Uso:   python3 tests/fechas_test.py [ruta/a/index.html]
Salida: 0 = todo bien, 1 = hay fallas.
"""
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pantallas_cuadran_test as base  # noqa: E402

URL = pathlib.Path(sys.argv[1]).resolve().as_uri() if len(sys.argv) > 1 else base.URL
PROHIBIDO = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "fecha con guiones (aaaa-mm-dd)"),
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"), "fecha dd/mm/aaaa"),
    (re.compile(r"\b(Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic) \d{2}\b"), "mes escrito como «Oct 26»"),
]
SEMBRAR = """() => {
  document.getElementById('login').style.display = 'none';
  S.clients[0].notas.push({d: '2026-10-29', a: 'Yo', t: 'Nota de prueba'});
  S.clients[0].hist.push({d: '2026-10-30', t: 'Contacto registrado'});
  log('Movimiento de prueba');
}"""


def main():
    fallas, revisadas = [], 0
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={"width": 1366, "height": 768})
        ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
        pag = ctx.new_page()
        pag.goto(URL)
        pag.evaluate(SEMBRAR)

        # 1) Barrido de todas las pantallas
        for nombre, preparar in base.PANTALLAS:
            pag.evaluate("() => {" + base.CIERRA + "}")
            pag.evaluate("() => {" + preparar + "}")
            pag.wait_for_timeout(550 if nombre.startswith(("Panel", "Chat")) else 150)
            texto = pag.evaluate("""() => {
              const raiz = document.querySelector('dialog[open]') || document.body;
              const campos = [...raiz.querySelectorAll('input,textarea')].map(i => i.value + ' ' + (i.placeholder || '')).join(' | ');
              return raiz.innerText + ' | ' + campos;
            }""")
            revisadas += 1
            for patron, que in PROHIBIDO:
                for m in sorted(set(patron.findall(texto)) if patron.groups == 0 else {x.group(0) for x in patron.finditer(texto)}):
                    fallas.append(f"{nombre}: {que}: «{m}»")

        # 2) Las fechas buenas tienen que verse donde corresponde
        pag.evaluate("() => {" + base.CIERRA + "}")
        pag.evaluate("() => {UI.view='gente';render();openDrawer('c',1)}")
        pag.wait_for_timeout(550)
        ficha = pag.inner_text("#dr")
        for esperado in ("2026/10/29", "2026/10/30"):
            if esperado not in ficha:
                fallas.append(f"Ficha del productor: no aparece la fecha «{esperado}»")
        pag.evaluate("() => {" + base.CIERRA + "}")

        try:
          # 3) Tecleo real en el formulario de tarea
          pag.evaluate("() => {UI.view='hoy';render();newTask()}")
          pag.fill("dialog input[name=txt]", "Tarea con fecha")
          campo = pag.locator("dialog input[name=due]")
          campo.fill("")
          esperado_valor = ""
          for ch in "2026/11/05":                       # carácter por carácter, como una persona
              campo.press_sequentially(ch)
              esperado_valor += ch
              if campo.input_value() != esperado_valor:
                  fallas.append(f"Tecleo: tras «{esperado_valor}» el campo muestra «{campo.input_value()}»")
          if not pag.evaluate("() => document.querySelector('dialog form').checkValidity()"):
              fallas.append("Una fecha válida (2026/11/05) fue rechazada por el formulario")
          pag.click("dialog button.pri")
          due = pag.evaluate("() => S.tasks.filter(t => t.txt === 'Tarea con fecha').map(t => t.due)")
          if due != ["2026-11-05"]:
              fallas.append(f"La fecha tecleada 2026/11/05 se guardó como {due}, se esperaba ['2026-11-05']")

          # 4) Un formato distinto se rechaza
          pag.evaluate("() => {UI.view='hoy';render();newTask()}")
          pag.fill("dialog input[name=txt]", "Otra")
          for malo in ("05/11/2026", "2026-11-05", "2026/13/01", "2026/11/32", "mañana"):
              pag.fill("dialog input[name=due]", malo)
              if pag.evaluate("() => document.querySelector('dialog form').checkValidity()"):
                  fallas.append(f"El formulario aceptó una fecha mal escrita: «{malo}»")

          # 5) Meses del formulario de precios: aaaa/mm
          pag.evaluate("() => {document.getElementById('dlg').close();UI.view='mercado';render();newPrecio()}")
          for bueno, ok in (("2026/11", True), ("2026-11", False), ("11/2026", False)):
              pag.fill("dialog input[name=f]", bueno)
              if pag.evaluate("() => document.querySelector('dialog form').checkValidity()") != ok:
                  fallas.append(f"Mes «{bueno}»: se esperaba {'aceptar' if ok else 'rechazar'}")
        except Exception as e:  # el formulario no admite escribir la fecha como aaaa/mm/dd
            fallas.append('Los formularios de fecha no aceptan escribir aaaa/mm/dd (' + str(e).splitlines()[0][:70] + ')')
        ctx.close()
        nav.close()

    print(f"{revisadas} pantallas revisadas + pruebas de tecleo y validación.")
    if fallas:
        print(f"FALLAS: {len(fallas)}")
        for f in dict.fromkeys(fallas):
            print("  -", f)
        sys.exit(1)
    print("TODAS LAS FECHAS EN aaaa/mm/dd.")


if __name__ == "__main__":
    main()
