"""Informes descargables para dirección: `sitio/informes/informe.pdf` y `sitio/informes/historico.xlsx`.

Se generan en cada actualización con los mismos datos que el cuadro de mando (`panel.construir`).
- PDF (4 páginas): 1) cuadro de mando de una página: ocho indicadores en tarjetas con precio, variaciones con
  color, fecha y tendencia de 24 meses; ranking visual del coste por kWh; claves de la semana. 2) Tabla de precios
  y variaciones (con mini tendencia por fila) y comparativo de los nueve indicadores en €/kWh desde 2022, con
  etiquetas al final de cada línea sin solapes. 3) Comparativo de la energía final con impuestos, nueve gráficos
  individuales (periodo analizado sombreado, último valor en el margen) y medias anuales. 4) Estado de las fuentes,
  fuentes y metodología.
- Excel: «Cuadro de mando» (tarjetas en celdas, tabla con formato condicional, ranking ordenado con gráfico), «Anual»
  y «Mensual» (medias), «Gráficos» (vinculados a los datos), «Comparador» (series elegidas con desplegables,
  frecuencia y Base 100 por fórmulas INDEX/MATCH, gráfico vinculado), una hoja de datos por serie en formato tabla
  (filtrable) y «Fuentes y criterios».
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
from openpyxl.worksheet.datavalidation import DataValidation  # noqa: E402
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
from . import lectura  # noqa: E402
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


def _etiquetas_finales(ax, items: list[tuple[str, float, str]], x, fontsize: float = 7.0) -> list[float]:
    """Etiqueta cada línea al final (a la derecha del último dato) y separa verticalmente las que chocarían.

    `items` = (id de la serie, valor y del último dato, texto). Devuelve las posiciones y (en datos) usadas, para pruebas.
    """
    if not items:
        return []
    ax.figure.canvas.draw()
    ymin, ymax = ax.get_ylim()
    alto_px = ax.get_window_extent().height
    por_unidad = alto_px / (ymax - ymin)
    min_px = fontsize * 1.5 * ax.figure.dpi / 72
    its = sorted([{"id": i, "py": (y - ymin) * por_unidad, "txt": t} for i, y, t in items], key=lambda o: o["py"])
    for k in range(1, len(its)):
        if its[k]["py"] - its[k - 1]["py"] < min_px:
            its[k]["py"] = its[k - 1]["py"] + min_px
    exceso = its[-1]["py"] + min_px / 2 - alto_px
    if exceso > 0:
        for o in its:
            o["py"] -= exceso
    for k in range(len(its) - 2, -1, -1):
        if its[k + 1]["py"] - its[k]["py"] < min_px:
            its[k]["py"] = its[k + 1]["py"] - min_px
    ys = []
    for o in its:
        y_dat = ymin + o["py"] / por_unidad
        ys.append(y_dat)
        ax.annotate(o["txt"], xy=(x, y_dat), xycoords="data", ha="left", va="center", fontsize=fontsize, color=COLORES[o["id"]],
                    annotation_clip=False, fontweight="bold")
    return ys


def grafico_comparativo(desde: dt.date, hasta: dt.date, ids: list[str] | None = None, alto: float = 4.0) -> bytes:
    """Comparativo en €/kWh. Leyenda fuera del área de datos (debajo) y etiqueta con nombre y último valor al final de
    cada línea, separadas si chocan. El eje X se prolonga un 13 % para alojar las etiquetas sin tapar las líneas."""
    ids = list(ids or ORDEN)
    fig, ax = plt.subplots(figsize=(10.5, alto), dpi=160)
    finales = []
    for id_ in ids:
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
        validos = d[col].dropna()
        if not validos.empty:
            finales.append((id_, float(validos.iloc[-1]), f"{INDICADORES[id_].nombre_corto} {_fmt(float(validos.iloc[-1]), 4 if id_ in ('omie', 'mibgas') else 3)}"))
    _estilo(ax)
    ax.set_ylabel("€/kWh")
    ax.set_ylim(bottom=0)
    margen = (pd.Timestamp(hasta) - pd.Timestamp(desde)) * 0.19
    ax.set_xlim(pd.Timestamp(desde), pd.Timestamp(hasta) + margen)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    ax.legend(ncol=5, fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    _etiquetas_finales(ax, finales, pd.Timestamp(hasta) + margen * 0.05, fontsize=6.6)
    return _png(fig)


def grafico_individual(id_: str, desde: dt.date, hasta: dt.date, periodo: tuple[dt.date, dt.date] | None = None) -> bytes:
    """Serie en su unidad original. Sombrea el periodo analizado (`periodo`) y anota el último valor en el margen
    derecho, fuera de la línea."""
    df = _series_df(id_)
    ind = INDICADORES[id_]
    fig, ax = plt.subplots(figsize=(3.6, 2.05), dpi=160)
    margen = (pd.Timestamp(hasta) - pd.Timestamp(desde)) * 0.16
    if not df.empty:
        d = df[(df["fecha"] >= pd.Timestamp(desde)) & (df["fecha"] <= pd.Timestamp(hasta))]
        if TIPO[id_] == "escalon":
            prev = df[df["fecha"] < pd.Timestamp(desde)].tail(1)
            d = pd.concat([prev.assign(fecha=pd.Timestamp(desde)), d, d.tail(1).assign(fecha=pd.Timestamp(hasta))])
            ax.step(d["fecha"], d["valor_original"], where="post", color=COLORES[id_], linewidth=1.5)
        else:
            ax.plot(d["fecha"], d["valor_original"], color=COLORES[id_], linewidth=0.9)
        ult = df.iloc[-1]
        ax.plot([pd.Timestamp(hasta)], [float(ult["valor_original"])], "o", color=COLORES[id_], markersize=2.5, clip_on=False)
        ax.annotate(_fmt(float(ult["valor_original"]), 2), xy=(pd.Timestamp(hasta) + margen * 0.08, float(ult["valor_original"])),
                    ha="left", va="center", fontsize=7.5, color=COLORES[id_], fontweight="bold", annotation_clip=False)
    else:
        ax.text(0.5, 0.5, "sin datos", ha="center", va="center", transform=ax.transAxes, color=TINTA3)
    if periodo:
        ax.axvspan(pd.Timestamp(periodo[0]), pd.Timestamp(periodo[1]) + pd.Timedelta(days=1), color=COLORES[id_], alpha=0.18, linewidth=0)
    _estilo(ax)
    ax.set_title(f"{ind.numero}. {ind.nombre_corto}", loc="left", fontsize=8.5, fontweight="bold")
    ax.set_ylabel(ind.unidad_original, fontsize=7)
    ax.set_ylim(bottom=0)
    ax.set_xlim(pd.Timestamp(desde), pd.Timestamp(hasta) + margen)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    return _png(fig)


def grafico_competitividad(panel: dict, meses_n: int = 24) -> bytes:
    """Izquierda: prima de cada alternativa de calefacción frente al pellet en saco (hoy y hace un año).
    Derecha: evolución mensual de esa prima en los últimos `meses_n` meses (medias mensuales en €/kWh con impuestos)."""
    resumen = {r["id"]: r for r in panel["resumen"]}
    comp = lectura.competitividad(resumen, "pellet_saco")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.1), dpi=160, gridspec_kw={"width_ratios": [1, 1.5]})
    if comp:
        y = range(len(comp))
        hoy = [c["prima_pct"] for c in comp]
        antes = [c["prima_hace_un_anyo_pct"] if c["prima_hace_un_anyo_pct"] is not None else 0 for c in comp]
        a1.barh([i + 0.2 for i in y], hoy, height=0.38, color=[COLORES[c["id"]] for c in comp], label="hoy")
        a1.barh([i - 0.2 for i in y], antes, height=0.38, color=[COLORES[c["id"]] for c in comp], alpha=0.35, label="hace un año")
        for i, c in enumerate(comp):
            a1.text(c["prima_pct"] + (3 if c["prima_pct"] >= 0 else -3), i + 0.2, lectura._pct(c["prima_pct"]), va="center",
                    ha="left" if c["prima_pct"] >= 0 else "right", fontsize=6.8, color=TINTA, fontweight="bold")
            if c["prima_hace_un_anyo_pct"] is not None:
                a1.text(c["prima_hace_un_anyo_pct"] + (3 if c["prima_hace_un_anyo_pct"] >= 0 else -3), i - 0.2, lectura._pct(c["prima_hace_un_anyo_pct"]),
                        va="center", ha="left" if c["prima_hace_un_anyo_pct"] >= 0 else "right", fontsize=6.2, color=TINTA2)
        a1.set_yticks(list(y))
        a1.set_yticklabels([c["nombre"] for c in comp], fontsize=7.5)
        a1.invert_yaxis()
        a1.axvline(0, color=TINTA, linewidth=0.8)
        vmax, vmin = max(hoy + antes + [0]), min(hoy + antes + [0])
        a1.set_xlim(vmin * 1.6 - 5 if vmin < 0 else -vmax * 0.06, vmax * 1.3 + 5)
        a1.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.0f} %".replace("-", "−")))
        a1.tick_params(axis="x", labelsize=7)
        from matplotlib.patches import Patch
        a1.legend(handles=[Patch(color=TINTA2, label="hoy"), Patch(color=TINTA2, alpha=0.35, label="hace un año")], fontsize=6.5, frameon=False,
                  loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    a1.set_title("Sobrecoste del kWh frente al pellet en saco", loc="left", fontsize=8.5, fontweight="bold")
    a1.spines[["top", "right"]].set_visible(False)
    meses_p, pellet = _mensual_kwh(panel, "pellet_saco")
    base = dict(zip(meses_p, pellet))
    for id_ in lectura.ALTERNATIVAS:
        meses, vals = _mensual_kwh(panel, id_)
        pares = [(m, (v / base[m] - 1) * 100) for m, v in zip(meses, vals) if v is not None and base.get(m)][-meses_n:]
        if pares:
            a2.plot([pd.Timestamp(m + "-15") for m, _ in pares], [v for _, v in pares], color=COLORES[id_], linewidth=1.6, label=INDICADORES[id_].nombre_corto)
            a2.annotate(f"{pares[-1][1]:+.0f} %".replace("-", "−"), xy=(pd.Timestamp(pares[-1][0] + "-15"), pares[-1][1]), xytext=(4, 0), textcoords="offset points",
                        fontsize=6.5, color=COLORES[id_], va="center", fontweight="bold")
    a2.axhline(0, color=TINTA, linewidth=0.8)
    _estilo(a2)
    a2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.0f} %".replace("-", "−")))
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    a2.tick_params(labelsize=7)
    a2.set_title(f"Evolución del sobrecoste frente al pellet en saco ({meses_n} meses, medias mensuales)", loc="left", fontsize=8.5, fontweight="bold")
    a2.legend(fontsize=6.5, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16))
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

    # ---------- Página 1: cuadro de mando (tarjetas, ranking, competitividad del pellet, claves)
    el.append(Paragraph("Precios de la energía en España", h1))
    el.append(Paragraph(f"Informe semanal n.º {semana.year}-{semana.week:02d} · periodo analizado del {desde_periodo:%d/%m/%Y} al {hoy:%d/%m/%Y} · "
                        f"ocho indicadores en €/kWh, con impuestos salvo los mercados mayoristas (OMIE y MIBGAS) · nada se estima: n. d. = no disponible.", peq))
    el.append(Spacer(1, 2 * mm))

    estilo_t = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(SUPERFICIE)), ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(TINTA)),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor(BORDE)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    kpi_valor4 = st("kv4", fontName=fb, fontSize=14, leading=16)
    kpi_var4 = st("kvar4", fontSize=7, leading=8.8)
    kpi_meta4 = st("km4", fontSize=6, leading=7.6, textColor=colors.HexColor(TINTA3))

    def tarjeta(id_, extra_id=None):
        r = resumen[id_]
        precio = _fmt(r["precio_eur_kwh"], 4 if id_ in ("omie", "mibgas") else 3)
        sem, inter = r["variacion_semanal_pct"], r["variacion_interanual_pct"]
        var = (f'Semana <font color="{_color_var(sem)}">{_pct(sem)}</font><br/>Un año <font color="{_color_var(inter)}">{_pct(inter)}</font>')
        if extra_id:
            e = resumen[extra_id]
            var += (f'<br/>Granel <b>{_fmt(e["precio_eur_kwh"], 3)}</b> €/kWh · <font color="{_color_var(e["variacion_interanual_pct"])}">{_pct(e["variacion_interanual_pct"])}</font> año')
        etiqueta = "mayorista, sin imp." if r["impuestos"].startswith("sin") else "con impuestos"
        meta = f"{NOMBRE_FUENTE[id_]} · {_fecha(r['fecha_dato'])} · {etiqueta}"
        spark = Image(io.BytesIO(sparkline(panel, id_)), width=26 * mm, height=6.5 * mm, hAlign="RIGHT")
        t = Table([[Paragraph(f"{r['numero']}. {r['nombre_corto']}", kpi_nombre)],
                   [Paragraph(f'{precio} <font size="6.5" color="{TINTA2}">€/kWh</font>', kpi_valor4)],
                   [Paragraph(var, kpi_var4)], [spark], [Paragraph(meta, kpi_meta4)]], colWidths=[ancho / 4 - 3 * mm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(SUPERFICIE)),
                               ("LINEBEFORE", (0, 0), (0, -1), 2.2, colors.HexColor(COLORES[id_])),
                               ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                               ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                               ("TOPPADDING", (0, 0), (0, 0), 3), ("BOTTOMPADDING", (0, -1), (0, -1), 3)]))
        return t

    tarjetas = [tarjeta("omie"), tarjeta("mibgas"), tarjeta("gasoleo_a"), tarjeta("pvpc"),
                tarjeta("tur2"), tarjeta("gasoleo_c"), tarjeta("butano"), tarjeta("pellet_saco", "pellet_granel")]
    cuadricula = Table([tarjetas[i:i + 4] for i in range(0, 8, 4)], colWidths=[ancho / 4] * 4)
    cuadricula.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                                    ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    el.append(cuadricula)
    el.append(Paragraph("Precio actual: media de 7 días (OMIE, MIBGAS, PVPC), última semana publicada (gasóleos) o valor vigente (TUR 2, butano, pellet). "
                        "▲ sube (rojo), ▼ baja (verde), ■ sin cambio. Línea: medias mensuales de 24 meses.", peq))

    ranking = Image(io.BytesIO(grafico_ranking(panel["resumen"])), width=ancho * 0.5, height=ancho * 0.5 * 2.5 / 6.2)
    claves = [Paragraph("Claves de la semana", h2)] + [Paragraph("• " + p_, st("cl", fontSize=8.2, leading=10.6, alignment=TA_JUSTIFY)) for p_ in panel["comentario"]]
    fila = Table([[ranking, claves]], colWidths=[ancho * 0.52, ancho * 0.48])
    fila.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    el.append(fila)
    el.append(Paragraph("Pellet frente a las alternativas de calefacción", h2))
    el.append(Image(io.BytesIO(grafico_competitividad(panel)), width=ancho, height=ancho * 3.1 / 10.5))
    el.append(Paragraph("Sobrecoste = precio de la alternativa ÷ precio del pellet en saco − 1, ambos en €/kWh con impuestos (dato calculado). "
                        "Positivo: el pellet es más barato. El valor de hace un año se deduce de las variaciones interanuales.", peq))

    # ---------- Página 2: lectura para dirección
    el.append(PageBreak())
    el.append(Paragraph("Qué significa cada indicador y cómo repercute en el pellet", h2))
    el.append(Paragraph("Para cada indicador: su precio y variaciones, una lectura fija de qué mide y por qué importa para el coste de producción o el precio "
                        "del pellet, y una frase calculada con las cifras de esta semana. El impacto en euros por tonelada depende de los consumos de cada planta y no se incluye.", peq))
    lect_t = st("lt", fontName=fb, fontSize=8.2, leading=10.2)
    lect_n = st("ln", fontSize=7.4, leading=9.4, alignment=TA_JUSTIFY)
    lect_d = st("ld", fontSize=7.4, leading=9.4, alignment=TA_JUSTIFY, textColor=colors.HexColor(TINTA))
    lect_k = st("lk", fontSize=7.2, leading=9.2)
    filas = [[Paragraph(c, celda_b) for c in ("Indicador", "Qué mide y por qué importa", "Esta semana (calculado)", "24 meses")]]
    for r in panel["resumen"]:
        if r["id"] == "pellet_granel":
            continue
        id_ = r["id"]
        sem, inter = r["variacion_semanal_pct"], r["variacion_interanual_pct"]
        extra = ""
        if id_ == "pellet_saco":
            g = resumen["pellet_granel"]
            extra = (f'<br/>Granel <b>{_fmt(g["precio_eur_kwh"], 3)}</b> €/kWh · <font color="{_color_var(g["variacion_interanual_pct"])}">{_pct(g["variacion_interanual_pct"])}</font> año')
        izq = [Paragraph(f"{r['numero']}. {r['nombre_corto']}", lect_t),
               Paragraph(f'<b>{_fmt(r["precio_eur_kwh"], 4 if id_ in ("omie", "mibgas") else 3)}</b> €/kWh · {_fmt(r["valor_original"], 2 if (r["valor_original"] or 0) > 10 else 4)} {r["unidad_original"].split(" (")[0]}', lect_k),
               Paragraph(f'Semana <font color="{_color_var(sem)}">{_pct(sem)}</font> · Un año <font color="{_color_var(inter)}">{_pct(inter)}</font>{extra}', lect_k),
               Paragraph(f'{NOMBRE_FUENTE[id_]} · {_fecha(r["fecha_dato"])}', kpi_meta4)]
        filas.append([izq, Paragraph(lectura.SIGNIFICADO[id_], lect_n), Paragraph(lectura.frase_dinamica(id_, resumen), lect_d),
                      Image(io.BytesIO(sparkline(panel, id_)), width=22 * mm, height=5.5 * mm)])
    tl = Table(filas, colWidths=[ancho * 0.21, ancho * 0.36, ancho * 0.29, ancho * 0.14], repeatRows=1)
    tl.setStyle(TableStyle(estilo_t + [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                                        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
                           + [("LINEBEFORE", (0, i), (0, i), 2, colors.HexColor(COLORES[r["id"]])) for i, r in enumerate([x for x in panel["resumen"] if x["id"] != "pellet_granel"], start=1)]))
    el.append(tl)

    # Estado de las fuentes en una línea y pie metodológico
    nombres_fuente = {"omie": "OMIE", "mibgas": "MIBGAS", "boletin_petrolero": "Comisión Europea", "esios_pvpc": "REE/ESIOS",
                      "boe_tur": "BOE (TUR)", "boe_butano": "BOE (butano)", "avebiom": "AVEBIOM", "ine_ipc": "INE"}
    ok = [nombres_fuente.get(k, k) for k, f in panel["fuentes"].items() if f.get("estado") == "ok"]
    mal = [f"{nombres_fuente.get(k, k)} ({str(f.get('error', ''))[:60]})" for k, f in panel["fuentes"].items() if f.get("estado") != "ok"]
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph(f"<b>Fuentes en la última actualización ({_fecha((panel.get('actualizado') or '')[:10])}):</b> "
                        + (f"correctas {len(ok)} de {len(ok) + len(mal)}" + (f"; con error: {'; '.join(mal)} (se muestra su último dato correcto)" if mal else "") + "."), peq))
    el.append(Paragraph("<b>Cómo se calcula:</b> impuestos vigentes en cada fecha (IVA, impuesto eléctrico e hidrocarburos) con referencia al BOE; conversión a €/kWh sobre poder "
                        "calorífico inferior (gasóleo 10,28 kWh/l; butano 12,73 kWh/kg; pellet 4,8 kWh/kg; gas PCI/PCS 0,904). OMIE y MIBGAS son mayoristas sin impuestos y no entran en el ranking. "
                        "Cada dato conserva su fuente y fecha; nada se rellena ni se estima. La lectura fija de cada indicador se redactó el 28/10/2026 y se revisa a mano; "
                        "las frases con cifras se calculan con los datos de este informe.", peq))
    el.append(Paragraph(f"Cuadro de mando interactivo (comparativo, filtros, CSV) y Excel con el histórico completo: {URL_PANEL} · Metodología: {URL_REPO}/blob/main/docs/METODOLOGIA.md · Versión {__version__}.", peq))
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
    # Tarjetas (2 filas x 4), cada una sobre un grupo de columnas combinadas
    resumen = {r["id"]: r for r in panel["resumen"]}
    grupos = [("C", "C"), ("D", "F"), ("G", "I"), ("J", "L")]
    orden_tarjetas = [("omie", None), ("mibgas", None), ("gasoleo_a", None), ("pvpc", None), ("tur2", None), ("gasoleo_c", None), ("butano", None), ("pellet_saco", "pellet_granel")]
    FILA_TARJETAS, ALTO_TARJETA = 5, 6
    for k, (id_, extra) in enumerate(orden_tarjetas):
        r = resumen[id_]
        c1, c2 = grupos[k % 4]
        f0 = FILA_TARJETAS + (k // 4) * (ALTO_TARJETA + 1)
        color = COLORES[id_].lstrip("#")
        etiqueta = "mayorista, sin impuestos" if r["impuestos"].startswith("sin") else "con impuestos"
        textos = [f"{r['numero']}. {r['nombre_corto']}  ·  {etiqueta}", None, f"Semana: {_pct(r['variacion_semanal_pct'])}", f"Un año: {_pct(r['variacion_interanual_pct'])}",
                  "" if not extra else f"{resumen[extra]['nombre_corto']}: {_fmt(resumen[extra]['precio_eur_kwh'], 3)} €/kWh ({_pct(resumen[extra]['variacion_semanal_pct'])} semana, {_pct(resumen[extra]['variacion_interanual_pct'])} año)",
                  f"{NOMBRE_FUENTE[id_]} · dato del {_fecha(r['fecha_dato'])}"]
        for i, txt in enumerate(textos):
            fila_i = f0 + i
            if c1 != c2:
                ws.merge_cells(f"{c1}{fila_i}:{c2}{fila_i}")
            celda = ws[f"{c1}{fila_i}"]
            if i == 1:
                celda.value = r["precio_eur_kwh"] if r["precio_eur_kwh"] is not None else "n. d."
                celda.number_format = ("0.0000" if id_ in ("omie", "mibgas") else "0.000") + ' "€/kWh"'
                celda.font = Font(name="Calibri", bold=True, size=18, color="0B0B0B")
            else:
                celda.value = txt
                celda.font = Font(name="Calibri", bold=(i == 0), size=11 if i == 0 else 9, color="FFFFFF" if i == 0 else ("52514E" if i == 5 else "0B0B0B"))
            if i == 0:
                for col in range(ws[f"{c1}1"].column, ws[f"{c2}1"].column + 1):
                    ws.cell(row=fila_i, column=col).fill = PatternFill("solid", fgColor=color)
            elif i in (2, 3):
                v = r["variacion_semanal_pct"] if i == 2 else r["variacion_interanual_pct"]
                celda.font = Font(name="Calibri", size=9, color=_color_var(v).lstrip("#"))
            else:
                for col in range(ws[f"{c1}1"].column, ws[f"{c2}1"].column + 1):
                    ws.cell(row=fila_i, column=col).fill = fill_suave
            celda.alignment = Alignment(vertical="center", horizontal="left")
        ws.row_dimensions[f0 + 1].height = 24
    fila_tabla = FILA_TARJETAS + 2 * (ALTO_TARJETA + 1) + 1
    ws.cell(row=fila_tabla - 1, column=2, value="Tabla de indicadores").font = fuente_h2
    cab = ["N.º", "Indicador", "Precio actual (€/kWh)", "Var. semanal (%)", "Var. interanual (%)", "Fecha del dato", "Valor original", "Unidad original", "Fuente", "Impuestos", "Estado"]
    cabecera(ws, fila_tabla, cab, col_ini=2)
    for i, r in enumerate(panel["resumen"], start=fila_tabla + 1):
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
    fin = fila_tabla + len(panel["resumen"])
    rojo, verde = Font(color="D03B3B"), Font(color="0CA30C")
    for col in ("E", "F"):
        rango = f"{col}{fila_tabla + 1}:{col}{fin}"
        ws.conditional_formatting.add(rango, CellIsRule(operator="greaterThan", formula=["0.0005"], font=rojo))
        ws.conditional_formatting.add(rango, CellIsRule(operator="lessThan", formula=["-0.0005"], font=verde))
        ws.conditional_formatting.add(rango, IconSetRule("3Arrows", "num", [-0.0005, -0.0005, 0.0005], showValue=True, reverse=False))
    anchos(ws, [2, 5, 46, 14, 13, 14, 13, 13, 22, 20, 14, 26])
    ws.freeze_panes = f"C{fila_tabla + 1}"
    fila = fin + 2
    ws.cell(row=fila, column=2, value="Claves de la semana (generadas a partir de los datos)").font = fuente_h2
    for k, p in enumerate(panel["comentario"], start=fila + 1):
        ws.cell(row=k, column=2, value="• " + p).alignment = Alignment(wrap_text=False)
    fila_g = fila + len(panel["comentario"]) + 2
    ws.cell(row=fila_g, column=2, value="Criterios: precio actual = media de 7 días (OMIE, MIBGAS, PVPC), última semana (gasóleos) o valor vigente (TUR 2, butano, pellet); "
                                        "variaciones frente al periodo anterior y frente a hace un año; nada se estima (n. d. = no disponible).").font = gris

    # Ranking de la energía final ordenado de menor a mayor (tabla auxiliar + gráfico de barras vinculado)
    fila_r = fila_g + 2
    ws.cell(row=fila_r, column=2, value="Ranking: coste por kWh de la energía final, con impuestos (de menor a mayor)").font = fuente_h2
    cabecera(ws, fila_r + 1, ["Indicador", "€/kWh"], col_ini=3)
    finales = sorted([r for r in panel["resumen"] if r["id"] not in ("omie", "mibgas") and r["precio_eur_kwh"] is not None], key=lambda r: r["precio_eur_kwh"])
    for k, r in enumerate(finales, start=fila_r + 2):
        ws.cell(row=k, column=3, value=r["nombre_corto"]).border = borde_fino
        c = ws.cell(row=k, column=4, value=r["precio_eur_kwh"])
        c.number_format = "0.000"
        c.border = borde_fino
    fin_r = fila_r + 1 + len(finales)
    bc = BarChart()
    bc.type = "bar"
    bc.style = 10
    bc.title = "Coste por kWh de la energía final, con impuestos (€/kWh)"
    bc.legend = None
    bc.height, bc.width = 8.5, 16
    bc.add_data(Reference(ws, min_col=4, min_row=fila_r + 1, max_row=fin_r), titles_from_data=True)
    bc.set_categories(Reference(ws, min_col=3, min_row=fila_r + 2, max_row=fin_r))
    bc.x_axis.scaling.orientation = "maxMin"   # el más barato arriba
    bc.x_axis.delete = False
    bc.y_axis.delete = False
    bc.y_axis.number_format = "0.000"
    ws.add_chart(bc, f"F{fila_r + 1}")

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
    ch.x_axis.delete = ch.y_axis.delete = False
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
    ba.x_axis.delete = ba.y_axis.delete = False
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
        c.x_axis.delete = c.y_axis.delete = False
        c.add_data(Reference(wm, min_col=3 + 2 * k, min_row=1, max_row=n), titles_from_data=True)
        c.set_categories(Reference(wm, min_col=1, min_row=2, max_row=n))
        c.series[0].graphicalProperties.line.solidFill = COLORES[id_].lstrip("#")
        c.series[0].graphicalProperties.line.width = 15000
        c.series[0].smooth = False
        wg.add_chart(c, f"{'A' if k % 2 == 0 else 'J'}{fila_g + 15 * (k // 2)}")

    # ---------- Comparador: hasta cuatro series elegidas con desplegables, frecuencia mensual/anual y Base 100
    wc = wb.create_sheet("Comparador")
    wc.sheet_view.showGridLines = False
    nm, na = len(meses) + 1, len(anyos) + 1          # últimas filas con datos en «Mensual» y «Anual»
    col_m, col_a = get_column_letter(len(cab)), get_column_letter(len(ORDEN) + 1)
    wc["B2"] = "Comparador de series"
    wc["B2"].font = fuente_titulo
    wc["B3"] = ("Elija hasta cuatro series en los desplegables, la frecuencia (mensual o anual) y si quiere verlas en Base 100 "
                "(cada serie dividida por su primer valor disponible). La tabla y el gráfico se recalculan con fórmulas sobre las hojas «Mensual» y «Anual».")
    wc["B3"].font = gris
    # Lista de series: nombre corto -> cabecera en «Mensual» (€/kWh) y en «Anual»
    wc["P4"], wc["Q4"], wc["R4"] = "Serie", "Columna en Mensual", "Columna en Anual"
    for j in ("P4", "Q4", "R4"):
        wc[j].font = Font(bold=True, color="52514E")
    for k, id_ in enumerate(ORDEN, start=5):
        wc[f"P{k}"] = INDICADORES[id_].nombre_corto
        wc[f"Q{k}"] = cab[1 + 2 * (k - 5)]
        wc[f"R{k}"] = INDICADORES[id_].nombre_corto + (" (sin imp.)" if id_ in ("omie", "mibgas") else "")
    fin_lista = 4 + len(ORDEN)
    dv_series = DataValidation(type="list", formula1=f"=$P$5:$P${fin_lista}", allow_blank=True, showDropDown=False)
    dv_frec = DataValidation(type="list", formula1='"Mensual,Anual"', allow_blank=False)
    dv_si = DataValidation(type="list", formula1='"No,Sí"', allow_blank=False)
    wc.add_data_validation(dv_series); wc.add_data_validation(dv_frec); wc.add_data_validation(dv_si)
    etiquetas = ["Serie 1", "Serie 2", "Serie 3", "Serie 4", "Frecuencia", "Base 100"]
    valores_ini = ["Gasóleo C", "Pellet saco 15 kg", "", "", "Mensual", "No"]
    for k, (et, v) in enumerate(zip(etiquetas, valores_ini), start=5):
        wc[f"B{k}"] = et
        wc[f"B{k}"].font = Font(bold=True)
        c = wc[f"C{k}"]
        c.value = v
        c.fill = PatternFill("solid", fgColor="FFF4D6")
        c.border = Border(left=Side(style="thin", color="DCDAD4"), right=Side(style="thin", color="DCDAD4"), top=Side(style="thin", color="DCDAD4"), bottom=Side(style="thin", color="DCDAD4"))
        (dv_series if k <= 8 else dv_frec if k == 9 else dv_si).add(c)
    wc["D5"] = "← desplegables (deje en blanco las series que no quiera)"
    wc["D5"].font = gris
    wc["B11"] = "Unidad: €/kWh (OMIE y MIBGAS sin impuestos; el resto con impuestos). Los huecos (#N/A) son periodos sin dato y no se dibujan."
    wc["B11"].font = gris
    # Cabeceras de la tabla calculada (fila 14), filas auxiliares 12 (índice de columna en Mensual/Anual) y 13 (primer valor para Base 100)
    FILA0 = 14
    n_filas = max(nm, na) - 1
    fin_t = FILA0 + n_filas
    wc[f"A{FILA0}"] = "Periodo"
    wc[f"A{FILA0}"].font = fuente_cab; wc[f"A{FILA0}"].fill = fill_cab
    wc["G12"], wc["G13"] = "Columna en la hoja origen (auxiliar)", "Primer valor disponible (auxiliar, Base 100)"
    wc["G12"].font = wc["G13"].font = gris
    for k in range(4):
        sel = f"$C${5 + k}"
        col_v, col_h = get_column_letter(2 + k), get_column_letter(8 + k)         # B..E visibles; H..K auxiliares (valor sin Base 100)
        wc[f"{col_v}{FILA0}"] = f'=IF({sel}="","(vacía)",{sel})'
        wc[f"{col_v}{FILA0}"].font = fuente_cab; wc[f"{col_v}{FILA0}"].fill = fill_cab
        wc[f"{col_h}{FILA0}"] = f'=IF({sel}="","(vacía)",{sel}&" (€/kWh)")'
        wc[f"{col_h}{FILA0}"].font = gris
        wc[f"{col_h}12"] = (f'=IF({sel}="",0,IF($C$9="Anual",IFERROR(MATCH(INDEX($R$5:$R${fin_lista},MATCH({sel},$P$5:$P${fin_lista},0)),Anual!$B$1:${col_a}$1,0),0),'
                            f'IFERROR(MATCH(INDEX($Q$5:$Q${fin_lista},MATCH({sel},$P$5:$P${fin_lista},0)),Mensual!$B$1:${col_m}$1,0),0)))')
        wc[f"{col_h}13"] = f'=IFERROR(INDEX({col_h}{FILA0 + 1}:{col_h}{fin_t},MATCH(TRUE,INDEX(ISNUMBER({col_h}{FILA0 + 1}:{col_h}{fin_t}),0),0)),NA())'
        wc[f"{col_h}12"].font = wc[f"{col_h}13"].font = gris
        wc[f"{col_h}13"].number_format = "0.0000"
    for i in range(1, n_filas + 1):
        f = FILA0 + i
        wc[f"A{f}"] = (f'=IF($C$9="Anual",IF({i}<={na - 1},INDEX(Anual!$A$2:$A${na},{i}),""),IF({i}<={nm - 1},INDEX(Mensual!$A$2:$A${nm},{i}),""))')
        for k in range(4):
            col_v, col_h = get_column_letter(2 + k), get_column_letter(8 + k)
            wc[f"{col_h}{f}"] = (f'=IF(OR($A{f}="",{col_h}$12=0),NA(),IF($C$9="Anual",'
                                 f'IF(INDEX(Anual!$B$2:${col_a}${na},{i},{col_h}$12)="",NA(),INDEX(Anual!$B$2:${col_a}${na},{i},{col_h}$12)),'
                                 f'IF(INDEX(Mensual!$B$2:${col_m}${nm},{i},{col_h}$12)="",NA(),INDEX(Mensual!$B$2:${col_m}${nm},{i},{col_h}$12))))')
            wc[f"{col_h}{f}"].number_format = "0.0000"
            wc[f"{col_v}{f}"] = f'=IF($C$10="Sí",{col_h}{f}/{col_h}$13*100,{col_h}{f})'
            wc[f"{col_v}{f}"].number_format = '[>=50]0.0;0.0000'
    anchos(wc, [12, 18, 18, 18, 18, 2, 18, 18, 18, 18, 2, 2, 2, 2, 2, 20, 30, 24])
    wc.freeze_panes = f"B{FILA0 + 1}"
    ch = LineChart()
    ch.title = "Comparador (series elegidas; cambia con los desplegables)"
    ch.y_axis.title = "€/kWh o índice (Base 100)"
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.height, ch.width = 9.5, 24
    for k in range(4):
        ch.add_data(Reference(wc, min_col=2 + k, min_row=FILA0, max_row=fin_t), titles_from_data=True)
    ch.set_categories(Reference(wc, min_col=1, min_row=FILA0 + 1, max_row=fin_t))
    for k, s_ in enumerate(ch.series):
        s_.graphicalProperties.line.solidFill = ["008300", "e34948", "2a78d6", "6250d6"][k]
        s_.graphicalProperties.line.width = 18000
        s_.smooth = False
    ch.display_blanks = "gap"
    wc.add_chart(ch, "G2")
    wb.calculation.fullCalcOnLoad = True

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
