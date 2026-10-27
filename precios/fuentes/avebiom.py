"""AVEBIOM: índice de precios del pellet doméstico (PDF trimestral).

Comprobado en la fase 1: PDF `IPB-indice-precios-PELLET-<n>T<AAAA>.pdf` con una página de medias
anuales (desde 2012) y una página «Precio medio trimestral» con los últimos 5 trimestres, por
formato: saco de 15 kg (€/saco), palet (€/t), granel en volquete (€/t), granel en cisterna (€/t),
cada uno con su c€/kWh (AVEBIOM usa 4,76 kWh/kg) y el IPB. Precios a consumidor final con IVA
y transporte (según el propio índice).
"""
from __future__ import annotations

import datetime as dt
import io
import json
import logging
import re
from dataclasses import dataclass

import pdfplumber

from ..config import DIR_ORIGINALES, USER_AGENT
from ..http import ErrorDescarga, clave_cache, descargar

log = logging.getLogger(__name__)

URL_PAGINA = "https://avebiom.org/actividades/indice-de-precios-biocombustibles-solidos/"
URL_MEDIA = "https://avebiom.org/wp-json/wp/v2/media"
FUENTE = "AVEBIOM, Índice de Precios de Biomasa al Consumidor (pellet de madera)"

FORMATOS = {
    "SACO de 15 kg": "saco",
    "PALET de sacos": "palet",
    "GRANEL en VOLQUETE": "volquete",
    "GRANEL en volquete": "volquete",
    "GRANEL en CISTERNA": "cisterna",
    "GRANEL en cisterna": "cisterna",
}


@dataclass(frozen=True)
class PrecioPellet:
    periodo: str              # "2026T3" (trimestre) o "2024" (media anual)
    formato: str              # saco | palet | volquete | cisterna
    precio: float             # €/saco (saco) o €/t (resto), con IVA según AVEBIOM
    ckwh_avebiom: float | None  # c€/kWh publicado por AVEBIOM (PCI 4,76 kWh/kg)
    pdf: str                  # nombre del PDF de donde sale


@dataclass(frozen=True)
class InformePellet:
    nombre_pdf: str
    url: str
    fecha_subida: dt.date | None
    fecha_actualizacion: str | None   # texto «octubre 2026»
    precios: tuple[PrecioPellet, ...]


def _num(t: str) -> float:
    return float(t.replace(".", "").replace(",", "."))


def _parsear_tabla(lineas: list[str], cabecera_periodos: list[str], nombre_pdf: str) -> list[PrecioPellet]:
    out: list[PrecioPellet] = []
    formato = None
    precios: list[float] | None = None
    n = len(cabecera_periodos)
    for l in lineas:
        l = l.strip()
        if l in FORMATOS:
            formato = FORMATOS[l]
            precios = None
            continue
        if formato is None:
            continue
        m = re.match(r"^(€/saco|€/tn|c€/kWh)\s+(.*)$", l)
        if not m:
            continue
        valores = [_num(v) for v in m.group(2).split() if re.fullmatch(r"[\d.]+,\d+|\d+", v)]
        if m.group(1) in ("€/saco", "€/tn"):
            precios = valores[-n:] if len(valores) >= n else valores
            # alineación por la derecha: los últimos valores corresponden a los últimos periodos
            desfase = n - len(precios)
            for i, v in enumerate(precios):
                out.append(PrecioPellet(cabecera_periodos[desfase + i], formato, v, None, nombre_pdf))
        elif m.group(1) == "c€/kWh" and precios is not None:
            ck = valores
            desfase = n - len(ck)
            for i, v in enumerate(ck):
                per = cabecera_periodos[desfase + i]
                for k, p in enumerate(out):
                    if p.periodo == per and p.formato == formato and p.ckwh_avebiom is None:
                        out[k] = PrecioPellet(p.periodo, p.formato, p.precio, v, p.pdf)
                        break
    return out


