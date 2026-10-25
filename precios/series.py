"""Construcción de las series: frecuencia original + €/kWh (sin y con impuestos) + media mensual.

Ficheros que se escriben (todos en `datos/`):
- `series/<id>.csv`: una fila por dato original (día, semana, resolución, trimestre o año).
- `mensual/<id>.csv`: media mensual (método indicado en cada fila).
- `metadatos.json`: descripción de cada indicador y de sus series.
- `estado.json`: resultado de la última ejecución por fuente (ok/error, último dato, dato nuevo…).

El histórico se conserva: cada ejecución carga el CSV existente, añade o sustituye las filas
descargadas y nunca borra las antiguas. Si una fuente falla, su serie queda como estaba.
"""
from __future__ import annotations

import calendar
import datetime as dt
import json
import logging
import traceback

import pandas as pd

from . import __version__
from . import conversiones as cv
from . import impuestos as imp
from .config import DIR_DATOS, DIR_MENSUAL, DIR_SERIES, INICIO_AMPLIADO
from .fuentes import avebiom, boe, esios, mibgas, omie, wob
from .indicadores import INDICADORES, ORDEN

log = logging.getLogger(__name__)

COLUMNAS = [
    "fecha", "periodo", "valor_original", "unidad_original",
    "eur_kwh_sin_impuestos", "eur_kwh_con_impuestos", "con_impuestos_origen",
    "impuestos_detalle", "impuestos_pendiente", "fecha_publicacion", "referencia", "nota",
]


def _vacia() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNAS)


def cargar_serie(id_: str) -> pd.DataFrame:
    ruta = DIR_SERIES / f"{id_}.csv"
    if not ruta.exists():
        return _vacia()
    df = pd.read_csv(ruta, dtype={"periodo": str, "referencia": str, "nota": str, "impuestos_detalle": str, "impuestos_pendiente": str, "fecha_publicacion": str})
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    return df


def guardar_serie(id_: str, df: pd.DataFrame) -> None:
    DIR_SERIES.mkdir(parents=True, exist_ok=True)
    df = df[COLUMNAS].sort_values(["fecha", "periodo"]).drop_duplicates(subset=["fecha", "periodo"], keep="last")
    df.to_csv(DIR_SERIES / f"{id_}.csv", index=False, float_format="%.6f")


def fusionar(existente: pd.DataFrame, nuevo: pd.DataFrame) -> pd.DataFrame:
    """Las filas nuevas sustituyen a las existentes con la misma (fecha, periodo); el resto se conserva."""
    if existente.empty:
        return nuevo.copy()
    if nuevo.empty:
        return existente.copy()
    claves = set(zip(nuevo["fecha"], nuevo["periodo"]))
    mascara = [(f, p) not in claves for f, p in zip(existente["fecha"], existente["periodo"])]
    return pd.concat([existente[mascara], nuevo], ignore_index=True)


def _fila(fecha, periodo, valor, unidad, sin, con, origen, detalle="", pendiente="", publicacion=None, referencia="", nota="") -> dict:
    return {
        "fecha": fecha, "periodo": periodo, "valor_original": valor, "unidad_original": unidad,
        "eur_kwh_sin_impuestos": sin, "eur_kwh_con_impuestos": con, "con_impuestos_origen": origen,
        "impuestos_detalle": detalle, "impuestos_pendiente": pendiente or "",
        "fecha_publicacion": publicacion.isoformat() if isinstance(publicacion, dt.date) else (publicacion or ""),
        "referencia": referencia, "nota": nota,
    }


# ------------------------------------------------------------------ OMIE y MIBGAS (mayoristas)

def construir_omie(existente: pd.DataFrame, hoy: dt.date) -> pd.DataFrame:
    desde = INICIO_AMPLIADO if existente.empty else max(existente["fecha"]) - dt.timedelta(days=7)
    dias = omie.descargar_rango(desde, hoy + dt.timedelta(days=1))
    filas = [_fila(d.fecha, d.fecha.isoformat(), round(d.media_es, 4), "€/MWh", cv.eur_mwh_a_eur_kwh(d.media_es), None,
                   "no aplica (precio mayorista)", publicacion=d.fecha - dt.timedelta(days=1),
                   referencia=f"marginalpdbc_{d.fecha:%Y%m%d}.1", nota=f"{d.periodos} periodos; mín {d.minimo_es:.2f}, máx {d.maximo_es:.2f} €/MWh")
            for d in dias]
    return pd.DataFrame(filas, columns=COLUMNAS)


