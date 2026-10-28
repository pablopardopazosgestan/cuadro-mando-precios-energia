"""INE: variación anual del IPC por subclases/clases, para las condiciones fiscales de 2026.

Los RDL 7/2026, 18/2026 y 25/2026 condicionan varios tipos impositivos a que el IPC de una subclase
supere en más de un 15 % el del mismo mes del año anterior. Se leen las tablas del IPC (base 2021,
ECOICOP v2) a través del servicio Tempus publicado en www.ine.es (servicios.ine.es no es accesible):
- 79184: índices nacionales de subclases (04.5.1.0 Electricidad, 04.5.2.1 Gas natural,
  04.5.2.2 Hidrocarburos licuados, 07.2.2.1 Gasóleo, 07.2.2.2 Gasolina…).
- 76127: índices nacionales de clases (07.2.2 Combustibles y lubricantes para vehículos personales,
  que es la lectura que se da a «IPC de carburantes» del RDL 7/2026).
"""
from __future__ import annotations

import datetime as dt
import json
import logging

from ..config import DIR_DATOS
from ..http import descargar

log = logging.getLogger(__name__)

URL_TABLA = "https://www.ine.es/wstempus/js/ES/DATOS_TABLA/{tabla}?nult={nult}"
TABLA_SUBCLASES = 79184
TABLA_CLASES = 76127
FUENTE = "INE, IPC (base 2021), variación anual por subclases y clases (tablas 79184 y 76127)"

SERIES = {
    # clave usada en impuestos.py -> (tabla, nombre exacto de la serie en Tempus)
    "electricidad": (TABLA_SUBCLASES, "Nacional. Electricidad. Variación anual. "),
    "gas": (TABLA_SUBCLASES, "Nacional. Gas natural. Variación anual. "),
    "glp": (TABLA_SUBCLASES, "Nacional. Hidrocarburos licuados. Variación anual. "),
    "carburantes": (TABLA_CLASES, "Nacional. Combustibles y lubricantes para vehículos personales. Variación anual. "),
}
UMBRAL = 15.0
MESES_CONDICION = ["2026-04", "2026-06", "2026-07", "2026-09", "2026-10"]
RUTA_CONDICIONES = DIR_DATOS / "impuestos" / "condiciones_ipc_2026.json"


def descargar_tabla(tabla: int, nult: int = 24) -> list[dict]:
    cuerpo = descargar(URL_TABLA.format(tabla=tabla, nult=nult), headers={"Accept": "application/json"})
    return json.loads(cuerpo)


def variaciones_anuales(tablas: dict[int, list[dict]]) -> dict[str, dict[str, float]]:
    """{clave: {"AAAA-MM": variación anual %}} para las series de SERIES."""
    out: dict[str, dict[str, float]] = {}
    for clave, (tabla, nombre) in SERIES.items():
        serie = next((s for s in tablas[tabla] if s["Nombre"] == nombre), None)
        if serie is None:
            raise ValueError(f"INE: no se encuentra la serie {nombre!r} en la tabla {tabla}")
        out[clave] = {f"{d['Anyo']}-{int(d['FK_Periodo']):02d}": float(d["Valor"]) for d in serie["Data"] if d.get("Valor") is not None}
    return out


def actualizar_condiciones(ruta=RUTA_CONDICIONES) -> dict:
    """Descarga el IPC y rellena las condiciones (true/false/null) del fichero JSON. Devuelve el contenido."""
    tablas = {TABLA_SUBCLASES: descargar_tabla(TABLA_SUBCLASES), TABLA_CLASES: descargar_tabla(TABLA_CLASES)}
    var = variaciones_anuales(tablas)
    doc = json.loads(ruta.read_text(encoding="utf-8"))
    hoy = dt.date.today().isoformat()
    for mes in MESES_CONDICION:
        fila = doc["ipc"].setdefault(mes, {})
        valores = {}
        for clave in SERIES:
            v = var[clave].get(mes)
            fila[clave] = None if v is None else bool(v > UMBRAL)
            valores[clave] = v
        fila["valores_pct"] = valores
        fila["fuente"] = f"{FUENTE}; descargado el {hoy}" if any(v is not None for v in valores.values()) else None
    doc["_actualizado"] = hoy
    ruta.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