def leer_pdf(contenido: bytes, nombre_pdf: str) -> tuple[list[PrecioPellet], str | None]:
    """Devuelve los precios (anuales y trimestrales) y el texto de «Fecha de actualización»."""
    precios: list[PrecioPellet] = []
    actualizacion = None
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            if actualizacion is None:
                m = re.search(r"Fecha de actualización:\s*([a-záéíóú]+ \d{4})", texto, re.I)
                if m:
                    actualizacion = m.group(1)
            lineas = texto.splitlines()
            if lineas and lineas[0].startswith("Precio medio anual para el PELLET") and any(l.startswith("€/saco") for l in lineas):
                cab = lineas[1].split()
                periodos: list[str] = []
                i = 0
                while i < len(cab):
                    if re.fullmatch(r"\d{4}", cab[i]):
                        if i + 1 < len(cab) and re.fullmatch(r"\((\d)T\)", cab[i + 1]):
                            periodos.append(f"{cab[i]}T{cab[i + 1][1]}")
                            i += 2
                            continue
                        periodos.append(cab[i])
                    i += 1
                precios += [p for p in _parsear_tabla(lineas[2:], periodos, nombre_pdf) if "T" not in p.periodo]
            elif lineas and lineas[0].startswith("Precio medio trimestral para el PELLET") and any(l.startswith("€/saco") for l in lineas):
                periodos = [f"{m.group(2)}T{m.group(1)}" for m in re.finditer(r"(\d)T\s*·\s*(\d{4})", lineas[1])]
                if not periodos:
                    raise ValueError(f"{nombre_pdf}: no se reconoce la cabecera trimestral: {lineas[1]!r}")
                precios += _parsear_tabla(lineas[2:], periodos, nombre_pdf)
    if not precios:
        raise ValueError(f"{nombre_pdf}: no se ha encontrado ninguna tabla de precios del pellet")
    return precios, actualizacion


def listar_pdfs() -> list[tuple[dt.date, str]]:
    """PDF trimestrales de pellet en la mediateca de AVEBIOM: [(fecha de subida, url)].

    Se consultan dos vías y se unen: la API de medios de WordPress y la página del índice. Ambas se piden con el
    User-Agent del proyecto (el servidor rechaza a veces al cliente genérico, y desde el ejecutor de GitHub ha
    devuelto una página HTML en lugar de JSON). Si una vía falla se avisa y se usa la otra; si fallan las dos, error.
    """
    out: list[tuple[dt.date, str]] = []
    errores = []
    try:
        cuerpo = descargar(URL_MEDIA, params={"mime_type": "application/pdf", "per_page": 100, "search": "PELLET", "_fields": "date,source_url"},
                           headers={"User-Agent": USER_AGENT})
        try:
            medios = json.loads(cuerpo)
        except ValueError as e:
            raise ValueError(f"la API de medios no devolvió JSON ({e}); respuesta: {cuerpo[:120]!r}") from None
        for m in medios:
            url = m["source_url"]
            if re.search(r"IPB.*PELLET.*\.pdf$", url, re.I):
                out.append((dt.date.fromisoformat(m["date"][:10]), url))
    except Exception as e:  # noqa: BLE001
        errores.append(f"mediateca: {e}")
        log.warning("AVEBIOM: no se pudo leer la mediateca (%s); se intenta la página del índice", e)
    try:
        html = descargar(URL_PAGINA, headers={"User-Agent": USER_AGENT}).decode("utf-8", errors="replace")
        for u in set(re.findall(r'href="(https://avebiom\.org/[^"]*IPB[^"]*PELLET[^"]*\.pdf)"', html, re.I)):
            if u not in {x[1] for x in out}:
                out.append((dt.date.today(), u))
    except Exception as e:  # noqa: BLE001
        errores.append(f"página del índice: {e}")
        log.warning("AVEBIOM: no se pudo leer la página del índice (%s); se usa solo la mediateca", e)
    if not out:
        raise ErrorDescarga("AVEBIOM: ninguna vía devolvió PDF del pellet (" + "; ".join(errores) + ")")
    return sorted(out)


def descargar_informe(fecha_subida: dt.date, url: str) -> InformePellet:
    nombre = url.rsplit("/", 1)[-1]
    cuerpo = descargar(url, cache=clave_cache("avebiom", nombre))
    copia = DIR_ORIGINALES / "avebiom" / nombre
    if not copia.exists():
        copia.parent.mkdir(parents=True, exist_ok=True)
        copia.write_bytes(cuerpo)
    precios, actualizacion = leer_pdf(cuerpo, nombre)
    return InformePellet(nombre, url, fecha_subida, actualizacion, tuple(precios))


def descargar_todo() -> list[InformePellet]:
    return [descargar_informe(f, u) for f, u in listar_pdfs()]
