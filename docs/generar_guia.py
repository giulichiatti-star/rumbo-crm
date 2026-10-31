"""Genera docs/guia-rapida.pdf (guía de 2 páginas para quien prueba la app), con capturas reales.
Uso: python3 docs/generar_guia.py   (necesita reportlab y Playwright)"""
import datetime
import json
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SITIO = "https://giulichiatti-star.github.io/rumbo-crm/"
NEGRO, GRIS, VERDE, FONDO = colors.HexColor("#12161f"), colors.HexColor("#6a7080"), colors.HexColor("#15b374"), colors.HexColor("#f4f3ee")


def capturas(carpeta):
    pedidas = [("hoy", "UI.view='hoy';render()"), ("ciclo", "UI.view='ciclo';UI.cview='tiempo';render()"), ("costos", "UI.view='costos';UI.ctab='dietas';render()")]
    rutas = {}
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={"width": 1280, "height": 800})
        ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
        pag = ctx.new_page()
        pag.goto((RAIZ / "index.html").as_uri())
        pag.evaluate("() => { const L = document.getElementById('login'); if (L) L.style.display = 'none'; }")
        for nombre, accion in pedidas:
            pag.evaluate("() => {" + accion + "}")
            pag.wait_for_timeout(500)
            ruta = carpeta / f"{nombre}.png"
            pag.screenshot(path=str(ruta))
            rutas[nombre] = ruta
        nav.close()
    return rutas