def construir_mibgas(existente: pd.DataFrame, hoy: dt.date) -> pd.DataFrame:
    desde = INICIO_AMPLIADO if existente.empty else dt.date(max(existente["fecha"]).year, 1, 1)
    dias = mibgas.descargar_rango(desde, hoy + dt.timedelta(days=1))
    filas = [_fila(d.fecha, d.fecha.isoformat(), d.indice_es, "€/MWh", cv.eur_mwh_a_eur_kwh(d.indice_es), None,
                   "no aplica (precio mayorista)", publicacion=d.fecha, referencia=f"MIBGAS_Data_{d.fecha.year}.xlsx",
                   nota="" if d.volumen_mwh is None else f"volumen {d.volumen_mwh:.0f} MWh")
            for d in dias]
    return pd.DataFrame(filas, columns=COLUMNAS)


# ------------------------------------------------------------------ Boletín Petrolero

def construir_wob(semanas: list[wob.SemanaWob], url: str, producto: str) -> pd.DataFrame:
    filas = []
    for s in semanas:
        if s.fecha < INICIO_AMPLIADO:
            continue
        con = s.diesel_con if producto == "gasoleo_a" else s.calef_con
        sin = s.diesel_sin if producto == "gasoleo_a" else s.calef_sin
        if con is None:
            continue
        nota = ""
        if dt.date(2022, 4, 1) <= s.fecha <= dt.date(2022, 12, 31):
            nota = "precio antes de la bonificación de 20 c€/l (RDL 6/2022), que el Boletín no descuenta"
        filas.append(_fila(s.fecha, s.fecha.isoformat(), round(con / 1000, 5), "€/l",
                           cv.eur_1000l_a_eur_kwh(sin) if sin is not None else None, cv.eur_1000l_a_eur_kwh(con),
                           "original (el Boletín publica con y sin impuestos)",
                           detalle="IVA e impuesto sobre hidrocarburos incluidos por la fuente", publicacion=None,
                           referencia=url.rsplit("filename=", 1)[-1], nota=nota))
    return pd.DataFrame(filas, columns=COLUMNAS)


# ------------------------------------------------------------------ PVPC

def medias_mensuales_omie(serie_omie: pd.DataFrame) -> dict[str, float]:
    if serie_omie.empty:
        return {}
    df = serie_omie.copy()
    df["mes"] = [f.strftime("%Y-%m") for f in df["fecha"]]
    return df.groupby("mes")["valor_original"].mean().to_dict()


def _mes_anterior(fecha: dt.date) -> str:
    a, m = (fecha.year, fecha.month - 1) if fecha.month > 1 else (fecha.year - 1, 12)
    return f"{a}-{m:02d}"


def construir_pvpc(existente: pd.DataFrame, hoy: dt.date, omie_mensual: dict[str, float]) -> pd.DataFrame:
    inicio = dt.date(2021, 6, 1)  # inicio de la tarifa 2.0TD
    desde = inicio if existente.empty else max(existente["fecha"]) - dt.timedelta(days=3)
    dias = esios.descargar_rango(desde, hoy + dt.timedelta(days=1))
    filas = []
    for d in dias:
        ci = imp.pvpc_con_impuestos(d.media_eur_mwh, d.fecha, omie_mensual.get(_mes_anterior(d.fecha)))
        filas.append(_fila(d.fecha, d.fecha.isoformat(), round(d.media_eur_mwh, 4), "€/MWh", cv.eur_mwh_a_eur_kwh(d.media_eur_mwh),
                           None if ci.valor is None else cv.eur_mwh_a_eur_kwh(ci.valor),
                           "calculado" if ci.valor is not None else "no disponible", detalle=ci.detalle, pendiente=ci.pendiente,
                           publicacion=d.fecha - dt.timedelta(days=1), referencia="ESIOS 1001 geo 8741",
                           nota=f"{d.n_valores} valores; mín {d.minimo:.2f}, máx {d.maximo:.2f} €/MWh"))
    return pd.DataFrame(filas, columns=COLUMNAS)


