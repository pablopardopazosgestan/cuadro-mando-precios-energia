"""OMIE: precio del mercado diario en España (ficheros marginalpdbc).

Formato comprobado en la fase 1: cabecera `MARGINALPDBC;`, filas
`AAAA;MM;DD;periodo;precio_PT;precio_ES;` y una línea final `*`. Hasta el 30/09/2025 hay 24
periodos horarios (23/25 en los cambios de hora); desde el 01/10/2025, 96 cuartos de hora
(92/100 en los cambios de hora). La sexta columna es España (contrastado con el informe
mensual de OMIE de septiembre de 2026: 143,25 €/MWh).
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import zipfile
from dataclasses import dataclass

from ..config import DIR_CACHE
from ..http import ErrorDescarga, clave_cache, descargar

log = logging.getLogger(__name__)

URL_DESCARGA = "https://www.omie.es/file-download?parents=marginalpdbc&filename={nombre}"
ANYOS_EN_ZIP = range(2018, 2023)  # 2018–2022 se publican como zip anual
FUENTE = "OMIE, ficheros marginalpdbc (precio marginal del mercado diario)"
URL_FUENTE = "https://www.omie.es/es/file-access-list?parents=/Mercado%20Diario/1.%20Precios&dir=Precios%20horarios%20del%20mercado%20diario%20en%20Espa%C3%B1a&realdir=marginalpdbc"


@dataclass(frozen=True)
class DiaOmie:
    fecha: dt.date
    periodos: int
    media_es: float   # €/MWh, media aritmética de los periodos del día
    media_pt: float
    minimo_es: float
    maximo_es: float


def leer_fichero(texto: str) -> DiaOmie | None:
    """Lee el contenido de un fichero marginalpdbc. Devuelve None si no es un fichero válido."""
    if not texto.startswith("MARGINALPDBC"):
        return None
    fecha = None
    es: list[float] = []
    pt: list[float] = []
    for linea in texto.splitlines()[1:]:
        if linea.startswith("*") or not linea.strip():
            continue
        partes = linea.strip().strip(";").split(";")
        if len(partes) < 6:
            raise ValueError(f"fila OMIE inesperada: {linea!r}")
        f = dt.date(int(partes[0]), int(partes[1]), int(partes[2]))
        if fecha is None:
            fecha = f
        elif f != fecha:
            raise ValueError(f"fichero OMIE con dos fechas: {fecha} y {f}")
        pt.append(float(partes[4]))
        es.append(float(partes[5]))
    if fecha is None or not es:
        return None
    if len(es) not in (23, 24, 25, 92, 96, 100):
        raise ValueError(f"número de periodos inesperado en OMIE {fecha}: {len(es)}")
    return DiaOmie(fecha, len(es), sum(es) / len(es), sum(pt) / len(pt), min(es), max(es))


def descargar_dia(fecha: dt.date) -> DiaOmie | None:
    """Descarga el fichero diario. None si aún no está publicado."""
    return _dia_con_cache(fecha)


def descargar_anyo_zip(anyo: int) -> list[DiaOmie]:
    nombre = f"marginalpdbc_{anyo}.zip"
    cuerpo = descargar(URL_DESCARGA.format(nombre=nombre), cache=clave_cache("omie", nombre))
    z = zipfile.ZipFile(io.BytesIO(cuerpo))
    dias = []
    for n in sorted(z.namelist()):
        d = leer_fichero(z.read(n).decode("latin-1"))
        if d is not None:
            dias.append(d)
    return dias


def descargar_rango(desde: dt.date, hasta: dt.date) -> list[DiaOmie]:
    """Descarga todos los días entre `desde` y `hasta` (inclusive). Usa el zip anual cuando existe."""
    dias: dict[dt.date, DiaOmie] = {}
    for anyo in range(desde.year, hasta.year + 1):
        if anyo in ANYOS_EN_ZIP:
            for d in descargar_anyo_zip(anyo):
                if desde <= d.fecha <= hasta:
                    dias[d.fecha] = d
    f = desde
    while f <= hasta:
        if f.year not in ANYOS_EN_ZIP and f not in dias:
            try:
                d = _dia_con_cache(f)
            except ErrorDescarga as e:
                log.warning("OMIE %s: %s", f, e)
                d = None
            if d is not None:
                dias[f] = d
        f += dt.timedelta(days=1)
    return [dias[k] for k in sorted(dias)]


def _dia_con_cache(fecha: dt.date) -> DiaOmie | None:
    """Los días pasados se cachean; el de hoy/mañana se piden siempre."""
    nombre = f"marginalpdbc_{fecha:%Y%m%d}.1"
    usar_cache = fecha < dt.date.today()
    clave = clave_cache("omie", str(fecha.year), nombre) if usar_cache else None
    # Un fichero aún no publicado responde 404 (o, a veces, una página HTML): ambos casos → None.
    cuerpo = descargar(URL_DESCARGA.format(nombre=nombre), cache=clave, aceptar_404=True)
    dia = leer_fichero(cuerpo.decode("latin-1")) if cuerpo else None
    if dia is None and clave:
        (DIR_CACHE / clave).unlink(missing_ok=True)  # no dejar cacheadas respuestas vacías o de error
    return dia
