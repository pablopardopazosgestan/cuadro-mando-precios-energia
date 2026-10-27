"""Informes descargables: `sitio/informes/informe.pdf` y `sitio/informes/historico.xlsx`.

Se generan en cada actualización con los mismos datos que el cuadro de mando (`panel.construir`).
- PDF: presentación parecida al boletín de referencia, limitada a los ocho indicadores: fecha y periodo,
  resumen ejecutivo, tabla de precios y variaciones, gráfico comparativo, gráficos individuales, comentario
  de evolución, fuentes y metodología.
- Excel: histórico completo (frecuencia original, datos originales y convertidos), medias mensuales, tabla
  resumen, gráficos vinculados a los datos, fuentes y criterios; con filtros automáticos en cada tabla.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.chart import LineChart, Reference  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from . import __version__  # noqa: E402
from .config import DIR_DATOS, DIR_SERIES  # noqa: E402
from .indicadores import INDICADORES, ORDEN  # noqa: E402
from .panel import COLORES, DIR_SITIO, TIPO, URL_REPO, columna_panel, construir  # noqa: E402

log = logging.getLogger(__name__)

DIR_INFORMES = DIR_SITIO / "informes"
INICIO_INFORME = dt.date(2022, 1, 1)
NOMBRE_FUENTE = {"omie": "OMIE", "mibgas": "MIBGAS", "gasoleo_a": "Comisión Europea (WOB)", "gasoleo_c": "Comisión Europea (WOB)",
                 "pvpc": "REE/ESIOS", "tur2": "BOE", "butano": "BOE", "pellet_saco": "AVEBIOM", "pellet_granel": "AVEBIOM"}


def _fmt(x, dec=3, sufijo=""):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n. d."
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".") + sufijo


def _pct(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n. d."
    return ("+" if x > 0 else "") + _fmt(x, 1, " %")


def _fecha(s):
    return "—" if not s else f"{s[8:10]}/{s[5:7]}/{s[0:4]}"


# ------------------------------------------------------------------ gráficos (matplotlib)

def _series_df(id_: str) -> pd.DataFrame:
    ruta = DIR_SERIES / f"{id_}.csv"
    if not ruta.exists():
        return pd.DataFrame()
    df = pd.read_csv(ruta, dtype={"periodo": str})
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df.sort_values("fecha")


def _estilo_ejes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e6e4de", linewidth=0.8)
    ax.tick_params(labelsize=8, colors="#52514e")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))


def grafico_comparativo(desde: dt.date, hasta: dt.date) -> bytes:
    fig, ax = plt.subplots(figsize=(10.5, 5.2), dpi=150)
    for id_ in ORDEN:
        df = _series_df(id_)
        if df.empty:
            continue
        col, _ = columna_panel(id_)
        d = df[(df["fecha"] >= pd.Timestamp(desde)) & (df["fecha"] <= pd.Timestamp(hasta))]
        if TIPO[id_] == "escalon":
            # prolongar el último valor vigente hasta la fecha final
            prev = df[df["fecha"] < pd.Timestamp(desde)].tail(1)
            d = pd.concat([prev.assign(fecha=pd.Timestamp(desde)), d, d.tail(1).assign(fecha=pd.Timestamp(hasta))])
            ax.step(d["fecha"], d[col], where="post", color=COLORES[id_], linewidth=1.6,
                    linestyle="--" if id_ == "pellet_granel" else "-", label=INDICADORES[id_].nombre_corto)
        else:
            ax.plot(d["fecha"], d[col], color=COLORES[id_], linewidth=1.1, label=INDICADORES[id_].nombre_corto)
    _estilo_ejes(ax)
    ax.set_ylabel("€/kWh", fontsize=9, color="#52514e")
    ax.set_ylim(bottom=0)
    ax.legend(ncol=5, fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def grafico_individual(id_: str, desde: dt.date, hasta: dt.date) -> bytes:
    df = _series_df(id_)
    fig, ax = plt.subplots(figsize=(5.2, 3.0), dpi=150)
    ind = INDICADORES[id_]
    if not df.empty:
        d = df[(df["fecha"] >= pd.Timestamp(desde)) & (df["fecha"] <= pd.Timestamp(hasta))]
        if TIPO[id_] == "escalon":
            prev = df[df["fecha"] < pd.Timestamp(desde)].tail(1)
            d = pd.concat([prev.assign(fecha=pd.Timestamp(desde)), d, d.tail(1).assign(fecha=pd.Timestamp(hasta))])
            ax.step(d["fecha"], d["valor_original"], where="post", color=COLORES[id_], linewidth=1.6)
        else:
            ax.plot(d["fecha"], d["valor_original"], color=COLORES[id_], linewidth=1.0)
    else:
        ax.text(0.5, 0.5, "sin datos", ha="center", va="center", transform=ax.transAxes, color="#7a7873")
    _estilo_ejes(ax)
    ax.set_title(f"{ind.numero}. {ind.nombre_corto}", fontsize=9.5, loc="left", color="#0b0b0b")
    ax.set_ylabel(ind.unidad_original, fontsize=8, color="#52514e")
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


# ------------------------------------------------------------------ PDF

def generar_pdf(panel: dict, ruta: Path) -> Path:
    hoy = dt.date.fromisoformat(panel["fecha_referencia"])
    desde_periodo = hoy - dt.timedelta(days=6)
    semana = hoy.isocalendar()
    estilos = getSampleStyleSheet()
    normal = ParagraphStyle("n", parent=estilos["Normal"], fontSize=9, leading=12, alignment=TA_JUSTIFY)
    peq = ParagraphStyle("p", parent=normal, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#52514e"))
    h1 = ParagraphStyle("h1", parent=estilos["Title"], fontSize=18, leading=22, alignment=0, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=estilos["Heading2"], fontSize=12, leading=15, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#0b0b0b"))
    celda = ParagraphStyle("c", parent=normal, fontSize=7.8, leading=9.5, alignment=0)
    doc = SimpleDocTemplate(str(ruta), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title="Precios de la energía en España", author="Cuadro de mando de precios energéticos")
    ancho = A4[0] - 32 * mm
    el = []
    el.append(Paragraph("Precios de la energía en España", h1))
    el.append(Paragraph(f"Informe semanal n.º {semana.year}-{semana.week:02d} · periodo analizado: {desde_periodo:%d/%m/%Y} a {hoy:%d/%m/%Y} · "
                        f"generado el {dt.datetime.now():%d/%m/%Y %H:%M}", peq))
    el.append(Paragraph(f'Cuadro de mando interactivo: <a href="https://pablopardopazosgestan.github.io/cuadro-mando-precios-energia/" color="#2a78d6">pablopardopazosgestan.github.io/cuadro-mando-precios-energia</a>', peq))

    # Resumen ejecutivo: precios actuales y comparación entre energías
    el.append(Paragraph("Resumen ejecutivo", h2))
    coment = panel["comentario"]
    resumen_txt = [p for p in coment if p.startswith("Precio por kWh") or p.startswith("Precios mayoristas") or p.startswith("Sin precio")]
    evolucion_txt = [p for p in coment if p not in resumen_txt]
    for p in resumen_txt or ["Sin datos suficientes."]:
        el.append(Paragraph(p, normal))

    # Tabla de precios y variaciones
    el.append(Paragraph("Precios y variaciones", h2))
    cab = ["Indicador", "Precio actual (€/kWh)", "Variación semanal", "Variación interanual", "Fecha del dato", "Fuente", "Impuestos", "Estado"]
    filas = [[Paragraph(c.replace("\n", "<br/>"), celda) for c in cab]]
    for r in panel["resumen"]:
        filas.append([Paragraph(f"{r['numero']}. {r['nombre']}", celda),
                      _fmt(r["precio_eur_kwh"], 4 if r["id"] in ("omie", "mibgas") else 3),
                      _pct(r["variacion_semanal_pct"]), _pct(r["variacion_interanual_pct"]),
                      _fecha(r["fecha_dato"]), Paragraph(NOMBRE_FUENTE[r["id"]], celda),
                      Paragraph("sin (mayorista)" if r["impuestos"].startswith("sin") else "con", celda),
                      Paragraph(r["estado"], celda)])
    t = Table(filas, colWidths=[ancho * f for f in (0.27, 0.10, 0.09, 0.10, 0.09, 0.12, 0.09, 0.14)], repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7.8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#0b0b0b")), ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#dcdad4")),
        ("ALIGN", (1, 1), (4, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f6f3")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    el.append(t)
    el.append(Paragraph("Precio actual: media de los últimos 7 días (OMIE, MIBGAS, PVPC), última semana publicada (gasóleos) o valor vigente en la fecha de referencia "
                        "(TUR 2, butano, pellet). Variaciones frente a los 7 días, la semana o el valor vigente anteriores, y frente a lo mismo un año antes. "
                        "«n. d.»: no disponible (la fuente no lo da o no se puede calcular; nunca se estima).", peq))

    # Comentario de evolución
    el.append(Paragraph("Comentario de evolución", h2))
    for p in evolucion_txt or ["Sin variaciones calculables."]:
        el.append(Paragraph(p, normal))

    # Gráfico comparativo
    el.append(PageBreak())
    el.append(Paragraph("Comparativo en €/kWh desde enero de 2022", h2))
    el.append(Image(io.BytesIO(grafico_comparativo(INICIO_INFORME, hoy)), width=ancho, height=ancho * 5.2 / 10.5))
    el.append(Paragraph("OMIE y MIBGAS: precios mayoristas sin impuestos. Resto: con impuestos. Las líneas escalonadas son precios regulados o trimestrales, "
                        "que se mantienen hasta la siguiente revisión. Los huecos son periodos sin dato.", peq))

    # Gráficos individuales
    el.append(Paragraph("Evolución de cada indicador (unidad original)", h2))
    imgs = [Image(io.BytesIO(grafico_individual(id_, INICIO_INFORME, hoy)), width=ancho / 2 - 2 * mm, height=(ancho / 2 - 2 * mm) * 3.0 / 5.2) for id_ in ORDEN]
    filas_img = [imgs[i:i + 2] for i in range(0, len(imgs), 2)]
    if len(filas_img[-1]) == 1:
        filas_img[-1].append("")
    tg = Table(filas_img, colWidths=[ancho / 2, ancho / 2])
    tg.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    el.append(tg)

    # Fuentes y metodología
    el.append(PageBreak())
    el.append(Paragraph("Fuentes y metodología", h2))
    filas = [[Paragraph(c, celda) for c in ("Indicador", "Fuente", "Unidad y frecuencia", "Impuestos", "Conversión a €/kWh")]]
    for r in panel["resumen"]:
        m = panel["metadatos"].get(r["id"], {})
        filas.append([Paragraph(r["nombre"], celda), Paragraph(f'<a href="{r["url_fuente"]}" color="#2a78d6">{r["fuente"]}</a>', celda),
                      Paragraph(f"{r['unidad_original']}; {m.get('frecuencia', '')}", celda), Paragraph(m.get("impuestos_original", ""), celda),
                      Paragraph(m.get("conversion", ""), celda)])
    tf = Table(filas, colWidths=[ancho * f for f in (0.2, 0.26, 0.2, 0.14, 0.2)], repeatRows=1)
    tf.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#0b0b0b")), ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#dcdad4")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    el.append(tf)
    el.append(Spacer(1, 4 * mm))
    el.append(Paragraph("Factores de conversión (sobre poder calorífico inferior): " + "; ".join(
        f"{f['nombre']}: {_fmt(f['valor'], 3)} {f['unidad']} ({f['procedencia']})" for f in panel["factores"]) + ".", peq))
    el.append(Paragraph("Impuestos: se aplican los vigentes en cada fecha (IVA, impuesto especial sobre la electricidad e impuesto sobre hidrocarburos), con su "
                        "referencia al BOE; en 2026 varios tipos dependen del IPC del INE. Tabla completa en docs/METODOLOGIA.md del repositorio. "
                        "Los precios con impuestos de PVPC, TUR 2 y butano son calculados; los del Boletín Petrolero y AVEBIOM, originales de la fuente.", peq))
    estado = "; ".join(f"{k}: {'correcto' if f['estado'] == 'ok' else 'error (' + str(f.get('error', ''))[:80] + ')'}" for k, f in panel["fuentes"].items())
    el.append(Paragraph(f"Estado de las fuentes en la última actualización ({_fecha(panel['actualizado'] or '')}): {estado}.", peq))
    el.append(Paragraph(f"Cuadro de mando de precios energéticos en España, versión {__version__}. Código, datos y metodología: {URL_REPO}", peq))
    doc.build(el)
    return ruta


# ------------------------------------------------------------------ Excel

def generar_excel(panel: dict, ruta: Path) -> Path:
    wb = Workbook()
    negrita = Font(bold=True)
    cab_fill = PatternFill("solid", fgColor="F3F2EF")

    def cabecera(ws, fila, valores):
        for j, v in enumerate(valores, start=1):
            c = ws.cell(row=fila, column=j, value=v)
            c.font = negrita
            c.fill = cab_fill
            c.alignment = Alignment(wrap_text=True, vertical="top")

    def anchos(ws, lista):
        for j, a in enumerate(lista, start=1):
            ws.column_dimensions[get_column_letter(j)].width = a

    # Resumen
    ws = wb.active
    ws.title = "Resumen"
    ws["A1"] = "Precios de la energía en España: resumen ejecutivo"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Fecha de referencia: {_fecha(panel['fecha_referencia'])}. Última actualización: {panel['actualizado'] or ''}. Versión {__version__}."
    cabecera(ws, 4, ["N.º", "Indicador", "Precio actual (€/kWh)", "Impuestos", "Base del precio", "Variación semanal (%)", "Variación interanual (%)",
                     "Fecha del dato", "Valor original", "Unidad original", "Fuente", "Estado", "Detalle"])
    for i, r in enumerate(panel["resumen"], start=5):
        ws.append([r["numero"], r["nombre"], r["precio_eur_kwh"], r["impuestos"], r["base_precio"], r["variacion_semanal_pct"], r["variacion_interanual_pct"],
                   r["fecha_dato"], r["valor_original"], r["unidad_original"], r["fuente"], r["estado"], r["detalle_estado"]])
        ws.cell(row=i, column=3).number_format = "0.0000"
        ws.cell(row=i, column=6).number_format = "+0.0;-0.0;0.0"
        ws.cell(row=i, column=7).number_format = "+0.0;-0.0;0.0"
    ws.auto_filter.ref = f"A4:M{4 + len(panel['resumen'])}"
    ws.freeze_panes = "A5"
    anchos(ws, [5, 48, 14, 22, 40, 12, 12, 12, 12, 18, 40, 28, 50])
    fila = 6 + len(panel["resumen"])
    ws.cell(row=fila, column=1, value="Comentario semanal (generado a partir de los datos)").font = negrita
    for k, p in enumerate(panel["comentario"], start=fila + 1):
        ws.cell(row=k, column=1, value=p)

    # Mensual (fuente de los gráficos)
    wm = wb.create_sheet("Mensual")
    meses = sorted({m for id_ in ORDEN for m in panel["mensual"].get(id_, {}).get("meses", [])})
    cab = ["Mes"]
    for id_ in ORDEN:
        ind = INDICADORES[id_]
        cab += [f"{ind.nombre_corto} (€/kWh{', sin imp.' if id_ in ('omie', 'mibgas') else ', con imp.'})", f"{ind.nombre_corto} ({ind.unidad_original})"]
    cabecera(wm, 1, cab)
    idx = {}
    for id_ in ORDEN:
        m = panel["mensual"].get(id_, {})
        col_kwh = m.get("media_eur_kwh_sin") if id_ in ("omie", "mibgas") else m.get("media_eur_kwh_con")
        idx[id_] = {mes: (k, o) for mes, k, o in zip(m.get("meses", []), col_kwh or [], m.get("media_original", []))}
    for i, mes in enumerate(meses, start=2):
        fila_v = [mes]
        for id_ in ORDEN:
            k, o = idx[id_].get(mes, (None, None))
            fila_v += [k, o]
        wm.append(fila_v)
    for j in range(2, len(cab) + 1):
        for i in range(2, len(meses) + 2):
            wm.cell(row=i, column=j).number_format = "0.0000" if j % 2 == 0 else "0.00"
    wm.auto_filter.ref = f"A1:{get_column_letter(len(cab))}{len(meses) + 1}"
    wm.freeze_panes = "B2"
    anchos(wm, [10] + [16] * (len(cab) - 1))

    # Gráficos vinculados a la hoja Mensual
    wg = wb.create_sheet("Gráficos")
    wg["A1"] = "Gráficos vinculados a la hoja «Mensual» (medias mensuales)"
    wg["A1"].font = Font(bold=True, size=12)
    n = len(meses) + 1
    ch = LineChart()
    ch.title = "Comparativo en €/kWh (media mensual)"
    ch.y_axis.title = "€/kWh"
    ch.height, ch.width = 9, 26
    for k, id_ in enumerate(ORDEN):
        col = 2 + 2 * k
        ch.add_data(Reference(wm, min_col=col, min_row=1, max_row=n), titles_from_data=True)
    ch.set_categories(Reference(wm, min_col=1, min_row=2, max_row=n))
    for k, s in enumerate(ch.series):
        s.graphicalProperties.line.solidFill = COLORES[ORDEN[k]].lstrip("#")
        s.graphicalProperties.line.width = 15000
        s.smooth = False
        if ORDEN[k] == "pellet_granel":
            s.graphicalProperties.line.dashStyle = "dash"
    wg.add_chart(ch, "A3")
    fila_g = 23
    for k, id_ in enumerate(ORDEN):
        ind = INDICADORES[id_]
        c = LineChart()
        c.title = f"{ind.numero}. {ind.nombre_corto} ({ind.unidad_original}, media mensual)"
        c.y_axis.title = ind.unidad_original
        c.height, c.width = 7, 12.5
        c.legend = None
        c.add_data(Reference(wm, min_col=3 + 2 * k, min_row=1, max_row=n), titles_from_data=True)
        c.set_categories(Reference(wm, min_col=1, min_row=2, max_row=n))
        c.series[0].graphicalProperties.line.solidFill = COLORES[id_].lstrip("#")
        c.series[0].graphicalProperties.line.width = 15000
        c.series[0].smooth = False
        wg.add_chart(c, f"{'A' if k % 2 == 0 else 'I'}{fila_g + 15 * (k // 2)}")

    # Una hoja por serie con el histórico completo en su frecuencia original
    for id_ in ORDEN:
        ind = INDICADORES[id_]
        ws = wb.create_sheet(f"{ind.numero}_{id_}"[:31])
        ws["A1"] = f"{ind.numero}. {ind.nombre}"
        ws["A1"].font = Font(bold=True, size=12)
        ws["A2"] = f"Fuente: {ind.fuente}. Unidad original: {ind.unidad_original}. Frecuencia: {ind.frecuencia}. Impuestos del dato original: {ind.impuestos_original}. Conversión: {ind.conversion}"
        ws["A2"].alignment = Alignment(wrap_text=False)
        df = _series_df(id_)
        cols = ["fecha", "periodo", "valor_original", "unidad_original", "eur_kwh_sin_impuestos", "eur_kwh_con_impuestos", "con_impuestos_origen",
                "impuestos_detalle", "impuestos_pendiente", "fecha_publicacion", "referencia", "nota"]
        cabecera(ws, 4, ["Fecha", "Periodo", "Valor original", "Unidad", "€/kWh sin impuestos", "€/kWh con impuestos", "Origen del precio con impuestos",
                         "Impuestos aplicados", "Pendiente", "Fecha de publicación", "Referencia (fichero / BOE / PDF)", "Nota"])
        for _, f in df.iterrows():
            ws.append([f["fecha"].date() if hasattr(f["fecha"], "date") else f["fecha"]] + [None if (isinstance(f[c], float) and pd.isna(f[c])) else f[c] for c in cols[1:]])
        for i in range(5, 5 + len(df)):
            ws.cell(row=i, column=1).number_format = "DD/MM/YYYY"
            ws.cell(row=i, column=3).number_format = "0.0000"
            ws.cell(row=i, column=5).number_format = "0.000000"
            ws.cell(row=i, column=6).number_format = "0.000000"
        ws.auto_filter.ref = f"A4:L{4 + max(len(df), 1)}"
        ws.freeze_panes = "A5"
        anchos(ws, [12, 10, 12, 16, 12, 12, 22, 50, 30, 14, 28, 50])

    # Fuentes y criterios
    wf = wb.create_sheet("Fuentes y criterios")
    cabecera(wf, 1, ["N.º", "Indicador", "Fuente", "Dirección", "Unidad original", "Frecuencia", "Impuestos del dato original", "Conversión a €/kWh", "Nota"])
    for id_ in ORDEN:
        ind = INDICADORES[id_]
        wf.append([ind.numero, ind.nombre, ind.fuente, ind.url_fuente, ind.unidad_original, ind.frecuencia, ind.impuestos_original, ind.conversion, ind.nota])
    fila = len(ORDEN) + 3
    wf.cell(row=fila, column=1, value="Factores de conversión (PCI)").font = negrita
    for k, f in enumerate(panel["factores"], start=fila + 1):
        wf.append([None, f["nombre"], f["valor"], f["unidad"], f["procedencia"]])
    fila = fila + len(panel["factores"]) + 2
    wf.cell(row=fila, column=1, value="Criterios").font = negrita
    criterios = [
        "Nada se rellena ni se estima: si la fuente no da un dato, la celda queda vacía.",
        "Datos originales (valor_original) frente a calculados (precio con impuestos de PVPC, TUR 2 y butano). El Boletín Petrolero y AVEBIOM publican ya con impuestos.",
        "Impuestos vigentes en cada fecha, con referencia al BOE en la columna «Impuestos aplicados»; en 2026 varios tipos dependen del IPC del INE.",
        "Medias mensuales: media aritmética de los datos del mes (diarios/semanales); valor vigente ponderado por días (TUR 2, butano); valor del periodo (pellet).",
        "OMIE y MIBGAS son precios mayoristas y se muestran sin impuestos.",
        f"Metodología completa y tabla de impuestos: {URL_REPO}/blob/main/docs/METODOLOGIA.md",
    ]
    for k, c in enumerate(criterios, start=fila + 1):
        wf.cell(row=k, column=1, value=c)
    anchos(wf, [5, 45, 50, 50, 16, 40, 30, 60, 60])
    wb.save(ruta)
    return ruta


def generar(hoy: dt.date | None = None) -> list[Path]:
    panel = construir(hoy)
    DIR_INFORMES.mkdir(parents=True, exist_ok=True)
    salidas = [generar_pdf(panel, DIR_INFORMES / "informe.pdf"), generar_excel(panel, DIR_INFORMES / "historico.xlsx")]
    return salidas