def recalcular_impuestos_pvpc(serie: pd.DataFrame, omie_mensual: dict[str, float]) -> pd.DataFrame:
    """Vuelve a aplicar los impuestos a toda la serie (por si cambian las condiciones de IPC o llega OMIE)."""
    if serie.empty:
        return serie
    serie = serie.copy()
    for i, fila in serie.iterrows():
        f = fila["fecha"]
        ci = imp.pvpc_con_impuestos(float(fila["valor_original"]), f, omie_mensual.get(_mes_anterior(f)))
        serie.at[i, "eur_kwh_con_impuestos"] = None if ci.valor is None else cv.eur_mwh_a_eur_kwh(ci.valor)
        serie.at[i, "con_impuestos_origen"] = "calculado" if ci.valor is not None else "no disponible"
        serie.at[i, "impuestos_detalle"] = ci.detalle
        serie.at[i, "impuestos_pendiente"] = ci.pendiente or ""
    return serie


# ------------------------------------------------------------------ BOE: TUR 2 y butano

INICIO_BOE = dt.date(2019, 11, 1)  # para capturar los precios vigentes el 01/01/2020


def _desde_boe(existente: pd.DataFrame) -> dt.date:
    if existente.empty:
        return INICIO_BOE
    pub = pd.to_datetime(existente["fecha_publicacion"]).max().date()
    return pub + dt.timedelta(days=1)


def construir_tur2(existente: pd.DataFrame, hoy: dt.date) -> pd.DataFrame:
    filas = []
    for r in boe.resoluciones_tur(_desde_boe(existente), hoy):
        fijo, variable = r.tarifas["TUR.2"]
        ci = imp.tur_con_impuestos(variable, r.fecha_efectos)
        filas.append(_fila(r.fecha_efectos, r.fecha_efectos.isoformat(), variable, "c€/kWh (PCS)",
                           cv.ckwh_pcs_a_eur_kwh_pci(variable), None if ci.valor is None else cv.ckwh_pcs_a_eur_kwh_pci(ci.valor),
                           "calculado" if ci.valor is not None else "no disponible", detalle=ci.detalle, pendiente=ci.pendiente,
                           publicacion=r.fecha_publicacion, referencia=r.identificador,
                           nota=f"TUR.2: {r.descripciones.get('TUR.2', '')}; término fijo {fijo:.2f} €/cliente/mes; impuestos aplicados los vigentes en la fecha de efectos"
                                + (f"; {r.titulo[r.titulo.index('[corregida'):]}" if "[corregida" in r.titulo else "")))
    return pd.DataFrame(filas, columns=COLUMNAS)


def construir_butano(existente: pd.DataFrame, hoy: dt.date) -> pd.DataFrame:
    filas = []
    for r in boe.resoluciones_butano(_desde_boe(existente), hoy):
        ci = imp.butano_bombona_con_impuestos(r.precio_sin_impuestos_ckg, r.fecha_efectos)
        sin_bombona = r.precio_sin_impuestos_ckg / 100 * cv.MASA_BOMBONA_KG
        filas.append(_fila(r.fecha_efectos, r.fecha_efectos.isoformat(), r.precio_sin_impuestos_ckg, "c€/kg (antes de impuestos)",
                           cv.eur_bombona_a_eur_kwh(sin_bombona), None if ci.valor is None else cv.eur_bombona_a_eur_kwh(ci.valor),
                           "calculado" if ci.valor is not None else "no disponible", detalle=ci.detalle, pendiente=ci.pendiente,
                           publicacion=r.fecha_publicacion, referencia=r.identificador,
                           nota=(f"bombona 12,5 kg: {sin_bombona:.2f} € antes de impuestos" + (f"; {ci.valor:.2f} € con impuestos (calculado)" if ci.valor is not None else ""))))
    return pd.DataFrame(filas, columns=COLUMNAS)


def recalcular_impuestos_regulados(id_: str, serie: pd.DataFrame) -> pd.DataFrame:
    if serie.empty:
        return serie
    serie = serie.copy()
    for i, fila in serie.iterrows():
        f = fila["fecha"]
        v = float(fila["valor_original"])
        if id_ == "tur2":
            ci = imp.tur_con_impuestos(v, f)
            con = None if ci.valor is None else cv.ckwh_pcs_a_eur_kwh_pci(ci.valor)
        else:
            ci = imp.butano_bombona_con_impuestos(v, f)
            con = None if ci.valor is None else cv.eur_bombona_a_eur_kwh(ci.valor)
        serie.at[i, "eur_kwh_con_impuestos"] = con
        serie.at[i, "con_impuestos_origen"] = "calculado" if ci.valor is not None else "no disponible"
        serie.at[i, "impuestos_detalle"] = ci.detalle
        serie.at[i, "impuestos_pendiente"] = ci.pendiente or ""
    return serie