def main():
    est = getSampleStyleSheet()
    H1 = ParagraphStyle("h1", parent=est["Heading1"], fontName="Helvetica-Bold", fontSize=22, textColor=NEGRO, spaceAfter=4)
    H2 = ParagraphStyle("h2", parent=est["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=NEGRO, spaceBefore=12, spaceAfter=4)
    NR = ParagraphStyle("nr", parent=est["BodyText"], fontName="Helvetica", fontSize=10, leading=14, textColor=NEGRO)
    LI = ParagraphStyle("li", parent=NR, leftIndent=12, bulletIndent=0, spaceAfter=2)
    SUB = ParagraphStyle("sub", parent=NR, textColor=GRIS)

    def li(t):
        return Paragraph(t, LI, bulletText="•")

    tmp = pathlib.Path(tempfile.mkdtemp())
    img = capturas(tmp)

    def foto(nombre, ancho=16.4):
        return Image(str(img[nombre]), width=ancho * cm, height=ancho * cm * 800 / 1280)

    def pie(c, doc):
        c.saveState()
        c.setFillColor(NEGRO)
        c.rect(0, A4[1] - 1.1 * cm, A4[0], 1.1 * cm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(1.8 * cm, A4[1] - 0.72 * cm, "Rumbo · Guía rápida")
        c.drawRightString(A4[0] - 1.8 * cm, A4[1] - 0.72 * cm, f"Actualizada el {datetime.date.today():%d/%m/%Y}")
        c.setFillColor(GRIS)
        c.setFont("Helvetica", 8)
        c.drawCentredString(A4[0] / 2, 0.8 * cm, f"Página {doc.page}")
        c.restoreState()

    historia = [
        Spacer(1, 0.2 * cm), Paragraph("Rumbo", H1),
        Paragraph("Para evaluar sistemas de recría y engorde: costos, márgenes, mercado y forraje, en un solo lugar.", SUB),
        HRFlowable(width="100%", thickness=1, color=VERDE, spaceBefore=6, spaceAfter=6),
        Paragraph("1. Entrar por primera vez", H2),
        li(f"Abrí <b>{SITIO}</b> en el celular o en la computadora."),
        li("Escribí tu correo y una contraseña de al menos 6 letras o números, y tocá <b>Crear cuenta</b>. Las próximas veces, <b>Entrar</b>."),
        li("Con la misma cuenta ves lo mismo en el celular y en la computadora. No hace falta instalar nada."),
        Paragraph("2. Qué hay en cada pantalla", H2),
        foto("hoy", 15.5),
        Spacer(1, 0.15 * cm),
        Table([
            ["Hoy", "Lo que requiere tu atención, de a una cosa por vez. Deslizá la tarjeta a la derecha para descartarla o a la izquierda para verla después. También ves el mercado y tus tareas."],
            ["Ciclo", "Cada lote en una línea de tiempo, del ingreso a la venta. Arrastrá una barra para cambiar las fechas. El tablero los ordena por estado."],
            ["Productores", "La cartera con sus lotes, notas y tareas."],
            ["Mercado", "Precios del gordo, la invernada, el maíz y otros, con sus relaciones. Cargá los precios de cada mes."],
            ["Costos", "Costo del forraje, dietas y raciones, y la biblioteca de etapas. Cambiás un dato y todo se recalcula."],
            ["Real", "Lo que medís en el campo contra lo que el modelo suponía."],
            ["Análisis", "Calendario del sistema, sensibilidad, comparador de cuándo encerrar y vender, y curva de precios."],
        ], colWidths=[2.8 * cm, 14.2 * cm], style=TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, FONDO]), ("PADDING", (0, 0), (-1, -1), 5)])),
        Paragraph("Para ir rápido a cualquier lado, escribí en la barra de arriba (o apretá Cmd+K en Mac, Ctrl+K en Windows): un productor, un lote, «cargar precios»…", NR),
    ]
    historia[-2] = Table([[Paragraph(c, NR) if i else Paragraph(f"<b>{c}</b>", NR) for i, c in enumerate(f)] for f in [
        ["Hoy", "Lo que requiere tu atención, de a una cosa por vez. Deslizá la tarjeta a la derecha para descartarla o a la izquierda para verla después. También ves el mercado y tus tareas."],
        ["Ciclo", "Cada lote en una línea de tiempo, del ingreso a la venta. Arrastrá una barra para cambiar las fechas. El tablero los ordena por estado."],
        ["Productores", "La cartera con sus lotes, notas y tareas."],
        ["Mercado", "Precios del gordo, la invernada, el maíz y otros, con sus relaciones. Cargá los precios de cada mes."],
        ["Costos", "Costo del forraje, dietas y raciones, y la biblioteca de etapas. Cambiás un dato y todo se recalcula."],
        ["Real", "Lo que medís en el campo contra lo que el modelo suponía."],
        ["Análisis", "Calendario del sistema, sensibilidad, comparador de cuándo encerrar y vender, y curva de precios."]]],
        colWidths=[2.8 * cm, 14.2 * cm], style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, FONDO]), ("PADDING", (0, 0), (-1, -1), 5)]))
    historia += [
        Paragraph("3. Tus datos están cuidados", H2),
        li("Todo lo que cargás se guarda solo. Arriba a la derecha dice <b>Sincronizado</b> cuando ya quedó en el servidor."),
        li("Si no hay internet, seguí trabajando: se guarda en tu aparato y se envía cuando vuelva la conexión."),
        li("Si cargaste en el celular y en la computadora al mismo tiempo, la app te pregunta cuál querés conservar. <b>Lo otro no se pierde</b>: queda como copia."),
        li("Tocá el círculo de arriba a la derecha (<b>Mi cuenta y datos</b>) para descargar una copia, cargar una copia o restaurar una de las últimas 14 que se guardan solas, una por día."),
        Paragraph("4. Cuando algo no anda o se te ocurre algo", H2),
        li("Abajo de cualquier pantalla, tocá <b>¿Algo no anda? Contanos</b>. Escribí qué estabas haciendo y qué pasó. Nos llega con la pantalla y la versión, así podemos ayudarte rápido."),
        li("Si arriba aparece <b>«Hay una versión nueva»</b>, terminá lo que estás cargando y tocá <b>Actualizar</b>. No te saca de tu cuenta ni borra nada."),
        foto("costos", 12.5),
        Paragraph("Los valores marcados «ejemplo» o «ilustrativo» vienen así del modelo de origen: reemplazalos con tus datos reales (por ejemplo, tu costo de implantación, tus raciones y tus pesadas).", SUB),
    ]
    SimpleDocTemplate(str(RAIZ / "docs" / "guia-rapida.pdf"), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.9 * cm, bottomMargin=1.6 * cm,
                      title="Rumbo · Guía rápida", author="Rumbo").build(historia, onFirstPage=pie, onLaterPages=pie)
    print("docs/guia-rapida.pdf generado")


if __name__ == "__main__":
    main()
