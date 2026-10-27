"""Informes descargables para dirección: `sitio/informes/informe.pdf` y `sitio/informes/historico.xlsx`.

Se generan en cada actualización con los mismos datos que el cuadro de mando (`panel.construir`).
- PDF (4 páginas): 1) cuadro de mando de una página: ocho indicadores en tarjetas con precio, variaciones con
  color, fecha y tendencia de 24 meses; ranking visual del coste por kWh; claves de la semana. 2) Tabla de precios
  y variaciones y comparativo en €/kWh desde 2022. 3) Nueve gráficos individuales con el último valor anotado.
  4) Fuentes, metodología y estado de las fuentes.
- Excel: «Cuadro de mando» (tarjeta resumen con formato condicional y dos gráficos), «Anual» y «Mensual» (medias),
  «Gráficos» (vinculados a los datos), una hoja de datos por serie en formato tabla (filtrable) y «Fuentes y
  criterios».
Todo texto numérico se formatea a la española y nada se estima: los datos no disponibles aparecen como «n. d.».
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.chart import BarChart, LineChart, Reference  # noqa: E402
from openpyxl.formatting.rule import CellIsRule, IconSetRule  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402
from openpyxl.worksheet.table import Table as TablaExcel, TableStyleInfo  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from . import __version__  # noqa: E402
from .config import DIR_SERIES  # noqa: E402
from .indicadores import INDICADORES, ORDEN  # noqa: E402
from .panel import COLORES, DIR_SITIO, TIPO, URL_REPO, columna_panel, construir  # noqa: E402

log = logging.getLogger(__name__)

DIR_INFORMES = DIR_SITIO / "informes"
INICIO_INFORME = dt.date(2022, 1, 1)
URL_PANEL = "https://pablopardopazosgestan.github.io/cuadro-mando-precios-energia/"
NOMBRE_FUENTE = {"omie": "OMIE", "mibgas": "MIBGAS", "gasoleo_a": "Comisión Europea (WOB)", "gasoleo_c": "Comisión Europea (WOB)",
                 "pvpc": "REE/ESIOS", "tur2": "BOE (DGPEM)", "butano": "BOE (DGPEM)", "pellet_saco": "AVEBIOM", "pellet_granel": "AVEBIOM"}
TINTA, TINTA2, TINTA3 = "#0b0b0b", "#52514e", "#8f8e86"
SUPERFICIE, BORDE, ACENTO = "#f3f2ef", "#dcdad4", "#2a78d6"
SUBE, BAJA = "#d03b3b", "#0ca30c"   # para el consumidor, subir es malo (rojo) y bajar es bueno (verde)


# ------------------------------------------------------------------ utilidades de formato

def _fmt(x, dec=3, sufijo=""):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n. d."
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".") + sufijo


def _pct(x, flecha=True):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n. d."
    signo = "▲\u00a0" if x > 0.05 else ("▼\u00a0" if x < -0.05 else "■\u00a0")
    return (signo if flecha else "") + ("+" if x > 0 else "") + _fmt(x, 1, "\u00a0%")


def _color_var(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return TINTA3
    return SUBE if x > 0.05 else (BAJA if x < -0.05 else TINTA2)


def _fecha(s):
    return "—" if not s else f"{s[8:10]}/{s[5:7]}/{s[0:4]}"


def _registrar_fuentes() -> tuple[str, str]:
    """Registra DejaVu Sans (viene con matplotlib, así que está en cualquier instalación) para tener € y flechas."""
    if "DejaVuSans" not in pdfmetrics.getRegisteredFontNames():
        base = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
        pdfmetrics.registerFont(TTFont("DejaVuSans", str(base / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(base / "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFontFamily("DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold", italic="DejaVuSans", boldItalic="DejaVuSans-Bold")
    return "DejaVuSans", "DejaVuSans-Bold"


# ------------------------------------------------------------------ datos auxiliares

def _series_df(id_: str) -> pd.DataFrame:
    ruta = DIR_SERIES / f"{id_}.csv"
    if not ruta.exists():
        return pd.DataFrame()
    df = pd.read_csv(ruta, dtype={"periodo": str})
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df.sort_values("fecha")


def _mensual_kwh(panel: dict, id_: str) -> tuple[list[str], list[float | None]]:
    m = panel["mensual"].get(id_, {})
    return m.get("meses", []), (m.get("media_eur_kwh_sin") if id_ in ("omie", "mibgas") else m.get("media_eur_kwh_con")) or []


def _anual(panel: dict) -> dict[str, dict[str, float | None]]:
    """Medias anuales en €/kWh por serie a partir de las medias mensuales (solo años con 12 meses, salvo el actual)."""
    out: dict[str, dict[str, float | None]] = {}
    anyo_actual = panel["fecha_referencia"][:4]
    for id_ in ORDEN:
        meses, vals = _mensual_kwh(panel, id_)
        por_anyo: dict[str, list[float]] = {}
        completos: dict[str, int] = {}
        for mes, v in zip(meses, vals):
            a = mes[:4]
            completos[a] = completos.get(a, 0) + 1
            if v is not None:
                por_anyo.setdefault(a, []).append(v)
        out[id_] = {a: (sum(v) / len(v) if (len(v) == completos[a] and (completos[a] == 12 or a == anyo_actual)) else None)
                    for a, v in por_anyo.items()}
    return out


# ------------------------------------------------------------------ gráficos (matplotlib)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": BORDE, "axes.labelcolor": TINTA2,
                     "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.titlecolor": TINTA})


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    return buf.getvalue()


def _estilo(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e6e4de", linewidth=0.7)
    ax.set_axisbelow(True)


def sparkline(panel: dict, id_: str, meses_n: int = 24) -> bytes:
    meses, vals = _mensual_kwh(panel, id_)
    fig, ax = plt.subplots(figsize=(2.2, 0.55), dpi=160)
    pares = [(m, v) for m, v in zip(meses, vals)][-meses_n:]
    xs = [pd.Timestamp(m + "-15") for m, _ in pares]
    ys = [v if v is not None else float("nan") for _, v in pares]
    if TIPO[id_] == "escalon":
        ax.step(xs, ys, where="post", color=COLORES[id_], linewidth=1.3)
    else:
        ax.plot(xs, ys, color=COLORES[id_], linewidth=1.3)
    ultimo = next((v for v in reversed(ys) if v == v), None)
    if ultimo is not None:
        ax.plot([xs[-1]], [ultimo], "o", color=COLORES[id_], markersize=3)
    ax.axis("off")
    fig.subplots_adjust(0, 0.05, 1, 0.95)
    return _png(fig)


def grafico_ranking(resumen: list[dict]) -> bytes:
    finales = sorted([r for r in resumen if r["id"] not in ("omie", "mibgas") and r["precio_eur_kwh"] is not None], key=lambda r: r["precio_eur_kwh"])
    fig, ax = plt.subplots(figsize=(6.2, 2.5), dpi=160)
    nombres = [r["nombre_corto"] for r in finales]
    plt.rcParams.update({"font.size": 8})
    valores = [r["precio_eur_kwh"] for r in finales]
    barras = ax.barh(nombres, valores, color=[COLORES[r["id"]] for r in finales], height=0.62)
    for b, v in zip(barras, valores):
        ax.text(b.get_width() + max(valores) * 0.01, b.get_y() + b.get_height() / 2, _fmt(v, 3) + " €/kWh", va="center", fontsize=7.5, color=TINTA)
    ax.set_xlim(0, max(valores) * 1.28 if valores else 1)
    ax.invert_yaxis()
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.tick_params(axis="x", bottom=False, labelbottom=False)
    ax.tick_params(axis="y", length=0, labelsize=8)
    ax.set_title("Coste por kWh de la energía final, con impuestos (de menor a mayor)", loc="left", fontsize=8.5)
    fig.tight_layout()
    return _png(fig)


def grafico_comparativo(desde: dt.date, hasta: dt.date) -> bytes:
    fig, ax = plt.subplots(figsize=(10.5, 4.6), dpi=160)
    for id_ in ORDEN:
        df = _series_df(id_)
        if df.empty:
            continue
        col, _ = columna_panel(id_)
        d = df[(df["fecha"] >= pd.Timestamp(desde)) & (df["fecha"] <= pd.Timestamp(hasta))]
        etiqueta = INDICADORES[id_].nombre_corto + (" (sin imp.)" if id_ in ("omie", "mibgas") else "")
        if TIPO[id_] == "escalon":
            prev = df[df["fecha"] < pd.Timestamp(desde)].tail(1)
            d = pd.concat([prev.assign(fecha=pd.Timestamp(desde)), d, d.tail(1).assign(fecha=pd.Timestamp(hasta))])
            ax.step(d["fecha"], d[col], where="post", color=COLORES[id_], linewidth=1.7, linestyle="--" if id_ == "pellet_granel" else "-", label=etiqueta)
        else:
            ax.plot(d["fecha"], d[col], color=COLORES[id_], linewidth=1.0, label=etiqueta, alpha=0.95)
    _estilo(ax)
    ax.set_ylabel("€/kWh")
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    ax.legend(ncol=5, fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    return _png(fig)


def grafico_individual(id_: str, desde: dt.date, hasta: dt.date) -> bytes:
    df = _series_df(id_)
    ind = INDICADORES[id_]
    fig, ax = plt.subplots(figsize=(3.6, 2.2), dpi=160)
    if not df.empty:
        d = df[(df["fecha"] >= pd.Timestamp(desde)) & (df["fecha"] <= pd.Timestamp(hasta))]
        if TIPO[id_] == "escalon":
            prev = df[df["fecha"] < pd.Timestamp(desde)].tail(1)
            d = pd.concat([prev.assign(fecha=pd.Timestamp(desde)), d, d.tail(1).assign(fecha=pd.Timestamp(hasta))])
            ax.step(d["fecha"], d["valor_original"], where="post", color=COLORES[id_], linewidth=1.5)
        else:
            ax.plot(d["fecha"], d["valor_original"], color=COLORES[id_], linewidth=0.9)
        ult = df.iloc[-1]
        ax.annotate(_fmt(float(ult["valor_original"]), 2), xy=(pd.Timestamp(hasta), float(ult["valor_original"])), xytext=(-2, 4),
                    textcoords="offset points", ha="right", fontsize=7.5, color=TINTA, fontweight="bold")
    else:
        ax.text(0.5, 0.5, "sin datos", ha="center", va="center", transform=ax.transAxes, color=TINTA3)
    _estilo(ax)
    ax.set_title(f"{ind.numero}. {ind.nombre_corto}", loc="left", fontsize=8.5, fontweight="bold")
    ax.set_ylabel(ind.unidad_original, fontsize=7)
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    return _png(fig)


# ------------------------------------------------------------------ PDF

def generar_pdf(panel: dict, ruta: Path) -> Path:
    fn, fb = _registrar_fuentes()
    hoy = dt.date.fromisoformat(panel["fecha_referencia"])
    desde_periodo = hoy - dt.timedelta(days=6)
    semana = hoy.isocalendar()
    titulo_corto = f"Semana {semana.year}-{semana.week:02d} · {desde_periodo:%d/%m} – {hoy:%d/%m/%Y}"

    def st(nombre, **kw):
        base = dict(fontName=fn, fontSize=9, leading=12, textColor=colors.HexColor(TINTA))
        base.update(kw)
        return ParagraphStyle(nombre, **base)

    normal = st("n", alignment=TA_JUSTIFY)
    peq = st("p", fontSize=7.2, leading=9.2, textColor=colors.HexColor(TINTA2))
    h1 = st("h1", fontName=fb, fontSize=20, leading=24)
    h2 = st("h2", fontName=fb, fontSize=12.5, leading=15, spaceBefore=8, spaceAfter=5)
    celda = st("c", fontSize=7.6, leading=9.4)
    celda_b = st("cb", fontName=fb, fontSize=7.6, leading=9.4)
    celda_r = st("cr", fontSize=7.6, leading=9.4, alignment=TA_RIGHT)
    kpi_nombre = st("kn", fontName=fb, fontSize=8.2, leading=10)
    kpi_valor = st("kv", fontName=fb, fontSize=17, leading=19)
    kpi_unidad = st("ku", fontSize=7, leading=9, textColor=colors.HexColor(TINTA2))
    kpi_var = st("kvar", fontSize=7.6, leading=9.6)
    kpi_meta = st("km", fontSize=6.6, leading=8.4, textColor=colors.HexColor(TINTA3))

    ancho = A4[0] - 28 * mm

    def cabecera_pie(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(ACENTO))
        canvas.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
        canvas.setFont(fb, 8.5)
        canvas.setFillColor(colors.HexColor(TINTA2))
        canvas.drawString(14 * mm, A4[1] - 12.5 * mm, "Precios de la energía en España · informe semanal")
        canvas.setFont(fn, 8.5)
        canvas.drawRightString(A4[0] - 14 * mm, A4[1] - 12.5 * mm, titulo_corto)
        canvas.setStrokeColor(colors.HexColor(BORDE))
        canvas.line(14 * mm, A4[1] - 14.5 * mm, A4[0] - 14 * mm, A4[1] - 14.5 * mm)
        canvas.setFont(fn, 7)
        canvas.setFillColor(colors.HexColor(TINTA3))
        canvas.drawString(14 * mm, 9 * mm, f"Fuentes: OMIE, MIBGAS, REE/ESIOS, Comisión Europea, BOE y AVEBIOM; impuestos según BOE e INE. Generado el {dt.datetime.now():%d/%m/%Y %H:%M}.")
        canvas.drawRightString(A4[0] - 14 * mm, 9 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(ruta), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=19 * mm, bottomMargin=15 * mm,
                            title="Precios de la energía en España · informe semanal", author="Cuadro de mando de precios energéticos")
    el = []
    resumen = {r["id"]: r for r in panel["resumen"]}

    # ---------- Página 1: cuadro de mando
    el.append(Paragraph("Precios de la energía en España", h1))
    el.append(Paragraph(f"Informe semanal n.º {semana.year}-{semana.week:02d} · periodo analizado del {desde_periodo:%d/%m/%Y} al {hoy:%d/%m/%Y} · "
                        f"ocho indicadores en €/kWh, con impuestos salvo los mercados mayoristas (OMIE y MIBGAS).", peq))
    el.append(Spacer(1, 3 * mm))

    def tarjeta(id_, extra_id=None):
        r = resumen[id_]
        precio = _fmt(r["precio_eur_kwh"], 4 if id_ in ("omie", "mibgas") else 3)
        sem, inter = r["variacion_semanal_pct"], r["variacion_interanual_pct"]
        var = (f'Semana: <font color="{_color_var(sem)}">{_pct(sem)}</font><br/>'
               f'Un año: <font color="{_color_var(inter)}">{_pct(inter)}</font>')
        extra = ""
        if extra_id:
            e = resumen[extra_id]
            extra = (f'<br/>{e["nombre_corto"]}: <b>{_fmt(e["precio_eur_kwh"], 3)}</b> €/kWh '
                     f'(<font color="{_color_var(e["variacion_semanal_pct"])}">{_pct(e["variacion_semanal_pct"])}</font> semana, '
                     f'<font color="{_color_var(e["variacion_interanual_pct"])}">{_pct(e["variacion_interanual_pct"])}</font> año)')
        etiqueta = "mayorista, sin impuestos" if r["impuestos"].startswith("sin") else "con impuestos"
        meta = f"{NOMBRE_FUENTE[id_]} · dato del {_fecha(r['fecha_dato'])} · {etiqueta}"
        if r["precio_eur_kwh"] is None:
            meta += f" · {r['detalle_estado'] or r['estado']}"
        izq = [Paragraph(f"{r['numero']}. {r['nombre_corto']}", kpi_nombre),
               Paragraph(f'{precio} <font size="7" color="{TINTA2}">€/kWh</font>', kpi_valor),
               Paragraph(var + extra, kpi_var), Paragraph(meta, kpi_meta)]
        der = Image(io.BytesIO(sparkline(panel, id_)), width=34 * mm, height=8.5 * mm)
        t = Table([[izq, der]], colWidths=[(ancho / 2 - 4 * mm) - 36 * mm, 36 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                               ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(SUPERFICIE)),
                               ("LINEBEFORE", (0, 0), (0, 0), 2.2, colors.HexColor(COLORES[id_])),
                               ("LEFTPADDING", (0, 0), (0, 0), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        return t

    tarjetas = [tarjeta("omie"), tarjeta("mibgas"), tarjeta("gasoleo_a"), tarjeta("pvpc"),
                tarjeta("tur2"), tarjeta("gasoleo_c"), tarjeta("butano"), tarjeta("pellet_saco", "pellet_granel")]
    cuadricula = Table([tarjetas[i:i + 2] for i in range(0, 8, 2)], colWidths=[ancho / 2, ancho / 2])
    cuadricula.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                                    ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    el.append(cuadricula)
    el.append(Paragraph("Precio actual: media de los últimos 7 días (OMIE, MIBGAS, PVPC), última semana publicada (gasóleos) o valor vigente hoy "
                        "(TUR 2, butano, pellet). Variaciones frente al periodo anterior y frente a hace un año. Línea: tendencia de las medias "
                        "mensuales de los últimos 24 meses. ▲ sube, ▼ baja, ■ sin cambio; n. d.: no disponible (nunca se estima).", peq))
    el.append(Spacer(1, 3 * mm))

    el.append(Image(io.BytesIO(grafico_ranking(panel["resumen"])), width=ancho * 0.72, height=ancho * 0.72 * 2.5 / 6.2, hAlign="LEFT"))
    el.append(Paragraph("Claves de la semana", h2))
    for p in panel["comentario"]:
        el.append(Paragraph("• " + p, normal))

    # ---------- Página 2: tabla y comparativo
    el.append(PageBreak())
    el.append(Paragraph("Precios y variaciones", h2))
    cab = ["Indicador", "€/kWh", "Semana", "Un año", "Fecha", "Valor original", "Fuente", "Estado"]
    filas = [[Paragraph(c, celda_b) for c in cab]]
    estilo_t = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(SUPERFICIE)), ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(TINTA)),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor(BORDE)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    for i, r in enumerate(panel["resumen"], start=1):
        sem, inter = r["variacion_semanal_pct"], r["variacion_interanual_pct"]
        punto = {"actualizado": BAJA, "sin actualización en el periodo": "#c98500"}.get(r["estado"], SUBE)
        filas.append([Paragraph(f"{r['numero']}. {r['nombre']}" + (" <font color='%s'>(sin impuestos)</font>" % TINTA3 if r["impuestos"].startswith("sin") else ""), celda),
                      Paragraph(f"<b>{_fmt(r['precio_eur_kwh'], 4 if r['id'] in ('omie', 'mibgas') else 3)}</b>", celda_r),
                      Paragraph(f'<font color="{_color_var(sem)}">{_pct(sem)}</font>', celda_r),
                      Paragraph(f'<font color="{_color_var(inter)}">{_pct(inter)}</font>', celda_r),
                      Paragraph(_fecha(r["fecha_dato"]).replace("/20", "/"), celda),
                      Paragraph(f"{_fmt(r['valor_original'], 2 if r['valor_original'] and r['valor_original'] > 10 else 4)} {r['unidad_original'].split(' (')[0]}", celda),
                      Paragraph(NOMBRE_FUENTE[r["id"]], celda),
                      Paragraph(f'<font color="{punto}">●</font> {r["estado"]}', celda)])
    t = Table(filas, colWidths=[ancho * f for f in (0.24, 0.09, 0.10, 0.10, 0.08, 0.13, 0.10, 0.16)], repeatRows=1)
    t.setStyle(TableStyle(estilo_t))
    el.append(t)
    el.append(Paragraph("Estado: ● actualizado (dato nuevo en los últimos 7 días); ● sin actualización en el periodo (la fuente publica con menor frecuencia); "
                        "● fuente no disponible o dato pendiente. Los precios con impuestos de PVPC, TUR 2 y butano son calculados con los tipos vigentes en cada "
                        "fecha; los del Boletín Petrolero y AVEBIOM, originales de la fuente.", peq))
    el.append(Paragraph("Comparativo en €/kWh desde enero de 2022", h2))
    el.append(Image(io.BytesIO(grafico_comparativo(INICIO_INFORME, hoy)), width=ancho, height=ancho * 4.6 / 10.5))
    el.append(Paragraph("Las líneas escalonadas son precios regulados o trimestrales, que se mantienen hasta la siguiente revisión. Los huecos son periodos sin dato.", peq))

    # ---------- Página 3: gráficos individuales
    el.append(PageBreak())
    el.append(Paragraph("Evolución de cada indicador desde 2022 (unidad original de la fuente; último valor anotado)", h2))
    w = ancho / 3 - 2 * mm
    imgs = [Image(io.BytesIO(grafico_individual(id_, INICIO_INFORME, hoy)), width=w, height=w * 2.2 / 3.6) for id_ in ORDEN]
    tg = Table([imgs[i:i + 3] for i in range(0, 9, 3)], colWidths=[ancho / 3] * 3)
    tg.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    el.append(tg)
    anual = _anual(panel)
    anyos = sorted({a for d in anual.values() for a in d})[-5:]
    el.append(Paragraph("Media anual en €/kWh", h2))
    filas = [[Paragraph("Indicador", celda_b)] + [Paragraph(a + ("*" if a == panel["fecha_referencia"][:4] else ""), celda_b) for a in anyos]]
    for id_ in ORDEN:
        filas.append([Paragraph(INDICADORES[id_].nombre_corto + (" (sin imp.)" if id_ in ("omie", "mibgas") else ""), celda)] +
                     [Paragraph(_fmt(anual[id_].get(a), 4 if id_ in ("omie", "mibgas") else 3), celda_r) for a in anyos])
    ta = Table(filas, colWidths=[ancho * 0.3] + [ancho * 0.7 / len(anyos)] * len(anyos))
    ta.setStyle(TableStyle(estilo_t))
    el.append(ta)
    el.append(Paragraph("* Año en curso: media de los meses disponibles. Los años sin dato en alguno de sus meses se dejan en blanco.", peq))

    # ---------- Página 4: estado de las fuentes y metodología
    el.append(PageBreak())
    el.append(Paragraph("Estado de las fuentes en la última actualización", h2))
    nombres_fuente = {"omie": "OMIE", "mibgas": "MIBGAS", "boletin_petrolero": "Comisión Europea (Weekly Oil Bulletin)", "esios_pvpc": "REE / ESIOS",
                      "boe_tur": "BOE (TUR gas natural)", "boe_butano": "BOE (butano envasado)", "avebiom": "AVEBIOM", "ine_ipc": "INE (IPC, impuestos de 2026)"}
    filas = [[Paragraph(c, celda_b) for c in ("Fuente", "Resultado", "Último dato", "Última descarga correcta")]]
    for k, f in panel["fuentes"].items():
        ult = max((s_.get("ultimo_dato") or "" for s_ in (f.get("series") or {}).values()), default="")
        ok = f.get("estado") == "ok"
        filas.append([Paragraph(nombres_fuente.get(k, k), celda),
                      Paragraph(f'<font color="{BAJA if ok else SUBE}">●</font> ' + ("correcto" if ok else "error: " + str(f.get("error", ""))[:90]), celda),
                      Paragraph(_fecha(ult) if ult else "—", celda), Paragraph(_fecha((f.get("ultima_actualizacion_correcta") or "")[:10]), celda)])
    te = Table(filas, colWidths=[ancho * f for f in (0.32, 0.38, 0.14, 0.16)])
    te.setStyle(TableStyle(estilo_t))
    el.append(te)
    el.append(Paragraph("La actualización es automática cada lunes y puede lanzarse a mano desde el repositorio. Si una fuente falla se conserva su último dato correcto y el error queda registrado.", peq))
    el.append(Paragraph("Fuentes y metodología", h2))
    celda_p = st("cp", fontSize=7, leading=8.6)
    filas = [[Paragraph(c, celda_b) for c in ("Indicador", "Fuente (enlace)", "Unidad y frecuencia", "Impuestos", "Conversión a €/kWh")]]
    for r in panel["resumen"]:
        m = panel["metadatos"].get(r["id"], {})
        filas.append([Paragraph(r["nombre"], celda_p), Paragraph(f'<a href="{r["url_fuente"]}" color="{ACENTO}">{r["fuente"]}</a>', celda_p),
                      Paragraph(f"{r['unidad_original']}; {m.get('frecuencia', '')}", celda_p), Paragraph(m.get("impuestos_original", ""), celda_p),
                      Paragraph(m.get("conversion", ""), celda_p)])
    tf = Table(filas, colWidths=[ancho * f for f in (0.19, 0.27, 0.2, 0.14, 0.2)], repeatRows=1)
    tf.setStyle(TableStyle(estilo_t + [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    el.append(tf)
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph("<b>Factores de conversión</b> (sobre poder calorífico inferior): " + "; ".join(
        f"{f['nombre']}: {_fmt(f['valor'], 3)} {f['unidad']}" for f in panel["factores"]) + ". Procedencia: IDAE (gasóleo, butano, PCI/PCS del gas natural) y boletín de referencia (pellet; AVEBIOM usa 4,76 kWh/kg).", peq))
    el.append(Paragraph("<b>Impuestos:</b> se aplican los vigentes en cada fecha (IVA, impuesto especial sobre la electricidad e impuesto sobre hidrocarburos) con su "
                        "referencia al BOE; en 2026 varios tipos dependen del IPC del INE. Tabla completa en docs/METODOLOGIA.md del repositorio.", peq))
    el.append(Paragraph("<b>Criterios:</b> nada se rellena ni se estima; cada dato conserva su fuente, fecha de publicación y si es original o calculado. "
                        "OMIE y MIBGAS son precios mayoristas y se presentan sin impuestos. Pellet: trimestral desde el 4T2024, medias anuales de AVEBIOM antes.", peq))
    el.append(Paragraph(f"Cuadro de mando interactivo con filtros de periodo y descarga del Excel: {URL_PANEL} · Código, datos y metodología: {URL_REPO} · Versión {__version__}.", peq))
    doc.build(el, onFirstPage=cabecera_pie, onLaterPages=cabecera_pie)
    return ruta


# ------------------------------------------------------------------ Excel

def generar_excel(panel: dict, ruta: Path) -> Path:
    wb = Workbook()
    fuente_titulo = Font(name="Calibri", bold=True, size=16, color="0B0B0B")
    fuente_h2 = Font(name="Calibri", bold=True, size=12, color="0B0B0B")
    fuente_cab = Font(name="Calibri", bold=True, color="FFFFFF")
    fill_cab = PatternFill("solid", fgColor="2A78D6")
    fill_suave = PatternFill("solid", fgColor="F3F2EF")
    gris = Font(name="Calibri", size=9, color="52514E")
    borde_fino = Border(bottom=Side(style="thin", color="DCDAD4"))

    def cabecera(ws, fila, valores, col_ini=1):
        for j, v in enumerate(valores, start=col_ini):
            c = ws.cell(row=fila, column=j, value=v)
            c.font = fuente_cab
            c.fill = fill_cab
            c.alignment = Alignment(wrap_text=True, vertical="center")

    def anchos(ws, lista):
        for j, a in enumerate(lista, start=1):
            ws.column_dimensions[get_column_letter(j)].width = a

    def tabla(ws, ref, nombre, estilo="TableStyleMedium2"):
        t = TablaExcel(displayName=nombre, ref=ref)
        t.tableStyleInfo = TableStyleInfo(name=estilo, showRowStripes=True)
        ws.add_table(t)

    # ---------- Cuadro de mando
    ws = wb.active
    ws.title = "Cuadro de mando"
    ws.sheet_view.showGridLines = False
    hoy = panel["fecha_referencia"]
    ws["B2"] = "Precios de la energía en España"
    ws["B2"].font = fuente_titulo
    ws["B3"] = f"Informe semanal · fecha de referencia {_fecha(hoy)} · última actualización {(panel['actualizado'] or '')[:16].replace('T', ' ')} UTC · precios con impuestos salvo los mercados mayoristas"
    ws["B3"].font = gris
    cab = ["N.º", "Indicador", "Precio actual (€/kWh)", "Var. semanal (%)", "Var. interanual (%)", "Fecha del dato", "Valor original", "Unidad original", "Fuente", "Impuestos", "Estado"]
    cabecera(ws, 5, cab, col_ini=2)
    for i, r in enumerate(panel["resumen"], start=6):
        vals = [r["numero"], r["nombre"], r["precio_eur_kwh"], None if r["variacion_semanal_pct"] is None else r["variacion_semanal_pct"] / 100,
                None if r["variacion_interanual_pct"] is None else r["variacion_interanual_pct"] / 100, r["fecha_dato"], r["valor_original"],
                r["unidad_original"], NOMBRE_FUENTE[r["id"]], "sin (mayorista)" if r["impuestos"].startswith("sin") else "con", r["estado"]]
        for j, v in enumerate(vals, start=2):
            c = ws.cell(row=i, column=j, value=v if v is not None else "n. d.")
            c.border = borde_fino
            c.alignment = Alignment(vertical="center", wrap_text=(j in (3, 12)))
        ws.cell(row=i, column=4).number_format = "0.0000" if r["id"] in ("omie", "mibgas") else "0.000"
        ws.cell(row=i, column=4).font = Font(bold=True, size=12)
        ws.cell(row=i, column=5).number_format = "+0.0%;-0.0%;0.0%"
        ws.cell(row=i, column=6).number_format = "+0.0%;-0.0%;0.0%"
        ws.cell(row=i, column=8).number_format = "0.00" if (r["valor_original"] or 0) > 10 else "0.0000"
        ws.row_dimensions[i].height = 30
        ws.cell(row=i, column=2).fill = PatternFill("solid", fgColor=COLORES[r["id"]].lstrip("#"))
        ws.cell(row=i, column=2).font = Font(bold=True, color="FFFFFF")
    fin = 5 + len(panel["resumen"])
    rojo, verde = Font(color="D03B3B"), Font(color="0CA30C")
    for col in ("E", "F"):
        rango = f"{col}6:{col}{fin}"
        ws.conditional_formatting.add(rango, CellIsRule(operator="greaterThan", formula=["0.0005"], font=rojo))
        ws.conditional_formatting.add(rango, CellIsRule(operator="lessThan", formula=["-0.0005"], font=verde))
        ws.conditional_formatting.add(rango, IconSetRule("3Arrows", "num", [-0.0005, -0.0005, 0.0005], showValue=True, reverse=False))
    anchos(ws, [2, 5, 46, 14, 13, 14, 13, 13, 22, 20, 14, 26])
    ws.freeze_panes = "C6"
    fila = fin + 2
    ws.cell(row=fila, column=2, value="Claves de la semana (generadas a partir de los datos)").font = fuente_h2
    for k, p in enumerate(panel["comentario"], start=fila + 1):
        ws.cell(row=k, column=2, value="• " + p).alignment = Alignment(wrap_text=False)
    fila_g = fila + len(panel["comentario"]) + 2
    ws.cell(row=fila_g, column=2, value="Criterios: precio actual = media de 7 días (OMIE, MIBGAS, PVPC), última semana (gasóleos) o valor vigente (TUR 2, butano, pellet); "
                                        "variaciones frente al periodo anterior y frente a hace un año; nada se estima (n. d. = no disponible).").font = gris

    # Gráfico de barras del ranking (energía final) vinculado a la tabla del cuadro de mando
    bc = BarChart()
    bc.type = "bar"
    bc.style = 10
    bc.title = "Precio actual por kWh (€/kWh)"
    bc.y_axis.title = "€/kWh"
    bc.legend = None
    bc.height, bc.width = 8.5, 16
    bc.add_data(Reference(ws, min_col=4, min_row=5, max_row=fin), titles_from_data=True)
    bc.set_categories(Reference(ws, min_col=3, min_row=6, max_row=fin))
    bc.y_axis.number_format = "0.000"
    ws.add_chart(bc, f"B{fila_g + 2}")

    # ---------- Anual y Mensual
    anual = _anual(panel)
    wa = wb.create_sheet("Anual")
    anyos = sorted({a for d in anual.values() for a in d})
    cabecera(wa, 1, ["Año"] + [INDICADORES[id_].nombre_corto + (" (sin imp.)" if id_ in ("omie", "mibgas") else "") for id_ in ORDEN])
    for i, a in enumerate(anyos, start=2):
        wa.cell(row=i, column=1, value=int(a))
        for j, id_ in enumerate(ORDEN, start=2):
            c = wa.cell(row=i, column=j, value=anual[id_].get(a))
            c.number_format = "0.0000"
    wa.cell(row=len(anyos) + 3, column=1, value="Media anual en €/kWh de cada serie (media de sus medias mensuales). Solo años completos; el año en curso usa los meses disponibles. Vacío = falta algún mes.").font = gris
    anchos(wa, [8] + [16] * len(ORDEN))
    wa.freeze_panes = "B2"

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
        _, kwh = _mensual_kwh(panel, id_)
        idx[id_] = {mes: (k, o) for mes, k, o in zip(m.get("meses", []), kwh, m.get("media_original", []))}
    for i, mes in enumerate(meses, start=2):
        fila_v = [mes]
        for id_ in ORDEN:
            k, o = idx[id_].get(mes, (None, None))
            fila_v += [k, o]
        wm.append(fila_v)
    for j in range(2, len(cab) + 1):
        for i in range(2, len(meses) + 2):
            wm.cell(row=i, column=j).number_format = "0.0000" if j % 2 == 0 else "0.00"
    tabla(wm, f"A1:{get_column_letter(len(cab))}{len(meses) + 1}", "Mensual", "TableStyleLight9")
    wm.freeze_panes = "B2"
    anchos(wm, [10] + [15] * (len(cab) - 1))

    # ---------- Gráficos vinculados
    wg = wb.create_sheet("Gráficos")
    wg.sheet_view.showGridLines = False
    wg["A1"] = "Gráficos vinculados a las hojas «Mensual» y «Anual»: se actualizan si cambian los datos"
    wg["A1"].font = fuente_h2
    n = len(meses) + 1
    ch = LineChart()
    ch.title = "Comparativo en €/kWh (medias mensuales)"
    ch.y_axis.title = "€/kWh"
    ch.height, ch.width = 9.5, 28
    for k, id_ in enumerate(ORDEN):
        ch.add_data(Reference(wm, min_col=2 + 2 * k, min_row=1, max_row=n), titles_from_data=True)
    ch.set_categories(Reference(wm, min_col=1, min_row=2, max_row=n))
    for k, s in enumerate(ch.series):
        s.graphicalProperties.line.solidFill = COLORES[ORDEN[k]].lstrip("#")
        s.graphicalProperties.line.width = 15000
        s.smooth = False
        if ORDEN[k] == "pellet_granel":
            s.graphicalProperties.line.dashStyle = "dash"
    wg.add_chart(ch, "A3")
    ba = BarChart()
    ba.title = "Media anual en €/kWh"
    ba.height, ba.width = 9.5, 28
    for j in range(2, len(ORDEN) + 2):
        ba.add_data(Reference(wa, min_col=j, min_row=1, max_row=len(anyos) + 1), titles_from_data=True)
    ba.set_categories(Reference(wa, min_col=1, min_row=2, max_row=len(anyos) + 1))
    for k, s in enumerate(ba.series):
        s.graphicalProperties.solidFill = COLORES[ORDEN[k]].lstrip("#")
    wg.add_chart(ba, "A23")
    fila_g = 43
    for k, id_ in enumerate(ORDEN):
        ind = INDICADORES[id_]
        c = LineChart()
        c.title = f"{ind.numero}. {ind.nombre_corto} ({ind.unidad_original}, media mensual)"
        c.height, c.width = 7, 13.5
        c.legend = None
        c.add_data(Reference(wm, min_col=3 + 2 * k, min_row=1, max_row=n), titles_from_data=True)
        c.set_categories(Reference(wm, min_col=1, min_row=2, max_row=n))
        c.series[0].graphicalProperties.line.solidFill = COLORES[id_].lstrip("#")
        c.series[0].graphicalProperties.line.width = 15000
        c.series[0].smooth = False
        wg.add_chart(c, f"{'A' if k % 2 == 0 else 'J'}{fila_g + 15 * (k // 2)}")

    # ---------- Una hoja de datos por serie (formato tabla, filtrable)
    for id_ in ORDEN:
        ind = INDICADORES[id_]
        ws = wb.create_sheet(f"Datos {ind.numero} {ind.nombre_corto}"[:31].replace("/", "-"))
        ws["A1"] = f"{ind.numero}. {ind.nombre}"
        ws["A1"].font = fuente_h2
        ws["A2"] = f"Fuente: {ind.fuente}. Unidad original: {ind.unidad_original}. Frecuencia: {ind.frecuencia}. Impuestos del dato original: {ind.impuestos_original}. Conversión: {ind.conversion}"
        ws["A2"].font = gris
        df = _series_df(id_)
        cols = ["fecha", "periodo", "valor_original", "unidad_original", "eur_kwh_sin_impuestos", "eur_kwh_con_impuestos", "con_impuestos_origen",
                "impuestos_detalle", "impuestos_pendiente", "fecha_publicacion", "referencia", "nota"]
        nombres = ["Fecha", "Periodo", "Valor original", "Unidad", "€/kWh sin impuestos", "€/kWh con impuestos", "Origen del precio con impuestos",
                   "Impuestos aplicados", "Pendiente", "Fecha de publicación", "Referencia (fichero / BOE / PDF)", "Nota"]
        for j, v in enumerate(nombres, start=1):
            ws.cell(row=4, column=j, value=v)
        for _, f in df.iterrows():
            ws.append([f["fecha"].date()] + [None if (isinstance(f[c], float) and pd.isna(f[c])) else f[c] for c in cols[1:]])
        for i in range(5, 5 + len(df)):
            ws.cell(row=i, column=1).number_format = "DD/MM/YYYY"
            ws.cell(row=i, column=3).number_format = "0.0000"
            ws.cell(row=i, column=5).number_format = "0.000000"
            ws.cell(row=i, column=6).number_format = "0.000000"
        tabla(ws, f"A4:L{4 + max(len(df), 1)}", f"Datos_{id_}", "TableStyleLight9")
        ws.freeze_panes = "A5"
        anchos(ws, [12, 10, 13, 16, 13, 13, 24, 55, 30, 15, 30, 55])

    # ---------- Fuentes y criterios
    wf = wb.create_sheet("Fuentes y criterios")
    cabecera(wf, 1, ["N.º", "Indicador", "Fuente", "Dirección", "Unidad original", "Frecuencia", "Impuestos del dato original", "Conversión a €/kWh", "Nota"])
    for id_ in ORDEN:
        ind = INDICADORES[id_]
        wf.append([ind.numero, ind.nombre, ind.fuente, ind.url_fuente, ind.unidad_original, ind.frecuencia, ind.impuestos_original, ind.conversion, ind.nota])
    for i in range(2, len(ORDEN) + 2):
        for j in range(1, 10):
            wf.cell(row=i, column=j).alignment = Alignment(wrap_text=True, vertical="top")
    fila = len(ORDEN) + 3
    wf.cell(row=fila, column=1, value="Factores de conversión (poder calorífico inferior)").font = fuente_h2
    for k, f in enumerate(panel["factores"], start=fila + 1):
        wf.cell(row=k, column=2, value=f["nombre"]); wf.cell(row=k, column=3, value=f["valor"]); wf.cell(row=k, column=4, value=f["unidad"]); wf.cell(row=k, column=5, value=f["procedencia"])
    fila = fila + len(panel["factores"]) + 2
    wf.cell(row=fila, column=1, value="Criterios").font = fuente_h2
    criterios = [
        "Nada se rellena ni se estima: si la fuente no da un dato, la celda queda vacía (n. d.).",
        "Datos originales (valor original) frente a calculados (precio con impuestos de PVPC, TUR 2 y butano). El Boletín Petrolero y AVEBIOM publican ya con impuestos.",
        "Impuestos vigentes en cada fecha, con referencia al BOE en la columna «Impuestos aplicados»; en 2026 varios tipos dependen del IPC del INE.",
        "Medias mensuales: media aritmética de los datos del mes (diarios/semanales); valor vigente ponderado por días (TUR 2, butano); valor del periodo (pellet).",
        "OMIE y MIBGAS son precios mayoristas y se muestran sin impuestos.",
        f"Metodología completa y tabla de impuestos: {URL_REPO}/blob/main/docs/METODOLOGIA.md · Cuadro de mando: {URL_PANEL}",
    ]
    for k, c in enumerate(criterios, start=fila + 1):
        wf.cell(row=k, column=1, value=c)
    anchos(wf, [5, 42, 48, 48, 16, 38, 30, 58, 58])
    wb.save(ruta)
    return ruta


def generar(hoy: dt.date | None = None) -> list[Path]:
    panel = construir(hoy)
    DIR_INFORMES.mkdir(parents=True, exist_ok=True)
    return [generar_pdf(panel, DIR_INFORMES / "informe.pdf"), generar_excel(panel, DIR_INFORMES / "historico.xlsx")]