# ------------------------------------------------------------------ AVEBIOM

def _inicio_periodo(periodo: str) -> dt.date:
    if "T" in periodo:
        a, t = periodo.split("T")
        return dt.date(int(a), (int(t) - 1) * 3 + 1, 1)
    return dt.date(int(periodo), 1, 1)


def construir_pellet(informes: list[avebiom.InformePellet], formato: str) -> pd.DataFrame:
    """Serie trimestral (y anual donde no hay trimestre) a partir de todos los PDF. El PDF más reciente manda."""
    mejor: dict[str, tuple[avebiom.PrecioPellet, avebiom.InformePellet]] = {}
    for inf in sorted(informes, key=lambda i: i.fecha_subida or dt.date.min):
        for p in inf.precios:
            if p.formato == formato:
                mejor[p.periodo] = (p, inf)
    trimestres_por_anyo = {}
    for per in mejor:
        if "T" in per:
            trimestres_por_anyo.setdefault(per[:4], set()).add(per)
    filas = []
    for per, (p, inf) in sorted(mejor.items(), key=lambda kv: _inicio_periodo(kv[0])):
        inicio = _inicio_periodo(per)
        if inicio < INICIO_AMPLIADO:
            continue
        anual = "T" not in per
        if anual and len(trimestres_por_anyo.get(per, ())) == 4:
            continue  # ya hay los cuatro trimestres del año: la media anual sobra
        # Año parcialmente cubierto por trimestres (2024: solo 4T): se conserva la media anual para los meses sin trimestre
        unidad = "€/saco" if formato == "saco" else "€/t"
        kwh = cv.eur_saco_a_eur_kwh(p.precio) if formato == "saco" else cv.eur_tonelada_a_eur_kwh(p.precio)
        nota = ("media anual publicada por AVEBIOM (no hay dato trimestral descargable)" if anual else "precio medio trimestral") + \
               (f"; c€/kWh según AVEBIOM (4,76 kWh/kg): {p.ckwh_avebiom}" if p.ckwh_avebiom is not None else "")
        filas.append(_fila(inicio, per, p.precio, unidad, None, kwh, "original (IVA incluido según AVEBIOM)",
                           detalle="IVA incluido por la fuente (AVEBIOM indica el 21 % en el 3T2026; el tipo aplicado en trimestres con IVA reducido no está detallado)",
                           publicacion=inf.fecha_subida, referencia=inf.nombre_pdf, nota=nota))
    return pd.DataFrame(filas, columns=COLUMNAS)


# ------------------------------------------------------------------ Medias mensuales

def _meses(desde: dt.date, hasta: dt.date):
    a, m = desde.year, desde.month
    while (a, m) <= (hasta.year, hasta.month):
        yield a, m
        a, m = (a + (m == 12), (m % 12) + 1)


