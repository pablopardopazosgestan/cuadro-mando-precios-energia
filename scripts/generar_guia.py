"""Genera `docs/GUIA_DE_USUARIO.pdf`: guía completa para la persona que usa el cuadro de mando.

Usa las capturas de `docs/guia/` (tomadas del panel publicado con Playwright: `scripts/capturas_guia.js`) y las
páginas del último `sitio/informes/informe.pdf`. Los textos de esta guía describen el sistema tal como está en la
versión indicada en `precios/__init__.py`; si cambia algo relevante, actualizar aquí y regenerar.

    python scripts/generar_guia.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

from precios import __version__  # noqa: E402
from precios.informes import ACENTO, BORDE, SUPERFICIE, TINTA, TINTA2, TINTA3, URL_PANEL, _registrar_fuentes  # noqa: E402
from precios.panel import URL_REPO  # noqa: E402

DIR_GUIA = RAIZ / "docs" / "guia"
SALIDA = RAIZ / "docs" / "GUIA_DE_USUARIO.pdf"
ANCHO = A4[0] - 30 * mm


def main() -> Path:
    fn, fb = _registrar_fuentes()

    def st(nombre, **kw):
        base = dict(fontName=fn, fontSize=9.5, leading=13, textColor=colors.HexColor(TINTA), alignment=TA_JUSTIFY)
        base.update(kw)
        return ParagraphStyle(nombre, **base)

    normal = st("n")
    peq = st("p", fontSize=7.8, leading=10, textColor=colors.HexColor(TINTA2))
    pie_fig = st("pf", fontSize=7.8, leading=10, textColor=colors.HexColor(TINTA3), spaceBefore=2, spaceAfter=8)
    h1 = st("h1", fontName=fb, fontSize=22, leading=27, spaceAfter=6, alignment=0)
    h2 = st("h2", fontName=fb, fontSize=14.5, leading=18, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor(ACENTO), alignment=0, keepWithNext=1)
    h3 = st("h3", fontName=fb, fontSize=11, leading=14, spaceBefore=8, spaceAfter=3, alignment=0, keepWithNext=1)
    celda = st("c", fontSize=8.2, leading=10.5, alignment=0)
    celda_b = st("cb", fontName=fb, fontSize=8.2, leading=10.5, alignment=0)
    destacado = st("d", fontSize=9.5, leading=13, backColor=colors.HexColor(SUPERFICIE), borderPadding=(6, 8, 6, 8), spaceBefore=6, spaceAfter=10)

    def P(t, s=normal):
        return Paragraph(t, s)

    def lista(items):
        return ListFlowable([ListItem(P(i), leftIndent=12, value="•") for i in items], bulletType="bullet", start="•", leftIndent=12, bulletFontSize=8)

    def figura(nombre, texto, ancho=ANCHO):
        ruta = DIR_GUIA / nombre
        if not ruta.exists():
            return [P(f"[falta la captura {nombre}]", pie_fig)]
        from PIL import Image as PILImage
        with PILImage.open(ruta) as im:
            w, h = im.size
        alto = ancho * h / w
        if alto > 190 * mm:
            alto = 190 * mm
            ancho = alto * w / h
        return [Image(str(ruta), width=ancho, height=alto, hAlign="LEFT"), P(texto, pie_fig)]

    def tabla(filas, anchos, cab=True):
        datos = [[Paragraph(c, celda_b if (cab and i == 0) else celda) for c in f] for i, f in enumerate(filas)]
        t = Table(datos, colWidths=[ANCHO * a for a in anchos], repeatRows=1 if cab else 0)
        estilo = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor(BORDE)),
                  ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 4)]
        if cab:
            estilo += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(SUPERFICIE)), ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(TINTA))]
        t.setStyle(TableStyle(estilo))
        return t

    hoy = dt.date.today()

    def cabecera_pie(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(ACENTO))
        canvas.rect(0, A4[1] - 5 * mm, A4[0], 5 * mm, stroke=0, fill=1)
        canvas.setFont(fn, 8)
        canvas.setFillColor(colors.HexColor(TINTA3))
        canvas.drawString(15 * mm, A4[1] - 11 * mm, "Cuadro de mando de precios energéticos en España · guía de usuario")
        canvas.drawRightString(A4[0] - 15 * mm, A4[1] - 11 * mm, f"versión {__version__} · {hoy:%d/%m/%Y}")
        canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Página {doc.page}")
        canvas.drawString(15 * mm, 9 * mm, URL_PANEL)
        canvas.restoreState()

    doc = SimpleDocTemplate(str(SALIDA), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=17 * mm, bottomMargin=15 * mm,
                            title="Guía de usuario · Cuadro de mando de precios energéticos en España", author="Cuadro de mando de precios energéticos")
    el = []

    # ------------------------------------------------------------ Portada
    el += [Spacer(1, 30 * mm), P("Cuadro de mando de precios energéticos en España", h1),
           P("Guía de usuario", st("sub", fontName=fb, fontSize=15, leading=19, textColor=colors.HexColor(TINTA2), alignment=0)), Spacer(1, 6 * mm),
           P("Cómo consultar los ocho indicadores, comparar series, descargar el informe PDF y el Excel, entender cómo se calculan "
             "los precios y qué hacer cuando una fuente no responde.", st("intro", fontSize=11, leading=15)), Spacer(1, 10 * mm)]
    el += figura("01_portada.png", "El cuadro de mando publicado, con la barra de navegación, la cabecera y las primeras tarjetas.")
    el += [Spacer(1, 6 * mm),
           tabla([["Acceso", f'<a href="{URL_PANEL}" color="{ACENTO}">{URL_PANEL}</a>'],
                  ["Actualización", "Automática, cada lunes a las 05:17 UTC (06:17 o 07:17 hora peninsular). También a mano."],
                  ["Informes", "PDF (4 páginas) y Excel (histórico completo), regenerados en cada actualización y descargables desde el panel."],
                  ["Código y datos", f'<a href="{URL_REPO}" color="{ACENTO}">{URL_REPO}</a>'],
                  ["Versión de esta guía", f"{__version__} · {hoy:%d/%m/%Y}"]], [0.25, 0.75], cab=False)]
    el.append(PageBreak())

    # ------------------------------------------------------------ Índice
    el += [P("Contenido", h2)]
    el += [lista(["1. Qué es y qué mide",
                  "2. Cómo entrar y moverse por el panel",
                  "3. Resumen ejecutivo: tarjetas, ranking, tabla y claves de la semana",
                  "4. Comparativo: elegir series, periodo, Base 100, media móvil y compartir",
                  "5. Evolución de cada indicador: unidad, datos, CSV y cambios de impuestos",
                  "6. Informe PDF: qué hay en cada página",
                  "7. Excel: hojas, gráficos vinculados y hoja «Comparador»",
                  "8. Actualización semanal: cómo funciona, cómo lanzarla y cómo saber si ha ido bien",
                  "9. Si una fuente falla",
                  "10. Cómo se calculan los precios: criterios, impuestos y conversiones",
                  "11. Preguntas frecuentes",
                  "12. Glosario"])]

    # ------------------------------------------------------------ 1
    el += [P("1. Qué es y qué mide", h2),
           P("El cuadro de mando reúne en una sola página, en una unidad común (€/kWh), los precios de las energías más habituales en "
             "España: mercado eléctrico, electricidad regulada, gas mayorista, gas regulado, gasóleos, butano y pellet. Todos los datos "
             "proceden de fuentes públicas oficiales o sectoriales, se descargan automáticamente cada semana y se guardan con su fecha, "
             "su fuente y si llevan o no impuestos. <b>Nada se estima ni se rellena:</b> cuando la fuente no publica un dato, el panel "
             "muestra «no disponible» (n. d.)."),
           tabla([["N.º", "Indicador", "Fuente", "Frecuencia", "Impuestos"],
                  ["1", "Electricidad: precio del mercado diario (OMIE), España", "OMIE", "Diaria", "Sin impuestos (mayorista)"],
                  ["2", "Gas natural: MIBGAS-ES Index", "MIBGAS", "Diaria", "Sin impuestos (mayorista)"],
                  ["3", "Gasóleo de automoción (gasóleo A): precio medio en España", "Comisión Europea, Boletín Petrolero", "Semanal (lunes)", "Con impuestos"],
                  ["4", "Electricidad PVPC: término de energía, tarifa 2.0TD (Península)", "REE / ESIOS", "Diaria", "Calculado con impuestos"],
                  ["5", "Gas natural TUR 2: término variable", "BOE (resoluciones trimestrales)", "Trimestral", "Calculado con impuestos"],
                  ["6", "Gasóleo de calefacción (gasóleo C): precio medio en España", "Comisión Europea, Boletín Petrolero", "Semanal (lunes)", "Con impuestos"],
                  ["7", "Butano: bombona regulada de 12,5 kg", "BOE (resoluciones bimestrales)", "Bimestral", "Calculado con impuestos"],
                  ["8", "Pellet: saco de 15 kg y granel en volquete", "AVEBIOM, Índice de Precios de Biomasa", "Trimestral (anual hasta 2024)", "Con impuestos"]],
                 [0.06, 0.38, 0.24, 0.14, 0.18]),
           P("Histórico: desde enero de 2020 donde la fuente lo publica (el encargo exige desde 2022); el PVPC 2.0TD existe desde junio de "
             "2021 y el pellet tiene dato trimestral desde el cuarto trimestre de 2024 (antes, medias anuales oficiales de AVEBIOM).", peq)]

    # ------------------------------------------------------------ 2
    el += [P("2. Cómo entrar y moverse por el panel", h2),
           P(f"Abra <a href='{URL_PANEL}' color='{ACENTO}'>{URL_PANEL}</a> en cualquier navegador (ordenador, tableta o móvil). No hace "
             "falta usuario ni contraseña: la página es pública para quien tenga el enlace."),
           lista(["<b>Barra superior:</b> enlaces fijos a Resumen, Comparativo, Indicadores, Estado, Fuentes y Descargas.",
                  "<b>Cabecera:</b> fecha de referencia (el día de la última actualización), hora de la última actualización correcta y versión; "
                  "botones «Informe PDF», «Histórico Excel» y «Actualizar» (lanza la actualización de datos desde el propio panel; apartado 8.2).",
                  "<b>Aviso:</b> si en la última actualización falló alguna fuente, aparece una franja de aviso bajo la cabecera con el nombre de la fuente.",
                  "<b>Claro u oscuro:</b> el panel sigue el modo del dispositivo. <b>Imprimir:</b> Ctrl+P (o Cmd+P) produce una copia limpia, sin controles.",
                  "<b>Móvil:</b> la página se adapta al ancho de pantalla; las tablas se desplazan lateralmente con el dedo."])]
    el += figura("11_movil.png", "Vista en un teléfono móvil.", ancho=55 * mm)

    # ------------------------------------------------------------ 3
    el += [P("3. Resumen ejecutivo", h2), P("3.1 Tarjetas", h3),
           P("Ocho tarjetas, una por indicador (la del pellet incluye el granel en una línea adicional). Cada tarjeta muestra:"),
           lista(["El <b>precio actual en €/kWh</b>, en grande.",
                  "<b>Semana:</b> variación frente al periodo anterior. <b>Un año:</b> variación frente a hace un año. "
                  "▲ en rojo = sube (peor para el consumidor), ▼ en verde = baja, ■ = sin cambio.",
                  "La <b>fuente</b> y la <b>fecha del dato</b> en que se basa el precio.",
                  "Una <b>línea de tendencia</b> con las medias mensuales de los últimos 24 meses.",
                  "La etiqueta «mayorista, sin impuestos» (OMIE y MIBGAS) o «con impuestos» (el resto)."])]
    el += figura("02_tarjetas.png", "Tarjetas del resumen ejecutivo.")
    el += [P("<b>Qué es el «precio actual»:</b> para OMIE, MIBGAS y PVPC, la media de los últimos 7 días con dato; para los gasóleos, "
             "la última semana publicada por el Boletín Petrolero; para TUR 2, butano y pellet, el valor vigente en la fecha de referencia. "
             "Las variaciones comparan con el periodo anterior equivalente (los 7 días previos, la semana anterior o el valor vigente 7 "
             "días antes) y con la misma fecha de hace un año.", destacado),
           P("3.2 Ranking y claves de la semana", h3),
           P("El gráfico de barras ordena de menor a mayor el coste por kWh de las energías finales con impuestos (todas menos OMIE y "
             "MIBGAS, que son precios mayoristas y no son comparables con un precio al consumidor). A su derecha, «Claves de la semana» "
             "resume en frases las variaciones de al menos un 1 %, las interanuales y el orden de precios. Esas frases se generan "
             "automáticamente a partir de los números de la tabla: no contienen interpretación ni previsiones.")]
    el += figura("03_ranking_claves.png", "Ranking del coste por kWh y claves de la semana.")
    el += [P("3.3 Tabla de indicadores", h3),
           P("La tabla repite los datos de las tarjetas con más detalle: precio en €/kWh, variaciones, fecha del dato, fuente (con enlace) "
             "y estado. <b>Pulse una cabecera para ordenar</b> por esa columna. Al pasar el ratón por una fila se ve la base del cálculo, "
             "el valor en la unidad original y las notas."),
           tabla([["Estado", "Significado"],
                  ["● actualizado", "Hay un dato nuevo publicado en los últimos 7 días."],
                  ["● sin actualización en el periodo", "La fuente no ha publicado nada nuevo esta semana, pero está dentro de su periodicidad normal (por ejemplo, el TUR 2 cambia cada trimestre)."],
                  ["● fuente no disponible o dato pendiente", "No hay datos, o hace más tiempo del que admite la periodicidad de la fuente sin dato nuevo. Se muestra el último dato correcto y su fecha."]],
                 [0.3, 0.7])]
    el += figura("04_tabla.png", "Tabla de indicadores, ordenable por columnas.")

    # ------------------------------------------------------------ 4
    el += [P("4. Comparativo en €/kWh", h2),
           P("Es la herramienta de análisis del panel: un solo gráfico donde se superponen las series que usted elija, todas en €/kWh, "
             "con el periodo y las opciones que necesite. La configuración se guarda en la dirección de la página, así que puede "
             "compartir exactamente la vista que está mirando."),
           P("4.1 Elegir las series", h3),
           lista(["<b>Casillas de series:</b> marque o desmarque cada indicador. El color de la casilla es el de la línea. OMIE y MIBGAS llevan la etiqueta «sin impuestos».",
                  "<b>Conjuntos:</b> botones que seleccionan de golpe un grupo: <i>Todas</i>; <i>Energía final con impuestos</i> (todo menos los mayoristas, "
                  "las mismas series que el ranking); <i>Calefacción doméstica</i> (TUR 2, gasóleo C, butano, pellet saco y granel); <i>Electricidad</i> (OMIE y PVPC); "
                  "<i>Gas natural</i> (MIBGAS y TUR 2); <i>Carburantes</i> (gasóleo A); <i>Ninguna</i>.",
                  "También puede pulsar un nombre en la leyenda del gráfico para quitar esa serie."]),
           P("4.2 Periodo y frecuencia", h3),
           lista(["<b>Desde / Hasta:</b> fechas libres. <b>Atajos:</b> 3 meses, 1 año, 3 años, Desde 2022, Todo (desde 2020).",
                  "<b>Frecuencia original:</b> cada serie con su ritmo natural (diaria, semanal, trimestral…). Las series reguladas y el pellet se dibujan "
                  "en escalón: el precio se mantiene hasta la siguiente revisión.",
                  "<b>Media mensual:</b> todas las series como media de cada mes, útil para periodos largos.",
                  "El periodo elegido aquí se aplica también a los gráficos individuales de la sección siguiente."]),
           P("4.3 Opciones", h3),
           lista(["<b>Base 100 en la primera fecha del periodo:</b> cada serie se divide por su primer valor disponible dentro del periodo, de modo que todas "
                  "arrancan en 100 y el gráfico muestra <i>cuánto ha subido o bajado cada una en porcentaje</i>. Es la forma de comparar la evolución de "
                  "precios de magnitudes muy distintas (por ejemplo, el PVPC y el pellet). Al pasar el ratón se sigue viendo el €/kWh real.",
                  "<b>Media móvil de 7 días:</b> suaviza las tres series diarias (OMIE, MIBGAS y PVPC) para que no oculten al resto. El dato diario "
                  "sigue disponible en los gráficos individuales y en el Excel.",
                  "<b>Copiar enlace:</b> copia al portapapeles una dirección que reproduce la comparación exacta (series, fechas, frecuencia y opciones). "
                  "Péguela en un correo o un mensaje: quien la abra verá lo mismo."]),
           P("4.4 Leer el gráfico", h3),
           lista(["La leyenda está encima del área de datos y nunca tapa las líneas. Al final de cada línea aparece su nombre y su último valor del periodo; "
                  "si varias etiquetas coinciden, se separan en vertical.",
                  "Pase el ratón por una línea para ver la fecha, el €/kWh y el dato en la unidad original. Arrastre sobre el gráfico para ampliar; "
                  "doble clic para volver. La barra inferior permite desplazar el periodo visible.",
                  "Los huecos son periodos sin dato en la fuente: no se rellenan."])]
    el += figura("05_controles.png", "Controles del comparativo: series, conjuntos, periodo y opciones.")
    el += figura("06_comparativo.png", "Comparativo de cuatro series de calefacción doméstica, frecuencia original, con etiquetas al final de cada línea.")
    el += figura("07_base100.png", "El mismo periodo con el conjunto «Energía final con impuestos» y Base 100: se compara la evolución relativa, no el precio.")

    # ------------------------------------------------------------ 5
    el += [P("5. Evolución de cada indicador", h2),
           P("Nueve gráficos, uno por serie, con el periodo elegido en el comparativo. Cada tarjeta tiene cuatro botones:"),
           lista(["<b>Unidad original:</b> el dato tal como lo publica la fuente (€/MWh, €/l, c€/kWh, c€/kg, €/saco, €/t). <b>€/kWh:</b> el mismo dato convertido.",
                  "<b>Ver datos:</b> despliega una tabla con cada dato del periodo: fecha, periodo, valor original, €/kWh sin impuestos y €/kWh con impuestos. "
                  "Los mayoristas indican «no aplica» en la columna con impuestos.",
                  "<b>CSV:</b> descarga esa tabla como fichero de texto separado por «;» (se abre directamente en Excel) con una columna más para la fuente. "
                  "Los datos no disponibles quedan vacíos.",
                  "<b>Mostrar cambios de impuestos</b> (casilla sobre los gráficos): dibuja una línea vertical con el símbolo ⚖ en cada fecha en que cambió "
                  "el IVA, el impuesto especial sobre la electricidad o el impuesto sobre hidrocarburos de esa serie. Al pasar el ratón se lee el tipo "
                  "anterior, el nuevo y la norma del BOE. Afecta al PVPC, TUR 2, butano y pellet."])]
    el += figura("08_indicador_tur2.png", "Gráfico del TUR 2 con los cambios de impuestos marcados y la tabla «Ver datos» desplegada.", ancho=95 * mm)
    el += figura("09_indicadores.png", "Los nueve gráficos individuales.")
    el += [P("El último valor aparece anotado junto al final de la línea. Las series reguladas (TUR 2, butano) y el pellet se dibujan en escalón.", peq)]

    # ------------------------------------------------------------ 6
    el += [P("6. Informe PDF", h2),
           P("Botón «Informe PDF» en la cabecera o enlace en «Descargas». Se regenera en cada actualización con los mismos datos del panel; "
             "solo se conserva la última versión (el histórico completo está en el Excel). Dos páginas en A4, pensadas para leerse en cinco minutos:"),
           tabla([["Página", "Contenido"],
                  ["1. Cuadro de mando", "Ocho tarjetas con precio, variaciones, fuente, fecha y tendencia de 24 meses; ranking del coste por kWh de la energía final; "
                                         "claves de la semana; y el gráfico «Pellet frente a las alternativas de calefacción»: cuánto más (o menos) cuesta el kWh de gasóleo C, "
                                         "butano, TUR 2 y PVPC que el del pellet en saco, hoy y hace un año, y la evolución de esa diferencia en 24 meses."],
                  ["2. Evolución y lectura", "Ocho gráficos grandes, uno por indicador, con los últimos 24 meses en €/kWh (en las series diarias, el dato en claro y la media "
                                             "de 7 días en trazo grueso; el pellet a granel en discontinuo) y el último valor anotado. Encima, precio y variaciones; debajo, una "
                                             "explicación fija de qué mide y por qué importa para el coste de producción o el precio del pellet. Cierra con el estado de las fuentes."]],
                 [0.24, 0.76]),
           P("<b>Cómo leer el sobrecoste:</b> es el precio de la alternativa dividido por el precio del pellet en saco, menos uno, ambos en €/kWh con impuestos. "
             "Positivo significa que el pellet es más barato; si crece respecto a hace un año, la ventaja del pellet se amplía. El valor de hace un año se deduce "
             "de las variaciones interanuales. Las explicaciones fijas se redactaron el 28/10/2026 y se revisan a mano. "
             "El impacto en euros por tonelada depende de los consumos de cada planta y no se incluye.", destacado)]
    el += [Table([[Image(str(DIR_GUIA / f"pdf_p{i}.png"), width=ANCHO / 2 - 3 * mm, height=(ANCHO / 2 - 3 * mm) * 1.414) for i in (1, 2)]],
                 colWidths=[ANCHO / 2] * 2, style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1)])),
           P("Las dos páginas del informe semanal.", pie_fig)]

    # ------------------------------------------------------------ 7
    el += [P("7. Excel", h2),
           P("Botón «Histórico Excel» o enlace en «Descargas». Un solo libro con todo el histórico, los datos originales y los convertidos, "
             "medias, gráficos vinculados y un comparador. Al abrirlo, Excel recalcula las fórmulas (si aparece el aviso de contenido "
             "protegido, pulse «Habilitar edición»)."),
           tabla([["Hoja", "Qué contiene"],
                  ["Cuadro de mando", "Ocho tarjetas con precio y variaciones; tabla de indicadores con formato condicional (color y flechas); claves de la semana; ranking de la energía final ordenado, con gráfico."],
                  ["Anual", "Media anual en €/kWh de cada serie (solo años completos; el año en curso con los meses disponibles)."],
                  ["Mensual", "Media mensual de cada serie en €/kWh y en su unidad original, desde 2020, en formato tabla con filtros."],
                  ["Gráficos", "Comparativo mensual, barras anuales y nueve gráficos individuales, vinculados a «Mensual» y «Anual»: si cambia un dato, cambian los gráficos."],
                  ["Comparador", "Hasta cuatro series elegidas con desplegables, frecuencia mensual o anual y Base 100; tabla calculada con fórmulas y gráfico de líneas vinculado."],
                  ["Datos 1 … Datos 8", "Una hoja por serie con el histórico completo en su frecuencia original: fecha, periodo, valor original, unidad, €/kWh sin y con impuestos, origen del precio con impuestos, impuestos aplicados (con referencia al BOE), fecha de publicación, referencia (fichero, BOE o PDF) y nota. Formato tabla con filtros y paneles inmovilizados."],
                  ["Fuentes y criterios", "Fuente, dirección, unidad, frecuencia, impuestos del dato original, conversión y nota de cada indicador; factores de conversión; criterios."]],
                 [0.2, 0.8]),
           P("7.1 Cómo usar la hoja «Comparador»", h3),
           lista(["En las celdas amarillas <b>Serie 1</b> a <b>Serie 4</b> elija las series con el desplegable (deje en blanco las que no quiera).",
                  "En <b>Frecuencia</b> elija «Mensual» o «Anual». En <b>Base 100</b>, «Sí» para ver índices (cada serie dividida por su primer valor disponible) o «No» para €/kWh.",
                  "La tabla de debajo y el gráfico se recalculan solos. Los periodos sin dato muestran #N/A y no se dibujan: es intencionado, nada se rellena.",
                  "Las columnas de la derecha (H a K) son auxiliares: contienen el valor sin Base 100 y la columna de origen. No hace falta tocarlas."])]
    el += figura("xl_comparador.png", "Hoja «Comparador» del Excel (vista impresa; el gráfico vinculado aparece a la derecha de los desplegables al abrir el libro).", ancho=120 * mm)

    # ------------------------------------------------------------ 8
    el += [P("8. Actualización semanal", h2),
           P("8.1 Cómo funciona", h3),
           P("Cada lunes a las 05:17 UTC (06:17 en horario de invierno, 07:17 en verano) un proceso automático en GitHub Actions ejecuta, en este orden:"),
           ListFlowable([ListItem(P(t), leftIndent=14) for t in [
               "Pruebas automáticas del programa (si fallan, no se publica nada).",
               "Descarga de lo nuevo de cada fuente: OMIE, MIBGAS, ESIOS, Boletín Petrolero, BOE, AVEBIOM e INE (solo lo posterior al último dato guardado).",
               "Comprobación de que ninguna serie pierde histórico respecto a la versión anterior (si lo perdiera, se detiene).",
               "Comprobaciones con 22 valores de control contrastados con la fuente.",
               "Generación del informe PDF y del Excel.",
               "Generación del cuadro de mando y guardado de los datos en el repositorio (commit «Actualización automática»).",
               "Publicación de la web."]], bulletType="1", leftIndent=14),
           P("Todo el proceso dura entre uno y dos minutos. El panel muestra la fecha y hora de la última actualización correcta en la cabecera."),
           P("8.2 Lanzarla a mano", h3),
           P("Pulse <b>«Actualizar»</b> en la cabecera del panel. Se abre un cuadro que explica el proceso y pide, <b>solo la primera vez</b>, un token "
             "personal de GitHub con permiso de escritura en <i>Actions</i> sobre este repositorio. El token se guarda únicamente en ese navegador (no "
             "viaja a ningún sitio salvo a la API de GitHub) y puede borrarse con «Olvidar token». Al pulsar «Actualizar ahora», el panel lanza la "
             "actualización, muestra el progreso y se recarga solo cuando termina (uno o dos minutos). Si alguna fuente no respondió, lo indica y enlaza el registro."),
           lista(["<b>Cómo obtener el token (una vez):</b> en GitHub, foto de perfil → <i>Settings</i> → <i>Developer settings</i> → <i>Personal access tokens</i> → "
                  "<i>Fine-grained tokens</i> → <i>Generate new token</i>. Repositorio: solo este. Permisos: <i>Actions: Read and write</i>. Copie el token (empieza por github_pat_) y péguelo en el cuadro.",
                  "<b>No confundir con el token de ESIOS:</b> ese ya está guardado como secreto en GitHub y lo usa el propio proceso de actualización para descargar el PVPC. "
                  "Aquí hace falta permiso para <i>lanzar</i> el proceso, y eso solo lo da un token de GitHub; si se pega el de ESIOS, el cuadro lo rechaza.",
                  "<b>Alternativa sin token:</b> botón «Ver ejecuciones» del mismo cuadro (abre GitHub Actions). Elija «Actualizar datos y publicar» y pulse «Run workflow»."]),
           P("8.3 Saber si ha ido bien", h3),
           lista(["<b>En el panel:</b> sección «Estado de las fuentes y actualización»: por fuente, última descarga correcta, último dato y resultado (● correcto / ● error con el mensaje), y enlace a la ejecución.",
                  "<b>En GitHub:</b> la ejecución aparece en verde si todas las fuentes respondieron, y en rojo si alguna falló. En rojo, GitHub envía un correo al propietario del repositorio.",
                  "<b>Importante:</b> aunque una fuente falle, la web <i>se publica igualmente</i> con el último dato correcto de esa fuente, marcado con su fecha. El rojo es un aviso, no una caída del sistema."])]
    el += figura("12_actualizar.png", "El cuadro «Actualizar los datos ahora», con las instrucciones para el token.", ancho=120 * mm)
    el += figura("10_estado.png", "Estado de las fuentes y descargas.")

    # ------------------------------------------------------------ 9
    el += [P("9. Si una fuente falla", h2),
           P("Los fallos más probables y qué hacer. En todos los casos, el primer paso es relanzar la actualización a mano (apartado 8.2): "
             "la mayoría son caídas o bloqueos pasajeros de la fuente."),
           tabla([["Fuente", "Síntoma", "Qué hacer"],
                  ["REE / ESIOS (PVPC)", "Error de autorización o «403».", "Comprobar que el secreto ESIOS_TOKEN sigue creado en el repositorio (Settings → Secrets and variables → Actions). Si es un bloqueo por exceso de peticiones, el programa espera y reintenta solo; relanzar más tarde. El token se pide gratis a REE (consultasios@ree.es)."],
                  ["AVEBIOM (pellet)", "«Desafío captcha» o «ninguna vía devolvió PDF».", "Es un bloqueo del servidor de AVEBIOM a los robots. El panel solo lo consulta cuando puede haber un trimestre nuevo y reintenta con esperas; el resto del tiempo usa los PDF ya guardados. Si persiste semanas, ejecutar la actualización del pellet desde un ordenador (apartado 11) para guardar el PDF nuevo."],
                  ["BOE (TUR 2, butano)", "Error de conexión; o no aparece la resolución nueva.", "Relanzar. Si la resolución se publicó pero no se detecta, su título ha cambiado: avisar al responsable técnico (se busca por título en el sumario del BOE)."],
                  ["OMIE, MIBGAS", "Fichero del día no publicado o formato distinto.", "Relanzar al día siguiente. Un día sin dato no afecta al resto de la serie."],
                  ["Comisión Europea (gasóleos)", "Descarga interrumpida; dato de hace dos semanas.", "Relanzar. El Boletín Petrolero se publica con una o dos semanas de retraso: «sin actualización en el periodo» es normal."],
                  ["INE (IPC)", "Error de conexión.", "Relanzar. Solo afecta a los tipos impositivos de 2026 que dependen del IPC; mientras tanto esos meses quedan «no disponibles», nunca estimados."]],
                 [0.18, 0.24, 0.58])]

    # ------------------------------------------------------------ 10
    el += [P("10. Cómo se calculan los precios", h2),
           P("10.1 Criterios generales", h3),
           lista(["Cada dato conserva su fuente, su fecha de publicación, si es original o calculado y si lleva impuestos.",
                  "Nunca se interpola, se estima ni se rellena. Un hueco en la fuente es un hueco en el panel.",
                  "Los precios mayoristas (OMIE, MIBGAS) se presentan sin impuestos y se marcan como tales: no son comparables con un precio al consumidor.",
                  "Los precios con impuestos del PVPC, el TUR 2 y el butano se calculan con los tipos vigentes en cada fecha (IVA, impuesto especial sobre la "
                  "electricidad e impuesto sobre hidrocarburos), con su referencia al BOE. El Boletín Petrolero y AVEBIOM publican ya con impuestos.",
                  "En 2026 varios tipos dependen de la evolución del IPC (reales decretos-leyes 7/2026, 18/2026 y 25/2026): se leen del INE y, hasta que el INE "
                  "publica el dato, el mes queda «no disponible»."]),
           P("10.2 Conversión a €/kWh", h3),
           tabla([["Indicador", "Conversión"],
                  ["OMIE, MIBGAS, PVPC", "€/MWh ÷ 1.000. El MIBGAS se expresa sobre poder calorífico superior (PCS), como todo el mercado gasista."],
                  ["Gasóleos A y C", "€/l ÷ 10,28 kWh/l (poder calorífico inferior, IDAE)."],
                  ["TUR 2", "c€/kWh (PCS) ÷ 100 ÷ 0,904 = €/kWh sobre PCI; con impuestos: (precio + impuesto sobre hidrocarburos) × (1 + IVA)."],
                  ["Butano", "Precio de la bombona = c€/kg ÷ 100 × 12,5 kg, más impuesto sobre hidrocarburos e IVA; €/kWh = € ÷ 12,5 kg ÷ 12,73 kWh/kg (PCI)."],
                  ["Pellet", "€/saco ÷ 15 kg ÷ 4,8 kWh/kg; €/t ÷ 1.000 ÷ 4,8 kWh/kg (PCI). AVEBIOM usa 4,76 kWh/kg; su c€/kWh se guarda en la nota de cada dato."]],
                 [0.24, 0.76]),
           P("La tabla completa de impuestos por fecha, con la referencia al BOE de cada cambio, está en el documento de metodología del repositorio "
             f"({URL_REPO}/blob/main/docs/METODOLOGIA.md) y, resumida, en la última página del informe PDF y en la hoja «Fuentes y criterios» del Excel.", peq)]

    # ------------------------------------------------------------ 11
    el += [P("11. Preguntas frecuentes", h2)]
    faq = [
        ("¿Por qué el pellet (o el TUR 2) dice «sin actualización en el periodo»?",
         "Porque su fuente publica cada trimestre (o cada dos meses el butano). El dato mostrado es el vigente; cambiará cuando se publique el siguiente."),
        ("¿Por qué OMIE o MIBGAS tienen un €/kWh tan bajo frente a los demás?",
         "Son precios mayoristas, sin impuestos ni peajes ni márgenes. Por eso no entran en el ranking de energía final."),
        ("¿Por qué el PVPC sube y baja tanto de un día a otro?",
         "Es un precio diario ligado al mercado. Para leer la tendencia use la media móvil de 7 días o la frecuencia mensual del comparativo."),
        ("¿Qué significa «n. d.»?",
         "No disponible: la fuente no publica ese dato o todavía no puede calcularse (por ejemplo, un tipo impositivo de 2026 pendiente del IPC). Nunca se sustituye por una estimación."),
        ("¿Puedo ver el precio de 2022 con la bonificación de 20 c€/l del gasóleo?",
         "El Boletín Petrolero no descuenta esa bonificación (abril–diciembre de 2022); el panel muestra el precio del Boletín y lo advierte en la nota."),
        ("¿Cómo comparo la evolución del gasóleo C con la del pellet?",
         "En el comparativo marque solo esas dos series (o use «Calefacción doméstica»), elija el periodo y active Base 100 para ver la evolución relativa."),
        ("¿Cómo mando a alguien exactamente lo que estoy viendo?",
         "Pulse «Copiar enlace» en el comparativo y pegue la dirección. Para una copia fija, imprima a PDF (Ctrl+P) o descargue el informe."),
        ("¿Los datos del Excel son los mismos que los del panel?",
         "Sí: panel, PDF y Excel se generan en la misma ejecución a partir de los mismos ficheros de datos."),
        ("¿Se puede cambiar un dato a mano?",
         "No está previsto: todos los datos vienen de las fuentes y se regeneran en cada actualización. Un cambio manual se perdería en la siguiente."),
        ("¿Dónde está el histórico completo si el PDF y el Excel solo guardan la última versión?",
         "En el propio Excel (hojas «Datos») y en el repositorio, carpeta datos/, con todo el historial de versiones."),
    ]
    for q, a in faq:
        el.append(KeepTogether([P(f"<b>{q}</b>"), P(a), Spacer(1, 3)]))
    el += [P("Actualizar el pellet desde un ordenador (solo si AVEBIOM bloquea al servidor de GitHub durante semanas): instalar Python 3.12 o superior, "
             "descargar el repositorio y ejecutar <font face='Courier'>pip install -r requirements.txt</font> y "
             "<font face='Courier'>python -m precios actualizar --solo pellet_saco</font>; después, subir al repositorio los ficheros nuevos de "
             "<font face='Courier'>datos/</font>. Las instrucciones técnicas completas están en docs/USO.md del repositorio.", peq)]

    # ------------------------------------------------------------ 12
    el += [P("12. Glosario", h2),
           tabla([["Término", "Significado"],
                  ["€/kWh", "Euros por kilovatio hora: coste de una unidad de energía. Permite comparar electricidad, gas, gasóleo, butano y pellet entre sí."],
                  ["PCI / PCS", "Poder calorífico inferior / superior. El panel convierte a €/kWh sobre PCI (la energía realmente aprovechable); el gas se comercializa sobre PCS (factor 0,904)."],
                  ["OMIE", "Operador del mercado eléctrico ibérico: precio del mercado diario (mayorista)."],
                  ["MIBGAS-ES Index", "Índice diario del mercado mayorista de gas de España."],
                  ["PVPC 2.0TD", "Precio voluntario para el pequeño consumidor: tarifa eléctrica regulada (término de energía, media diaria)."],
                  ["TUR 2", "Tarifa de último recurso del gas natural para consumos entre 5.000 y 50.000 kWh/año (término variable)."],
                  ["Boletín Petrolero", "Weekly Oil Bulletin de la Comisión Europea: precios medios semanales de carburantes por país."],
                  ["AVEBIOM", "Asociación Española de la Biomasa; publica el Índice de Precios de Biomasa al Consumidor (pellet)."],
                  ["IEE", "Impuesto especial sobre la electricidad."],
                  ["IH", "Impuesto sobre hidrocarburos (gas natural, GLP)."],
                  ["Base 100", "Índice que fija en 100 el primer valor del periodo de cada serie para comparar evoluciones porcentuales."],
                  ["Media móvil de 7 días", "Media de cada día con los seis anteriores; suaviza las oscilaciones diarias."],
                  ["Variación interanual", "Cambio porcentual respecto al mismo momento de hace un año."],
                  ["n. d.", "No disponible: la fuente no da el dato. Nunca se estima."],
                  ["GitHub Actions / Pages", "Servicio que ejecuta la actualización semanal y publica la web."]],
                 [0.22, 0.78])]

    doc.build(el, onFirstPage=cabecera_pie, onLaterPages=cabecera_pie)
    return SALIDA


if __name__ == "__main__":
    print(main())
