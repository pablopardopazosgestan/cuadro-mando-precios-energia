"""REE/ESIOS: indicador 1001, término de facturación de energía activa del PVPC 2.0TD (€/MWh).

Requiere el token personal en la variable de entorno ESIOS_TOKEN (nunca en un fichero).
Geo 8741 = Península. Sin token la API devuelve 403 (cortafuegos), comprobado en la fase 1.
Como respaldo solo para contrastes puntuales existe la API pública apidatos.ree.es (un día por
petición; rechaza rangos largos).
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
from dataclasses import dataclass

from ..http import ErrorDescarga, clave_cache, descargar

log = logging.getLogger(__name__)

URL = "https://api.esios.ree.es/indicators/1001"
URL_APIDATOS = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"
GEO_PENINSULA = 8741
FUENTE = "REE/ESIOS, indicador 1001 (término de facturación de energía activa del PVPC 2.0TD, Península)"
URL_FUENTE = "https://www.esios.ree.es/es/pvpc"


class FaltaToken(ErrorDescarga):
    pass


@dataclass(frozen=True)
class DiaPVPC:
    fecha: dt.date
    media_eur_mwh: float   # media aritmética de los valores del día (horarios o cuarto-horarios)
    n_valores: int
    minimo: float
    maximo: float


def token() -> str:
    t = os.environ.get("ESIOS_TOKEN", "").strip()
    if not t:
        raise FaltaToken("falta la variable de entorno ESIOS_TOKEN")
    return t


def leer_respuesta(contenido: bytes) -> list[DiaPVPC]:
    j = json.loads(contenido)
    valores = j["indicator"]["values"]
    por_dia: dict[dt.date, list[float]] = {}
    for v in valores:
        if v.get("geo_id") not in (None, GEO_PENINSULA):
            continue
        # datetime con zona horaria local; el día es el local
        f = dt.date.fromisoformat(v["datetime"][:10])
        por_dia.setdefault(f, []).append(float(v["value"]))
    return [DiaPVPC(f, sum(vs) / len(vs), len(vs), min(vs), max(vs)) for f, vs in sorted(por_dia.items())]


def descargar_mes(anyo: int, mes: int) -> list[DiaPVPC]:
    ini = dt.date(anyo, mes, 1)
    fin = (dt.date(anyo + (mes == 12), (mes % 12) + 1, 1) - dt.timedelta(days=1))
    cache = clave_cache("esios", "1001", f"{anyo}-{mes:02d}.json") if fin < dt.date.today() else None
    cuerpo = descargar(
        URL,
        params={"start_date": f"{ini}T00:00", "end_date": f"{fin}T23:59", "geo_ids[]": GEO_PENINSULA},
        headers={"Accept": "application/json; application/vnd.esios-api-v1+json", "x-api-key": token()},
        cache=cache,
    )
    dias = leer_respuesta(cuerpo)
    return [d for d in dias if ini <= d.fecha <= fin]


def descargar_rango(desde: dt.date, hasta: dt.date) -> list[DiaPVPC]:
    out: list[DiaPVPC] = []
    a, m = desde.year, desde.month
    while (a, m) <= (hasta.year, hasta.month):
        out += [d for d in descargar_mes(a, m) if desde <= d.fecha <= hasta]
        a, m = (a + (m == 12), (m % 12) + 1)
    return out


def apidatos_dia(fecha: dt.date) -> DiaPVPC | None:
    """Respaldo público (sin token) para contrastar un día concreto. Puede devolver 403."""
    cuerpo = descargar(URL_APIDATOS, params={"start_date": f"{fecha}T00:00", "end_date": f"{fecha}T23:59",
                                              "time_trunc": "hour", "geo_limit": "peninsular", "geo_ids": GEO_PENINSULA},
                       headers={"Accept": "application/json"}, reintentos=1)
    j = json.loads(cuerpo)
    for inc in j.get("included", []):
        if inc["attributes"]["title"] == "PVPC":
            vals = [float(v["value"]) for v in inc["attributes"]["values"] if v["datetime"][:10] == fecha.isoformat()]
            if vals:
                return DiaPVPC(fecha, sum(vals) / len(vals), len(vals), min(vals), max(vals))
    return None