def media_mensual(id_: str, serie: pd.DataFrame, hoy: dt.date) -> pd.DataFrame:
    cols = ["mes", "media_original", "unidad_original", "media_eur_kwh_sin_impuestos", "media_eur_kwh_con_impuestos", "n_datos", "metodo"]
    if serie.empty:
        return pd.DataFrame(columns=cols)
    s = serie.sort_values("fecha")
    unidad = s["unidad_original"].iloc[-1]
    filas = []
    if id_ in ("omie", "mibgas", "pvpc", "gasoleo_a", "gasoleo_c"):
        s = s.copy()
        s["mes"] = [f.strftime("%Y-%m") for f in s["fecha"]]
        for mes, g in s.groupby("mes"):
            con = g["eur_kwh_con_impuestos"].dropna()
            filas.append({"mes": mes, "media_original": g["valor_original"].mean(), "unidad_original": unidad,
                          "media_eur_kwh_sin_impuestos": g["eur_kwh_sin_impuestos"].mean(),
                          "media_eur_kwh_con_impuestos": con.mean() if len(con) == len(g) else None,
                          "n_datos": len(g), "metodo": "media aritmética de los datos del mes" + ("" if len(con) == len(g) else "; con impuestos no disponible en todo el mes")})
    elif id_ in ("tur2", "butano"):
        # valor vigente cada día del mes, media ponderada por días
        fechas = list(s["fecha"])
        for a, m in _meses(max(fechas[0], INICIO_AMPLIADO), hoy):
            ndias = calendar.monthrange(a, m)[1]
            acum = {"valor_original": 0.0, "eur_kwh_sin_impuestos": 0.0, "eur_kwh_con_impuestos": 0.0}
            falta_con = False
            dias_ok = 0
            for d in range(1, ndias + 1):
                dia = dt.date(a, m, d)
                if dia > hoy:
                    break
                vig = s[s["fecha"] <= dia]
                if vig.empty:
                    continue
                fila = vig.iloc[-1]
                dias_ok += 1
                acum["valor_original"] += float(fila["valor_original"])
                acum["eur_kwh_sin_impuestos"] += float(fila["eur_kwh_sin_impuestos"])
                if pd.isna(fila["eur_kwh_con_impuestos"]):
                    falta_con = True
                else:
                    acum["eur_kwh_con_impuestos"] += float(fila["eur_kwh_con_impuestos"])
            if dias_ok == 0:
                continue
            filas.append({"mes": f"{a}-{m:02d}", "media_original": acum["valor_original"] / dias_ok, "unidad_original": unidad,
                          "media_eur_kwh_sin_impuestos": acum["eur_kwh_sin_impuestos"] / dias_ok,
                          "media_eur_kwh_con_impuestos": None if falta_con else acum["eur_kwh_con_impuestos"] / dias_ok,
                          "n_datos": dias_ok, "metodo": "valor vigente cada día del mes, media ponderada por días" + ("; con impuestos no disponible" if falta_con else "")})
    else:  # pellet: el valor del periodo se asigna a sus meses; el trimestre manda sobre la media anual
        por_mes: dict[str, dict] = {}
        for _, fila in s.iterrows():
            per = fila["periodo"]
            if "T" in per:
                a, t = int(per[:4]), int(per[-1])
                meses = [(a, (t - 1) * 3 + k) for k in (1, 2, 3)]
                metodo = "valor del trimestre asignado a sus tres meses (dato trimestral, no mensual)"
            else:
                a = int(per)
                meses = [(a, k) for k in range(1, 13)]
                metodo = "media anual de AVEBIOM asignada a los meses sin dato trimestral"
            for a, m in meses:
                if dt.date(a, m, 1) > hoy:
                    continue
                clave = f"{a}-{m:02d}"
                if "T" not in per and clave in por_mes and "trimestre" in por_mes[clave]["metodo"]:
                    continue
                por_mes[clave] = {"mes": clave, "media_original": fila["valor_original"], "unidad_original": unidad,
                                  "media_eur_kwh_sin_impuestos": None, "media_eur_kwh_con_impuestos": fila["eur_kwh_con_impuestos"],
                                  "n_datos": 1, "metodo": metodo}
        filas = list(por_mes.values())
    return pd.DataFrame(filas, columns=cols).sort_values("mes")


# ------------------------------------------------------------------ Orquestación

def _estado_anterior() -> dict:
    ruta = DIR_DATOS / "estado.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"fuentes": {}}


