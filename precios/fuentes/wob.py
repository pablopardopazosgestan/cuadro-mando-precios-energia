"""Weekly Oil Bulletin (Comisión Europea): gasóleo de automoción y de calefacción en España.

Fichero histórico `Weekly_Oil_Bulletin_Prices_History…xlsx`, enlazado en la página del boletín.
Hojas `Prices with taxes` / `Prices wo taxes`; columnas españolas `ES_price_with_tax_diesel`,
`ES_price_with_tax_heating_oil` (y `_wo_tax_`), en €/1.000 litros; una fila por semana (lunes).
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import re
from dataclasses import dataclass

import openpyxl
from bs4 import BeautifulSoup

from ..http import descargar

log = logging.getLogger(__name__)

URL_PAGINA = "https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en"
FUENTE = "Comisión Europea, Weekly Oil Bulletin (fichero histórico de precios)"


@dataclass(frozen=True)
class SemanaWob:
    fecha: dt.date            # lunes al que se refiere el precio
    diesel_con: float | None  # €/1000 l con impuestos
    diesel_sin: float | None
    calef_con: float | None
    calef_sin: float | None


def localizar_url_historico(html: str) -> str:
    s = BeautifulSoup(html, "lxml")
    for a in s.find_all("a", href=True):
        if re.search(r"Prices_History", a["href"]):
            href = a["href"]
            return href if href.startswith("http") else "https://energy.ec.europa.eu" + href
    raise ValueError("no se encuentra el enlace al fichero histórico del Weekly Oil Bulletin")


def leer_excel(contenido: bytes) -> list[SemanaWob]:
    wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)

    def columna(hoja, nombre):
        filas = list(wb[hoja].iter_rows(values_only=True))
        cab = filas[0]
        i = cab.index(nombre)
        return {f[0].date(): (float(f[i]) if isinstance(f[i], (int, float)) else None, float(f[i + 1]) if isinstance(f[i + 1], (int, float)) else None)
                for f in filas[3:] if isinstance(f[0], dt.datetime)}

    con = columna("Prices with taxes", "ES_price_with_tax_diesel")
    sin = columna("Prices wo taxes", "ES_price_wo_tax_diesel")
    out = []
    for fecha in sorted(set(con) | set(sin)):
        dc, cc = con.get(fecha, (None, None))
        ds, cs = sin.get(fecha, (None, None))
        out.append(SemanaWob(fecha, dc, ds, cc, cs))
    return out


def descargar_historico() -> tuple[list[SemanaWob], str]:
    html = descargar(URL_PAGINA).decode("utf-8", errors="replace")
    url = localizar_url_historico(html)
    return leer_excel(descargar(url)), url
