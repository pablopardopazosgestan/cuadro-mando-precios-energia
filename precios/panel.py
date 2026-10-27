"""Generación del cuadro de mando: `sitio/datos/panel.json` (datos ya procesados) y `sitio/index.html`.

El HTML es estático y lee el JSON con `fetch`; los gráficos los dibuja Plotly en el navegador.
Criterios (decisiones del 25/10/2026):
- «Precio actual» en €/kWh: media de los últimos 7 días con dato para OMIE, MIBGAS y PVPC (decisión 8);
  último dato semanal para los gasóleos; valor vigente hoy para TUR 2, butano y pellet (decisión 5).
- Variación semanal: frente a los 7 días anteriores (diarios), la semana anterior (semanales) o el valor
  vigente hace 7 días (regulados y pellet). Interanual: lo mismo un año atrás.
- Se muestra el precio con impuestos cuando la fuente o el cálculo lo dan; OMIE y MIBGAS, sin impuestos y
  etiquetados como mayoristas (decisión 1). Nada se rellena: si no hay dato, «no disponible».
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import math
import shutil
from pathlib import Path

import pandas as pd

from . import __version__
from . import impuestos as imp
from .config import DIR_DATOS, DIR_SERIES, INICIO_AMPLIADO, RAIZ
from .indicadores import INDICADORES, ORDEN

log = logging.getLogger(__name__)

DIR_SITIO = RAIZ / "sitio"
URL_REPO = "https://github.com/pablopardopazosgestan/cuadro-mando-precios-energia"
URL_ACTIONS = URL_REPO + "/actions/workflows/actualizar.yml"

# Paleta categórica de referencia (dataviz), en orden fijo. El pellet a granel comparte el tono del
# pellet en saco y se distingue por el trazo discontinuo (codificación secundaria).
COLORES = {
    "omie": "#2a78d6", "mibgas": "#eb6834", "gasoleo_a": "#1baf7a", "pvpc": "#eda100",
    "tur2": "#e87ba4", "gasoleo_c": "#008300", "butano": "#6250d6", "pellet_saco": "#e34948", "pellet_granel": "#e34948",
}
COLORES_OSCURO = {
    "omie": "#3987e5", "mibgas": "#d95926", "gasoleo_a": "#199e70", "pvpc": "#c98500",
    "tur2": "#d55181", "gasoleo_c": "#008300", "butano": "#9085e9", "pellet_saco": "#e66767", "pellet_granel": "#e66767",
}
TIPO = {  # cómo se dibuja cada serie
    "omie": "diaria", "mibgas": "diaria", "pvpc": "diaria",
    "gasoleo_a": "semanal", "gasoleo_c": "semanal",
    "tur2": "escalon", "butano": "escalon", "pellet_saco": "escalon", "pellet_granel": "escalon",
}
PLAZOS_MAXIMOS_DIAS = {  # a partir de cuántos días sin dato nuevo se considera que la fuente no responde
    "omie": 4, "mibgas": 5, "pvpc": 4, "gasoleo_a": 14, "gasoleo_c": 14, "tur2": 100, "butano": 70,
    "pellet_saco": 125, "pellet_granel": 125,
}


def _f(x) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def cargar(id_: str) -> pd.DataFrame:
    ruta = DIR_SERIES / f"{id_}.csv"
    if not ruta.exists():
        return pd.DataFrame()
    df = pd.read_csv(ruta, dtype={"periodo": str, "nota": str, "referencia": str, "impuestos_pendiente": str, "fecha_publicacion": str})
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    return df.sort_values("fecha").reset_index(drop=True)


def columna_panel(id_: str) -> tuple[str, str]:
    """(columna de €/kWh que se muestra, etiqueta de impuestos)."""
    if id_ in ("omie", "mibgas"):
        return "eur_kwh_sin_impuestos", "sin impuestos (mayorista)"
    return "eur_kwh_con_impuestos", "con impuestos"


def valor_vigente(df: pd.DataFrame, col: str, fecha: dt.date) -> tuple[float | None, dt.date | None]:
    v = df[df["fecha"] <= fecha]
    if v.empty:
        return None, None
    fila = v.iloc[-1]
    return _f(fila[col]), fila["fecha"]


def media_ventana(df: pd.DataFrame, col: str, fin: dt.date, dias: int = 7) -> tuple[float | None, int]:
    """Media de los datos con fecha en (fin-dias, fin]. Devuelve (media, n). None si falta algún valor."""
    ini = fin - dt.timedelta(days=dias)
    v = df[(df["fecha"] > ini) & (df["fecha"] <= fin)]
    if v.empty or v[col].isna().any():
        return None, int(len(v))
    return float(v[col].mean()), int(len(v))


def semana_mas_cercana(df: pd.DataFrame, col: str, objetivo: dt.date, tolerancia: int = 4) -> float | None:
    v = df[(df["fecha"] >= objetivo - dt.timedelta(days=tolerancia)) & (df["fecha"] <= objetivo + dt.timedelta(days=tolerancia))]
    if v.empty:
        return None
    fila = v.iloc[(v["fecha"] - objetivo).abs().argsort().iloc[0]] if len(v) > 1 else v.iloc[0]
    return _f(fila[col])


def variacion(actual: float | None, anterior: float | None) -> float | None:
    if actual is None or anterior is None or anterior == 0:
        return None
    return (actual / anterior - 1) * 100


def resumen_indicador(id_: str, df: pd.DataFrame, hoy: dt.date, estado_fuente: dict | None) -> dict:
    ind = INDICADORES[id_]
    col, etiqueta_imp = columna_panel(id_)
    r = {"id": id_, "numero": ind.numero, "nombre": ind.nombre, "nombre_corto": ind.nombre_corto,
         "fuente": ind.fuente, "url_fuente": ind.url_fuente, "unidad_original": ind.unidad_original,
         "impuestos": etiqueta_imp, "frecuencia": ind.frecuencia,
         "precio_eur_kwh": None, "fecha_dato": None, "periodo_dato": None, "base_precio": None,
         "variacion_semanal_pct": None, "variacion_interanual_pct": None, "valor_original": None,
         "estado": "fuente no disponible o dato pendiente", "detalle_estado": "", "nota": ind.nota}
    if df.empty:
        r["detalle_estado"] = (estado_fuente or {}).get("error") or "sin datos"
        return r
    ultimo = df.iloc[-1]
    r["fecha_dato"] = ultimo["fecha"].isoformat()
    r["periodo_dato"] = str(ultimo["periodo"])
    r["valor_original"] = _f(ultimo["valor_original"])
    r["fecha_publicacion"] = ultimo.get("fecha_publicacion") if isinstance(ultimo.get("fecha_publicacion"), str) else None
    tipo = TIPO[id_]
    if tipo == "diaria":
        fin = ultimo["fecha"]
        actual, n = media_ventana(df, col, fin)
        anterior, _ = media_ventana(df, col, fin - dt.timedelta(days=7))
        hace_un_anyo, _ = media_ventana(df, col, fin - dt.timedelta(days=364))
        r["base_precio"] = f"media de los últimos 7 días ({(fin - dt.timedelta(days=6)):%d/%m} a {fin:%d/%m/%Y}, {n} datos)"
    elif tipo == "semanal":
        fin = ultimo["fecha"]
        actual = _f(ultimo[col])
        anterior = semana_mas_cercana(df, col, fin - dt.timedelta(days=7))
        hace_un_anyo = semana_mas_cercana(df, col, fin - dt.timedelta(days=364))
        r["base_precio"] = f"precio de la semana del {fin:%d/%m/%Y}"
    else:
        actual, f_act = valor_vigente(df, col, hoy)
        anterior, _ = valor_vigente(df, col, hoy - dt.timedelta(days=7))
        hace_un_anyo, _ = valor_vigente(df, col, hoy - dt.timedelta(days=365))
        r["base_precio"] = f"valor vigente el {hoy:%d/%m/%Y} (desde el {f_act:%d/%m/%Y})" if f_act else None
        if f_act:
            r["fecha_dato"] = f_act.isoformat()
    r["precio_eur_kwh"] = actual
    r["variacion_semanal_pct"] = variacion(actual, anterior)
    r["variacion_interanual_pct"] = variacion(actual, hace_un_anyo)
    if actual is None:
        pend = str(ultimo.get("impuestos_pendiente") or "")
        r["detalle_estado"] = "precio con impuestos no disponible: " + pend if pend else "sin valor en el periodo"
    # estado de actualización
    dias_sin_dato = (hoy - ultimo["fecha"]).days
    error = (estado_fuente or {}).get("estado") == "error"
    nuevo = (estado_fuente or {}).get("series", {}).get(id_, {}).get("dato_nuevo", False)
    if error and dias_sin_dato > PLAZOS_MAXIMOS_DIAS[id_]:
        r["estado"] = "fuente no disponible o dato pendiente"
        r["detalle_estado"] = (estado_fuente or {}).get("error") or ""
    elif dias_sin_dato > PLAZOS_MAXIMOS_DIAS[id_]:
        r["estado"] = "fuente no disponible o dato pendiente"
        r["detalle_estado"] = f"último dato del {ultimo['fecha']:%d/%m/%Y}, hace {dias_sin_dato} días"
    elif nuevo or dias_sin_dato <= 7:
        r["estado"] = "actualizado"
        if error:
            r["detalle_estado"] = "la última descarga falló; se muestra el último dato correcto"
    else:
        r["estado"] = "sin actualización en el periodo"
        r["detalle_estado"] = f"último dato del {ultimo['fecha']:%d/%m/%Y}; la fuente publica con frecuencia {ind.frecuencia.split(' (')[0]}"
    return r


def serie_para_grafico(id_: str, df: pd.DataFrame) -> dict:
    col, etiqueta = columna_panel(id_)
    if df.empty:
        return {"id": id_, "fechas": [], "eur_kwh": [], "original": [], "periodos": [], "tipo": TIPO[id_], "impuestos": etiqueta}
    return {
        "id": id_, "tipo": TIPO[id_], "impuestos": etiqueta,
        "fechas": [f.isoformat() for f in df["fecha"]],
        "eur_kwh": [_f(x) for x in df[col]],
        "eur_kwh_sin": [_f(x) for x in df["eur_kwh_sin_impuestos"]],
        "original": [_f(x) for x in df["valor_original"]],
        "periodos": [str(p) for p in df["periodo"]],
        "pendiente": [bool(isinstance(p, str) and p) for p in df["impuestos_pendiente"].fillna("")],
    }


def _fmt_pct(x: float | None) -> str:
    return "no disponible" if x is None else f"{x:+.1f} %".replace(".", ",")


def _fmt_eur(x: float | None, dec: int = 3) -> str:
    return "no disponible" if x is None else f"{x:.{dec}f} €/kWh".replace(".", ",")


def comentario_semanal(resumen: list[dict], hoy: dt.date) -> list[str]:
    """Frases generadas solo a partir de los números del resumen (nada interpretativo)."""
    parrafos: list[str] = []
    con_precio = [r for r in resumen if r["precio_eur_kwh"] is not None]
    sin_precio = [r for r in resumen if r["precio_eur_kwh"] is None]
    # 1. Variaciones semanales relevantes
    movs = sorted([r for r in con_precio if r["variacion_semanal_pct"] is not None and abs(r["variacion_semanal_pct"]) >= 1.0],
                  key=lambda r: -abs(r["variacion_semanal_pct"]))
    if movs:
        partes = [f"{r['nombre_corto']} {_fmt_pct(r['variacion_semanal_pct'])}" for r in movs]
        parrafos.append("Variaciones semanales de al menos un 1 %: " + "; ".join(partes) + ".")
    estables = [r["nombre_corto"] for r in con_precio if r["variacion_semanal_pct"] is not None and abs(r["variacion_semanal_pct"]) < 1.0]
    if estables:
        parrafos.append("Sin cambios apreciables en la semana (menos de un 1 %): " + ", ".join(estables) + ".")
    # 2. Interanual
    inter = [r for r in con_precio if r["variacion_interanual_pct"] is not None]
    if inter:
        sube = [f"{r['nombre_corto']} ({_fmt_pct(r['variacion_interanual_pct'])})" for r in inter if r["variacion_interanual_pct"] > 0]
        baja = [f"{r['nombre_corto']} ({_fmt_pct(r['variacion_interanual_pct'])})" for r in inter if r["variacion_interanual_pct"] <= 0]
        frase = "Respecto a hace un año"
        if sube:
            frase += ", suben " + ", ".join(sube)
        if baja:
            frase += (" y bajan " if sube else ", bajan ") + ", ".join(baja)
        parrafos.append(frase + ".")
    # 3. Comparación entre energías finales con impuestos (se excluyen los mayoristas)
    finales = sorted([r for r in con_precio if r["id"] not in ("omie", "mibgas")], key=lambda r: r["precio_eur_kwh"])
    if len(finales) >= 2:
        partes = [f"{r['nombre_corto']} {_fmt_eur(r['precio_eur_kwh'])}" for r in finales]
        frase = "Precio por kWh de energía final, con impuestos, de menor a mayor: " + "; ".join(partes) + "."
        if finales[0]["precio_eur_kwh"]:
            ratio = f"{finales[-1]['precio_eur_kwh'] / finales[0]['precio_eur_kwh']:.1f}".replace(".", ",")
            frase += f" El más caro ({finales[-1]['nombre_corto']}) cuesta {ratio} veces el más barato ({finales[0]['nombre_corto']})."
        parrafos.append(frase)
    mayoristas = [r for r in con_precio if r["id"] in ("omie", "mibgas")]
    if mayoristas:
        parrafos.append("Precios mayoristas, sin impuestos: " + "; ".join(f"{r['nombre_corto']} {_fmt_eur(r['precio_eur_kwh'], 4)}" for r in mayoristas) + ".")
    # 4. Datos no disponibles
    if sin_precio:
        parrafos.append("Sin precio en este momento: " + "; ".join(f"{r['nombre_corto']} ({r['detalle_estado'] or r['estado']})" for r in sin_precio) + ".")
    return parrafos


def construir(hoy: dt.date | None = None) -> dict:
    """Calcula todo lo que muestran el panel y los informes (resumen, comentario, series, mensual, estado)."""
    hoy = hoy or dt.date.today()
    estado = json.loads((DIR_DATOS / "estado.json").read_text(encoding="utf-8")) if (DIR_DATOS / "estado.json").exists() else {"fuentes": {}}
    meta = json.loads((DIR_DATOS / "metadatos.json").read_text(encoding="utf-8")) if (DIR_DATOS / "metadatos.json").exists() else {}
    fuente_de = {"omie": "omie", "mibgas": "mibgas", "gasoleo_a": "boletin_petrolero", "gasoleo_c": "boletin_petrolero", "pvpc": "esios_pvpc",
                 "tur2": "boe_tur", "butano": "boe_butano", "pellet_saco": "avebiom", "pellet_granel": "avebiom"}
    resumen, series, mensual = [], {}, {}
    for id_ in ORDEN:
        df = cargar(id_)
        resumen.append(resumen_indicador(id_, df, hoy, estado["fuentes"].get(fuente_de[id_])))
        series[id_] = serie_para_grafico(id_, df)
        rm = DIR_DATOS / "mensual" / f"{id_}.csv"
        if rm.exists():
            m = pd.read_csv(rm, dtype={"mes": str})
            mensual[id_] = {"meses": list(m["mes"]), "media_original": [_f(x) for x in m["media_original"]],
                            "media_eur_kwh_sin": [_f(x) for x in m["media_eur_kwh_sin_impuestos"]],
                            "media_eur_kwh_con": [_f(x) for x in m["media_eur_kwh_con_impuestos"]]}
    # Cambios de impuestos por serie (marcas verificables en los gráficos), con la condición del IVA eléctrico
    # evaluada con las medias mensuales de la propia serie OMIE
    omie_mensual = {m: v for m, v in zip(mensual.get("omie", {}).get("meses", []), mensual.get("omie", {}).get("media_original", [])) if v is not None}
    cambios = {id_: imp.cambios_impuestos(id_, INICIO_AMPLIADO, hoy, omie_mensual) for id_ in ("pvpc", "tur2", "butano", "pellet_saco", "pellet_granel")}
    ultima_ok = max((f.get("ultima_actualizacion_correcta") or "" for f in estado["fuentes"].values()), default="") or None
    informes = []
    for nombre in ("informe.pdf", "historico.xlsx"):
        if (DIR_SITIO / "informes" / nombre).exists():
            informes.append({"nombre": nombre, "url": f"informes/{nombre}"})
    panel = {
        "generado": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "fecha_referencia": hoy.isoformat(),
        "version": __version__,
        "ultima_actualizacion_correcta": ultima_ok,
        "actualizado": estado.get("actualizado"),
        "ejecucion_url": estado.get("ejecucion_url"),
        "fuentes_con_error": [k for k, f in estado["fuentes"].items() if f.get("estado") != "ok"],
        "url_actions": URL_ACTIONS, "url_repo": URL_REPO,
        "resumen": resumen,
        "comentario": comentario_semanal(resumen, hoy),
        "series": series,
        "mensual": mensual,
        "fuentes": estado["fuentes"],
        "metadatos": meta.get("indicadores", {}),
        "factores": meta.get("factores_conversion", []),
        "colores": COLORES, "colores_oscuro": COLORES_OSCURO,
        "cambios_impuestos": cambios,
        "conjuntos": {
            "todas": ORDEN,
            "final": [i for i in ORDEN if i not in ("omie", "mibgas")],
            "calefaccion": ["tur2", "gasoleo_c", "butano", "pellet_saco", "pellet_granel"],
            "electricidad": ["omie", "pvpc"], "gas": ["mibgas", "tur2"], "carburantes": ["gasoleo_a"],
        },
        "informes": informes,
    }
    return panel


def generar(hoy: dt.date | None = None) -> Path:
    panel = construir(hoy)
    (DIR_SITIO / "datos").mkdir(parents=True, exist_ok=True)
    (DIR_SITIO / "datos" / "panel.json").write_text(json.dumps(panel, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    shutil.copy(DIR_DATOS / "estado.json", DIR_SITIO / "datos" / "estado.json")
    plantilla = Path(__file__).with_name("plantilla_panel.html").read_text(encoding="utf-8")
    plotly_js = Path(__file__).with_name("plotly.min.js")
    if plotly_js.exists():
        shutil.copy(plotly_js, DIR_SITIO / "plotly.min.js")
    (DIR_SITIO / "index.html").write_text(plantilla, encoding="utf-8")
    (DIR_SITIO / ".nojekyll").write_text("", encoding="utf-8")
    return DIR_SITIO / "index.html"