def actualizar(hoy: dt.date | None = None, solo: set[str] | None = None) -> dict:
    """Actualiza todas las series. Devuelve el estado por fuente (y lo escribe en datos/estado.json)."""
    hoy = hoy or dt.date.today()
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    anterior = _estado_anterior()
    estado = {"actualizado": ahora, "version": __version__, "fuentes": {}}
    series: dict[str, pd.DataFrame] = {id_: cargar_serie(id_) for id_ in ORDEN}

    def registrar(fuente: str, ids: list[str], fn):
        ultimo_ok = anterior.get("fuentes", {}).get(fuente, {}).get("ultima_actualizacion_correcta")
        try:
            nuevas = fn()
            resumen = {"estado": "ok", "error": None, "ultima_actualizacion_correcta": ahora, "series": {}}
            for id_, nueva in nuevas.items():
                antes = series[id_]
                ult_antes = max(antes["fecha"]) if not antes.empty else None
                series[id_] = fusionar(antes, nueva)
                guardar_serie(id_, series[id_])
                ult = max(series[id_]["fecha"]) if not series[id_].empty else None
                resumen["series"][id_] = {"ultimo_dato": ult.isoformat() if ult else None, "n_datos": int(len(series[id_])),
                                          "dato_nuevo": bool(ult and (ult_antes is None or ult > ult_antes))}
        except Exception as e:  # noqa: BLE001
            log.error("fuente %s: %s", fuente, e)
            resumen = {"estado": "error", "error": f"{type(e).__name__}: {e}", "traza": traceback.format_exc()[-2000:],
                       "ultima_actualizacion_correcta": ultimo_ok, "series": {}}
            for id_ in ids:
                ult = max(series[id_]["fecha"]) if not series[id_].empty else None
                resumen["series"][id_] = {"ultimo_dato": ult.isoformat() if ult else None, "n_datos": int(len(series[id_])), "dato_nuevo": False}
        estado["fuentes"][fuente] = resumen

    def quiere(*ids):
        return solo is None or any(i in solo for i in ids)

    if quiere("omie"):
        registrar("omie", ["omie"], lambda: {"omie": construir_omie(series["omie"], hoy)})
    if quiere("mibgas"):
        registrar("mibgas", ["mibgas"], lambda: {"mibgas": construir_mibgas(series["mibgas"], hoy)})
    if quiere("gasoleo_a", "gasoleo_c"):
        def _wob():
            semanas, url = wob.descargar_historico()
            return {"gasoleo_a": construir_wob(semanas, url, "gasoleo_a"), "gasoleo_c": construir_wob(semanas, url, "gasoleo_c")}
        registrar("boletin_petrolero", ["gasoleo_a", "gasoleo_c"], _wob)
    omie_mensual = medias_mensuales_omie(series["omie"])
    if quiere("pvpc"):
        def _pvpc():
            nueva = construir_pvpc(series["pvpc"], hoy, omie_mensual)
            series["pvpc"] = recalcular_impuestos_pvpc(series["pvpc"], omie_mensual)
            return {"pvpc": nueva}
        registrar("esios_pvpc", ["pvpc"], _pvpc)
    if quiere("tur2"):
        def _tur():
            nueva = construir_tur2(series["tur2"], hoy)
            series["tur2"] = recalcular_impuestos_regulados("tur2", series["tur2"])
            return {"tur2": nueva}
        registrar("boe_tur", ["tur2"], _tur)
    if quiere("butano"):
        def _but():
            nueva = construir_butano(series["butano"], hoy)
            series["butano"] = recalcular_impuestos_regulados("butano", series["butano"])
            return {"butano": nueva}
        registrar("boe_butano", ["butano"], _but)
    if quiere("pellet_saco", "pellet_granel"):
        def _pellet():
            informes = avebiom.descargar_todo()
            return {"pellet_saco": construir_pellet(informes, "saco"), "pellet_granel": construir_pellet(informes, "volquete")}
        registrar("avebiom", ["pellet_saco", "pellet_granel"], _pellet)

    # medias mensuales y metadatos de todas las series (también las no actualizadas en esta ejecución)
    DIR_MENSUAL.mkdir(parents=True, exist_ok=True)
    meta = {"generado": ahora, "version": __version__, "indicadores": {}}
    for id_ in ORDEN:
        s = series[id_]
        mm = media_mensual(id_, s, hoy)
        mm.to_csv(DIR_MENSUAL / f"{id_}.csv", index=False, float_format="%.6f")
        ind = INDICADORES[id_]
        meta["indicadores"][id_] = {
            "numero": ind.numero, "nombre": ind.nombre, "nombre_corto": ind.nombre_corto, "unidad_original": ind.unidad_original,
            "frecuencia": ind.frecuencia, "fuente": ind.fuente, "url_fuente": ind.url_fuente, "impuestos_original": ind.impuestos_original,
            "conversion": ind.conversion, "nota": ind.nota,
            "primer_dato": min(s["fecha"]).isoformat() if not s.empty else None,
            "ultimo_dato": max(s["fecha"]).isoformat() if not s.empty else None,
            "n_datos": int(len(s)), "n_meses": int(len(mm)),
            "con_impuestos_no_disponible": int(s["eur_kwh_con_impuestos"].isna().sum()) if not s.empty else 0,
        }
    meta["factores_conversion"] = [{"nombre": f.nombre, "valor": f.valor, "unidad": f.unidad, "procedencia": f.procedencia}
                                   for f in (cv.PELLET_KWH_KG, cv.PELLET_AVEBIOM_KWH_KG, cv.GASOLEO_KWH_L, cv.BUTANO_KWH_KG, cv.GAS_NATURAL_PCI_PCS)]
    (DIR_DATOS / "metadatos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (DIR_DATOS / "estado.json").write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    return estado
