"""Sondeo de disponibilidad real de las fuentes (fase 1).

Descarga un dato reciente y uno de enero de 2022 de cada fuente y muestra
valores de control. No escribe nada en el repositorio: deja las descargas en
./descargas/ (ignorado por git). Ejecutar con:

    python scripts/fase1_sondeo_fuentes.py

Necesita red hacia: www.omie.es, www.mibgas.es, api.esios.ree.es (con
ESIOS_TOKEN), energy.ec.europa.eu, www.boe.es, avebiom.org.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

import openpyxl
import pdfplumber
import requests
from bs4 import BeautifulSoup
from lxml import etree

DESCARGAS = Path("descargas/fase1")
DESCARGAS.mkdir(parents=True, exist_ok=True)
S = requests.Session()


def get(url: str, **kw) -> requests.Response:
    """GET con reintentos (el BOE corta conexiones de vez en cuando)."""
    for intento in range(5):
        try:
            r = S.get(url, timeout=kw.pop("timeout", 90), **kw)
            return r
        except requests.RequestException as e:  # noqa: PERF203
            espera = 2**intento
            print(f"   reintento {intento + 1} tras error {type(e).__name__}: {espera}s")
            time.sleep(espera)
    raise RuntimeError(f"sin respuesta: {url}")


def omie_media_mes(texto_ficheros: list[str]) -> tuple[int, float]:
    n, suma = 0, 0.0
    for txt in texto_ficheros:
        for linea in txt.splitlines():
            partes = linea.split(";")
            if len(partes) >= 6 and re.fullmatch(r"\d{4}", partes[0]):
                suma += float(partes[5])  # columna 6 = España (col 5 = Portugal)
                n += 1
    return n, suma / n


def sondeo_omie() -> None:
    print("\n== OMIE (mercado diario, España) ==")
    r = get("https://www.omie.es/file-download?parents=marginalpdbc&filename=marginalpdbc_2022.zip")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    enero = [z.read(n).decode("latin-1") for n in z.namelist() if "_202201" in n]
    n, media = omie_media_mes(enero)
    print(f"   zip 2022: {len(z.namelist())} ficheros diarios; enero 2022: {n} horas, media ES = {media:.2f} €/MWh (control OMIE: 201,72)")
    hoy = dt.date.today()
    for d in (hoy, hoy + dt.timedelta(days=1)):
        r = get(f"https://www.omie.es/file-download?parents=marginalpdbc&filename=marginalpdbc_{d:%Y%m%d}.1")
        ok = r.text.startswith("MARGINALPDBC")
        periodos = sum(1 for l in r.text.splitlines() if re.match(r"\d{4};", l))
        print(f"   fichero {d}: {'OK' if ok else 'aún no publicado'}; periodos = {periodos}")


def sondeo_mibgas() -> None:
    print("\n== MIBGAS (MIBGAS-ES Index) ==")
    for anyo in (2022, dt.date.today().year):
        r = get(f"https://www.mibgas.es/es/file-access/MIBGAS_Data_{anyo}.xlsx?path=AGNO_{anyo}/XLS")
        wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
        hoja = next(h for h in wb.sheetnames if "ndex" in h or "ndice" in h)
        filas = [f for f in wb[hoja].iter_rows(values_only=True) if isinstance(f[0], dt.datetime)]
        cab = [str(c).replace("\n", " ") for c in next(wb[hoja].iter_rows(values_only=True))]
        if "Area" in cab:  # formato 2022: una fila por área
            es = [(f[0].date(), f[2]) for f in filas if f[1] == "ES"]
        else:  # formato 2023+: columna "MIBGAS-ES Index"
            i = next(k for k, c in enumerate(cab) if c.startswith("MIBGAS-ES Index"))
            es = [(f[0].date(), f[i]) for f in filas if f[i] is not None]
        es.sort()
        print(f"   {anyo}: hoja '{hoja}', {len(es)} días con índice ES; primero {es[0]}, último {es[-1]}")


def sondeo_esios() -> None:
    print("\n== REE/ESIOS indicador 1001 (PVPC 2.0TD, término de energía) ==")
    token = os.environ.get("ESIOS_TOKEN")
    if not token:
        print("   ESIOS_TOKEN no definido: sin token la API devuelve 403 (WAF Incapsula). Pendiente.")
        return
    cab = {"Accept": "application/json; application/vnd.esios-api-v1+json", "x-api-key": token}
    for ini, fin in (("2022-01-01T00:00", "2022-01-01T23:59"), (f"{dt.date.today():%Y-%m-%d}T00:00", f"{dt.date.today():%Y-%m-%d}T23:59")):
        r = get("https://api.esios.ree.es/indicators/1001", headers=cab, params={"start_date": ini, "end_date": fin, "geo_ids[]": 8741})
        print(f"   {ini[:10]}: HTTP {r.status_code}", end="")
        if r.ok:
            ind = r.json()["indicator"]
            vals = ind["values"]
            print(f"; '{ind['name']}' ({ind.get('magnitud', [{}])[0].get('name', '?')}); {len(vals)} valores; primero {vals[0]['value']} ({vals[0]['datetime']})")
        else:
            print(f"; {r.text[:120]!r}")


def sondeo_wob() -> None:
    print("\n== Boletín Petrolero UE (Weekly Oil Bulletin) ==")
    pagina = get("https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en").text
    enlace = next(a["href"] for a in BeautifulSoup(pagina, "lxml").find_all("a", href=True) if "Prices_History" in a["href"])
    url = enlace if enlace.startswith("http") else "https://energy.ec.europa.eu" + enlace
    r = get(url)
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    for hoja in ("Prices with taxes", "Prices wo taxes"):
        filas = list(wb[hoja].iter_rows(values_only=True))
        cab = filas[0]
        i_diesel = cab.index("ES_price_with_tax_diesel" if "with" in hoja else "ES_price_wo_tax_diesel")
        i_calef = i_diesel + 1
        datos = {f[0].date(): (f[i_diesel], f[i_calef]) for f in filas[3:] if isinstance(f[0], dt.datetime)}
        fechas = sorted(datos)
        print(f"   hoja '{hoja}': {len(fechas)} semanas, {fechas[0]} → {fechas[-1]}; España 2022-01-03 (gasóleo A, gasóleo C) = {datos[dt.date(2022, 1, 3)]} €/1000 l; última = {datos[fechas[-1]]}")


def boe_sumario_items(dia: dt.date):
    r = get(f"https://www.boe.es/datosabiertos/api/boe/sumario/{dia:%Y%m%d}", headers={"Accept": "application/json"})
    if r.status_code != 200:
        return []
    def walk(o):
        if isinstance(o, dict):
            if "titulo" in o and "identificador" in o:
                yield o
            for v in o.values():
                yield from walk(v)
        elif isinstance(o, list):
            for v in o:
                yield from walk(v)
    return list(walk(r.json()))


def boe_tablas(bid: str):
    r = get(f"https://www.boe.es/diario_boe/xml.php?id={bid}")
    root = etree.fromstring(r.content)
    texto = root.findall(".//texto")[-1]
    parrafos, tablas = [], []
    for el in texto.iter():
        tag = etree.QName(el).localname if isinstance(el.tag, str) else ""
        if tag == "p":
            parrafos.append(" ".join("".join(el.itertext()).split()))
        elif tag == "table":
            filas = []
            for tr in el.iter():
                if isinstance(tr.tag, str) and etree.QName(tr).localname == "tr":
                    filas.append([" ".join("".join(td.itertext()).split()) for td in tr if isinstance(td.tag, str) and etree.QName(td).localname in ("td", "th")])
            tablas.append(filas)
    return root.findtext(".//metadatos/titulo"), root.findtext(".//metadatos/fecha_publicacion"), parrafos, tablas


def sondeo_boe() -> None:
    print("\n== BOE (TUR gas natural y butano envasado) ==")
    patron = re.compile(r"tarifa de último recurso de gas natural|gases licuados del petróleo envasados|butano comercial envasado", re.I)
    for ini, fin in ((dt.date(2021, 12, 20), dt.date(2022, 1, 20)), (dt.date.today() - dt.timedelta(days=45), dt.date.today())):
        d = ini
        while d <= fin:
            for it in boe_sumario_items(d):
                if patron.search(it["titulo"]):
                    print(f"   {d} {it['identificador']}: {it['titulo'][:110]}…")
            d += dt.timedelta(days=1)
    for bid in ("BOE-A-2021-21356", "BOE-A-2022-665"):
        titulo, pub, parrafos, tablas = boe_tablas(bid)
        print(f"   {bid} (publicado {pub}): {len(tablas)} tablas")
        for fila in tablas[0][:5]:
            if any("TUR.2" in c for c in fila):
                print(f"      TUR.2 → {fila}")
        for p in parrafos:
            if "precio máximo de venta, antes de impuestos" in p and "c€/Kg" in p:
                print(f"      {p[:200]}")


UA_PROYECTO = (
    "cuadro-mando-precios-energia/0.1 (descarga automatizada de datos publicos; "
    "github.com/pablopardopazosgestan/cuadro-mando-precios-energia)"
)


def sondeo_avebiom() -> None:
    print("\n== AVEBIOM (índice de precios del pellet doméstico) ==")
    # La página HTML devuelve 403 al User-Agent por defecto de python-requests; se identifica el proyecto.
    pagina = get("https://avebiom.org/actividades/indice-de-precios-biocombustibles-solidos/", headers={"User-Agent": UA_PROYECTO}).text
    pdfs = sorted({a["href"] for a in BeautifulSoup(pagina, "lxml").find_all("a", href=True) if re.search(r"PELLET.*\.pdf$", a["href"], re.I)})
    print(f"   PDF de pellet enlazados en la página: {pdfs}")
    # La mediateca de WordPress (API REST) lista todos los PDF publicados; no exige User-Agent.
    r = get("https://avebiom.org/wp-json/wp/v2/media", params={"mime_type": "application/pdf", "per_page": 100, "search": "PELLET", "_fields": "date,source_url"})
    ipb = sorted((m["date"][:10], m["source_url"]) for m in r.json() if "IPB" in m["source_url"] and "PELLET" in m["source_url"].upper())
    print("   PDF trimestrales de pellet en la mediateca (API WordPress):")
    for fecha, url in ipb:
        print(f"      {fecha} {url}")
    url = ipb[-1][1]
    r = get(url)
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        print(f"   {url.rsplit('/', 1)[-1]}: {len(pdf.pages)} páginas")
        for pg in pdf.pages:
            t = pg.extract_text() or ""
            if "Precio medio trimestral" in t and "SACO" in t:
                print("   tabla trimestral (página con los últimos 5 trimestres):\n      " + "\n      ".join(t.splitlines()[:8]))
                break


if __name__ == "__main__":
    for f in (sondeo_omie, sondeo_mibgas, sondeo_esios, sondeo_wob, sondeo_boe, sondeo_avebiom):
        try:
            f()
        except Exception as e:  # noqa: BLE001
            print(f"   ERROR en {f.__name__}: {type(e).__name__}: {e}")
    print("\nFin del sondeo.")
