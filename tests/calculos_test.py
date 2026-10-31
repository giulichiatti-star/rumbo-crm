"""Prueba de cálculos (estándar de pruebas de Walter).

Reglas que cumple:
  - Los valores esperados se calcularon A MANO antes (salen de tu Excel o de cuentas hechas aparte)
    y se comparan explícitamente: resultado == esperado, con una tolerancia dicha en cada caso.
  - Lo que se escribe, se escribe TECLEANDO carácter por carácter (nunca fijando el valor final).
  - Casos límite a propósito: cruce de separador de miles, decimales, cero, vacío y negativos.
  - Nunca debe aparecer «NaN» ni «Infinity» en pantalla.

Uso:   python3 tests/calculos_test.py [ruta/a/index.html]
Salida: 0 = todo bien, 1 = hay fallas.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = pathlib.Path(sys.argv[1]).resolve().as_uri() if len(sys.argv) > 1 else (RAIZ / "index.html").as_uri()
OCULTAR_LOGIN = "() => { const L = document.getElementById('login'); if (L) L.style.display = 'none'; }"

# (descripción, expresión JavaScript, valor esperado, tolerancia). Valores de las hojas del Excel.
DEL_EXCEL = [
    # Costo_Forraje
    ("Alfalfa: costo anual USD/ha", "recCalc(S.rec[0]).usd", 357.5, 1e-9),
    ("Alfalfa: costo anual $/ha (dólar 1517)", "recCalc(S.rec[0]).pesos", 542327.5, 0.1),
    ("Alfalfa: materia seca utilizada", "recCalc(S.rec[0]).ms", 5850, 1e-9),
    ("Alfalfa: $/kg MS", "recCalc(S.rec[0]).kg", 92.7055556, 1e-6),
    ("Verdeo: costo anual USD/ha", "recCalc(S.rec[1]).usd", 135, 1e-9),
    ("Verdeo: materia seca utilizada", "recCalc(S.rec[1]).ms", 2800, 1e-9),
    ("Verdeo: $/kg MS", "recCalc(S.rec[1]).kg", 73.1410714, 1e-6),
    ("Silaje: costo anual USD/ha", "recCalc(S.rec[2]).usd", 932, 1e-9),
    ("Silaje: costo anual $/ha", "recCalc(S.rec[2]).pesos", 1413844, 0.1),
    ("Silaje: materia seca utilizada (con 10 % de pérdidas)", "recCalc(S.rec[2]).ms", 9000, 1e-9),
    ("Silaje: $/kg MS", "recCalc(S.rec[2]).kg", 157.0937778, 1e-6),
    # Dietas
    ("Maíz: $/kg MS", "insMS(S.ins[0])", 329.885057, 1e-6),
    ("Concentrado: $/kg MS", "insMS(S.ins[1])", 1107.931034, 1e-6),
    ("Heno: $/kg MS", "insMS(S.ins[2])", 136.363636, 1e-6),
    ("Silaje de maíz (insumo): $/kg MS", "insMS(S.ins[3])", 66.666667, 1e-6),
    ("Ración Adaptación: $/kg MS", "racCalc(S.rac[0]).cost", 349.633229, 1e-6),
    ("Ración Terminación: $/kg MS", "racCalc(S.rac[1]).cost", 399.909195, 1e-6),
    ("Ración Recría invernal: $/kg MS", "racCalc(S.rac[2]).cost", 158.212644, 1e-6),
    ("Ración Adaptación: proteína", "racCalc(S.rac[0]).pb", 0.12, 1e-9),
    ("Ración Terminación: proteína", "racCalc(S.rac[1]).pb", 0.1052, 1e-9),
    ("Ración Adaptación: energía", "racCalc(S.rac[0]).em", 2.72, 1e-9),
    ("Ración Terminación: energía", "racCalc(S.rac[1]).em", 3.092, 1e-9),
    ("Ración Adaptación: suma de porcentajes", "racCalc(S.rac[0]).sum", 1, 1e-9),
    # Biblioteca: costo efectivo = costo / (1 - merma)
    ("Costo efectivo Adaptación", "bibEf(S.bib[4])", 356.7686009, 1e-6),
    ("Costo efectivo Terminación", "bibEf(S.bib[5])", 408.0706074, 1e-6),
    ("Costo efectivo Recría invernal", "bibEf(S.bib[3])", 161.4414731, 1e-6),
    ("Costo efectivo Alfalfa (sin merma)", "bibEf(S.bib[0])", 92.7055556, 1e-6),
    # Mercado (octubre 2026)
    ("Invernada / gordo", "derived(lastMk()).ratio", 1.4588235, 1e-6),
    ("Kg de maíz por kg de gordo", "derived(lastMk()).kgMaiz", 14.8083624, 1e-6),
    ("Kg de soja por kg de gordo", "derived(lastMk()).kgSoja", 7.5892857, 1e-6),
    ("Litros de gasoil por kg de gordo", "derived(lastMk()).lGas", 1.8478261, 1e-6),
    ("Gordo en dólares por kg", "derived(lastMk()).usd", 2.8015821, 1e-6),
    # Margen de cada lote = ingreso neto − compra − desembolsos − interés (hoja Resultados)
    ("Lote 1: margen después de financiar", "lo(1).ingN-lo(1).compra-lo(1).desemb-lo(1).interes", 88457.94, 5),
    ("Lote 2: margen después de financiar", "lo(2).ingN-lo(2).compra-lo(2).desemb-lo(2).interes", -21678.63, 5),
    ("Lote 3: margen después de financiar", "lo(3).ingN-lo(3).compra-lo(3).desemb-lo(3).interes", -21001.80, 5),
    ("Lote 4: margen después de financiar", "lo(4).ingN-lo(4).compra-lo(4).desemb-lo(4).interes", -102550.01, 5),
    ("Lote 5: margen después de financiar", "lo(5).ingN-lo(5).compra-lo(5).desemb-lo(5).interes", -83445.05, 5),
    ("Lote 6: margen después de financiar", "lo(6).ingN-lo(6).compra-lo(6).desemb-lo(6).interes", -12402.87, 5),
    ("Lote 1: margen antes de financiar", "mAntes(lo(1))", 213167.54, 5),
    ("Lote 1: colchón de precio", "colchon(lo(1))", 0.0516421, 1e-4),
    # Sensibilidad del lote 1 (hoja Sensibilidad): diferencia contra la base, en $/cabeza
    ("Sensibilidad: GDPV −0,2", "simAt(lo(1),-0.2,0)", -137562, 60),
    ("Sensibilidad: GDPV −0,1", "simAt(lo(1),-0.1,0)", -61693, 60),
    ("Sensibilidad: GDPV +0,1", "simAt(lo(1),0.1,0)", 51299, 60),
    ("Sensibilidad: GDPV +0,2", "simAt(lo(1),0.2,0)", 94396, 60),
    ("Sensibilidad: precio −8 %", "simAt(lo(1),0,-0.08)", -137032, 60),
    ("Sensibilidad: precio +8 %", "simAt(lo(1),0,0.08)", 137032, 60),
]
# Balance de alfalfa de los 12 meses (hoja Calendario, columna G). La demanda se guardó con 1 decimal: tolerancia 0,6.
BALANCE = [12928.5, -1741.418, -6173.129, -6622.675, -8866.795, -12060.382, -7846.959, 4972.5, 2983.5, 2983.5, 4972.5, 8950.5]

# Cuentas hechas a mano para los casos que se escriben y los límites (ver comentario en cada una).
A_MANO = [
    # Una función a la vez: lo que devuelve y lo que se espera.
    ("Fórmula 0 (cero)", "money(0)", "$ 0"),
    ("Fórmula 999 (3 dígitos)", "money(999)", "$ 999"),
    ("Fórmula 1000 (cruza el separador de miles)", "money(1000)", "$ 1.000"),
    ("Fórmula 9999", "money(9999)", "$ 9.999"),
    ("Fórmula 1234567,89 (7 dígitos y decimales)", "money(1234567.89)", "$ 1.234.568"),
    ("Fórmula negativa", "money(-21678.63)", "-$ 21.679"),
    ("Abreviado 999", "short(999)", "$ 1 mil"),
    ("Abreviado 1 millón", "short(1e6)", "$ 1,0 M"),
    ("Abreviado 1234567", "short(1234567)", "$ 1,2 M"),
    ("Abreviado −1,5 millones", "short(-1500000)", "−$ 1,5 M"),
    ("Porcentaje 0,0516421", "pct(0.0516421)", "5,2%"),
    ("Porcentaje negativo", "pct(-0.0593,1)", "−5,9%"),
    ("Decimal cero", "dec(0)", "0,00"),
    ("Decimal 1234,5", "dec(1234.5)", "1234,50"),
]


def sin_nbsp(s):
    return str(s).replace(" ", " ")


def main():
    fallas, comprobaciones = [], 0

    def comparar(nombre, obtenido, esperado, tol=0.0):
        nonlocal comprobaciones
        comprobaciones += 1
        if isinstance(esperado, str):
            ok = sin_nbsp(obtenido) == esperado
        else:
            ok = obtenido is not None and abs(obtenido - esperado) <= tol
        if not ok:
            fallas.append(f"{nombre}: se obtuvo {obtenido!r} y se esperaba {esperado!r} (tolerancia {tol})")

    def sin_basura(pag, donde):
        nonlocal comprobaciones
        comprobaciones += 1
        texto = pag.inner_text("body")
        for malo in ("NaN", "Infinity", "undefined"):
            if malo in texto:
                fallas.append(f"{donde}: aparece «{malo}» en pantalla")

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={"width": 1366, "height": 900})
        ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
        pag = ctx.new_page()
        pag.goto(URL)
        pag.evaluate(OCULTAR_LOGIN)
        ev = pag.evaluate

        # 1) Todo lo del Excel
        for nombre, expr, esperado, tol in DEL_EXCEL:
            comparar(nombre, ev(expr), esperado, tol)
        bal = ev("forrajeBal().map(x=>x[1])")
        for i, esperado in enumerate(BALANCE):
            comparar(f"Balance de alfalfa, mes {i + 1}", bal[i], esperado, 0.6)

        # 2) Formatos y casos límite
        for nombre, expr, esperado in A_MANO:
            comparar(nombre, ev(expr), esperado)

        # 3) Ceros y vacíos: nada debe romperse ni dar NaN
        ev("() => {S.rec[0].vida=0;S.rec[0].rend=0;S.ins[0].ms=0;S.rec[0].ha=0;S.bib[5].merma=0;render()}")
        comparar("Vida útil 0: no divide por cero", ev("recCalc(S.rec[0]).amort"), 350, 1e-9)
        comparar("Rendimiento 0: costo por kg en 0", ev("recCalc(S.rec[0]).kg"), 0, 1e-12)
        comparar("MS 0: $/kg MS en 0", ev("insMS(S.ins[0])"), 0, 1e-12)
        for vista, sub in (("costos", "forraje"), ("costos", "dietas"), ("costos", "biblioteca"), ("hoy", None), ("mercado", None), ("analisis", "cal")):
            ev("([v,s]) => {UI.view=v; if(v==='costos')UI.ctab=s; if(v==='analisis')UI.atab=s; render()}", [vista, sub])
            sin_basura(pag, f"Con ceros, {vista} {sub or ''}")
        pag.evaluate("() => localStorage.clear()")
        pag.goto(URL)
        pag.evaluate(OCULTAR_LOGIN)

        # 4) Tecleo real, carácter por carácter, sobre pantallas de Costos
        pag.evaluate("() => {UI.view='costos';UI.ctab='forraje';render()}")
        campo = pag.locator('input[data-p="rec.0.vida"]')
        campo.fill("")
        campo.press_sequentially("5")                  # vida útil de la alfalfa 4 -> 5
        campo.press("Tab")
        # A mano: amortización 350/5 = 70; total = 70+15+15+240 = 340 USD/ha; ×1517 = 515.780 $; ÷5850 = 88,167521
        comparar("Tecleo vida útil 5: USD/ha/año", ev("recCalc(S.rec[0]).usd"), 340, 1e-9)
        comparar("Tecleo vida útil 5: $/ha/año", ev("recCalc(S.rec[0]).pesos"), 515780, 0.01)
        comparar("Tecleo vida útil 5: $/kg MS", ev("recCalc(S.rec[0]).kg"), 88.1675214, 1e-6)
        comparar("Tecleo vida útil 5: costo mostrado en la tabla", pag.inner_text("tr:has-text('Costo por kg de MS utilizada') td:nth-child(2)"), "$ 88,17")

        ha = pag.locator('input[data-p="rec.0.ha"]')
        ha.fill("")
        esperado_valor = ""
        for ch in "40":                                # hectáreas 17 -> 40, dígito por dígito
            ha.press_sequentially(ch)
            esperado_valor += ch
            comparar(f"Tecleo hectáreas: el campo muestra «{esperado_valor}»", ha.input_value(), esperado_valor)
        ha.press("Tab")
        # A mano (marzo): oferta = 40 ha × 9000 kg × 9 % × 65 % = 21.060; demanda = 21.010,9 (8.950,5 de oferta con 17 ha + 12.060,4 de falta) -> balance 49,1
        comparar("Tecleo hectáreas 40: balance de marzo", ev("forrajeBal()[5][1]"), 49.1, 0.06)
        # A mano: con 40 ha la oferta de cada mes supera la demanda (diciembre +8.627, enero +9.523, febrero +3.243, abril +2.917): ningún mes falta
        comparar("Tecleo hectáreas 40: meses con falta de alfalfa", ev("forrajeBal().filter(x=>x[1]<0).length"), 0, 0)
        sin_basura(pag, "Después de teclear hectáreas")

        # Precio del maíz: se destilda «tomar de Mercado» y se tipea 1000 (cruza el separador de miles)
        pag.evaluate("() => {UI.ctab='dietas';render()}")
        pag.locator('input[data-act="mkt"]').uncheck()
        precio = pag.locator('input[data-p="ins.0.precio"]')
        precio.fill("")
        esperado_valor = ""
        for ch in "1000":
            precio.press_sequentially(ch)
            esperado_valor += ch
            comparar(f"Tecleo precio del maíz: el campo muestra «{esperado_valor}»", precio.input_value(), esperado_valor)
        precio.press("Tab")
        # A mano: maíz 1000/0,87 = 1149,425287 $/kg MS.  Terminación = 0,91×1149,425287 + 0,09×1107,931034 = 1145,690805
        #         Adaptación = 0,6×1149,425287 + 0,1×1107,931034 + 0,3×136,363636 = 841,357367
        comparar("Maíz a 1000: $/kg MS", ev("insMS(S.ins[0])"), 1149.425287, 1e-6)
        comparar("Maíz a 1000: ración Terminación", ev("racCalc(S.rac[1]).cost"), 1145.690805, 1e-6)
        comparar("Maíz a 1000: ración Adaptación", ev("racCalc(S.rac[0]).cost"), 841.357367, 1e-6)
        sin_basura(pag, "Después de teclear el precio del maíz")

        # Precios del mes: se tipea todo el formulario (incluye 7 dígitos y decimales)
        pag.evaluate("() => {UI.view='mercado';render();newPrecio()}")
        for nombre, valor in (("gor", "4310.5"), ("inv", "6250"), ("maiz", "1234567"), ("usd", "1520")):
            c = pag.locator(f"dialog input[name={nombre}]")
            c.fill("")
            for ch in valor:
                c.press_sequentially(ch)
            comparar(f"Tecleo {nombre}: el campo muestra todo lo escrito", c.input_value(), valor)
        pag.locator("dialog input[name=f]").fill("01/2027")
        pag.click("dialog button.pri")
        # A mano: invernada/gordo = 6250/4310,5 = 1,4499478;  kg de maíz por kg de gordo = 4310,5×1000/1234567 = 3,4915075
        comparar("Precios del mes: invernada/gordo", ev("derived(lastMk()).ratio"), 1.4499478, 1e-6)
        comparar("Precios del mes: kg de maíz por kg de gordo", ev("derived(lastMk()).kgMaiz"), 3.4915075, 1e-6)
        sin_basura(pag, "Después de cargar precios del mes")
        for serie in ("soja", "gas", "kg"):             # el mes nuevo tiene que poder verse en todos los gráficos
            pag.evaluate("(s) => {UI.serie=s;render()}", serie)
            sin_basura(pag, f"Mercado, gráfico «{serie}», con el mes nuevo")

        # Costo por kilo ganado (calculadora de la Biblioteca)
        pag.evaluate("() => localStorage.clear()")
        pag.goto(URL)
        pag.evaluate(OCULTAR_LOGIN)
        # A mano: terminación a 300 kg: consumo 0,028×300 = 8,4 kg MS; costo diario = 8,4×408,0706074 + 30 = 3457,793; ÷ 1,3 = 2659,8408
        gv = ev("gdpvEf(S.bib[5],9,300)")
        comparar("Terminación a 300 kg: GDPV", gv, 1.3, 1e-9)
        comparar("Terminación a 300 kg: costo por kg ganado", (0.028 * 300 * ev("bibEf(S.bib[5])") + 30) / gv, 2659.8408, 0.01)
        # A mano: alfalfa estacional en octubre (0,9) a 275 kg: 0,9 + (−0,15)×(275−175)/100 = 0,75
        comparar("Alfalfa a 275 kg en octubre: GDPV ajustado por peso", ev("gdpvEf(S.bib[0],9,275)"), 0.75, 1e-9)
        # A mano: con GDPV bajo el mínimo (0,2) se usa el mínimo: 0,25 + (−0,15)×(475−175)/100 = −0,2 -> 0,2
        comparar("GDPV nunca baja del mínimo", ev("gdpvEf(S.bib[0],5,475)"), 0.2, 1e-9)
        comparar("GDPV 0 del mes: no gana peso", ev("gdpvEf(S.bib[2],0,200)"), 0, 1e-12)

        ctx.close()
        nav.close()

    print(f"{comprobaciones} comprobaciones.")
    if fallas:
        print(f"FALLAS: {len(fallas)}")
        for f in fallas:
            print("  -", f)
        sys.exit(1)
    print("TODOS LOS CÁLCULOS COINCIDEN CON LO ESPERADO.")


if __name__ == "__main__":
    main()
