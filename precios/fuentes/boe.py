"""BOE: resoluciones de la DGPEM con la TUR de gas natural y el precio máximo del butano envasado.

Método comprobado en la fase 1: se recorren los sumarios diarios de la API de datos abiertos
(`/datosabiertos/api/boe/sumario/AAAAMMDD`), se filtran por título y se lee el XML de cada
resolución (`/diario_boe/xml.php?id=BOE-A-…`), que contiene las tablas de precios.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from lxml import etree

from ..config import DIR_CACHE, DIR_ORIGINALES
from ..http import ErrorDescarga, clave_cache, descargar

log = logging.getLogger(__name__)

URL_SUMARIO = "https://www.boe.es/datosabiertos/api/boe/sumario/{dia:%Y%m%d}"
URL_XML = "https://www.boe.es/diario_boe/xml.php?id={bid}"
URL_HTML = "https://www.boe.es/diario_boe/txt.php?id={bid}"

RE_TUR = re.compile(r"^Resolución .*por la que se publica la tarifa de último recurso de gas natural", re.I)
RE_BUTANO = re.compile(
    r"^Resolución .*por la que se publican los nuevos precios máximos de venta, antes de impuestos, "
    r"(de los gases licuados del petróleo envasados|del butano comercial envasado)", re.I
)
RE_RELEVANTE = re.compile(r"último recurso de gas natural|gases licuados del petróleo envasados|butano comercial envasado", re.I)

MESES = {m: i + 1 for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"])}


@dataclass
class ItemSumario:
    dia: dt.date
    identificador: str
    titulo: str


@dataclass
class DocumentoBOE:
    identificador: str
    titulo: str
    fecha_publicacion: dt.date
    fecha_disposicion: dt.date | None
    parrafos: list[str]
    tablas: list[list[list[str]]]
    url_pdf: str | None = None

    @property
    def url_html(self) -> str:
        return URL_HTML.format(bid=self.identificador)


def _recorrer(o):
    if isinstance(o, dict):
        if "titulo" in o and "identificador" in o:
            yield o
        for v in o.values():
            yield from _recorrer(v)
    elif isinstance(o, list):
        for v in o:
            yield from _recorrer(v)


def sumario(dia: dt.date) -> list[ItemSumario]:
    """Ítems relevantes del sumario de un día (cacheados; los días sin BOE devuelven lista vacía)."""
    ruta = DIR_CACHE / clave_cache("boe", "sumario", f"{dia:%Y}", f"{dia:%Y%m%d}.json")
    if ruta.exists():
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return [ItemSumario(dia, d["id"], d["titulo"]) for d in datos]
    cuerpo = descargar(URL_SUMARIO.format(dia=dia), headers={"Accept": "application/json"}, aceptar_404=True)
    items: list[ItemSumario] = []
    if cuerpo:
        try:
            j = json.loads(cuerpo)
        except json.JSONDecodeError as e:
            raise ErrorDescarga(f"sumario BOE {dia} no es JSON: {e}") from e
        for it in _recorrer(j):
            if RE_RELEVANTE.search(it["titulo"]):
                items.append(ItemSumario(dia, it["identificador"], it["titulo"]))
    if dia < dt.date.today():  # el sumario de hoy puede completarse más tarde
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps([{"id": i.identificador, "titulo": i.titulo} for i in items], ensure_ascii=False), encoding="utf-8")
    return items


def buscar(desde: dt.date, hasta: dt.date, patron: re.Pattern, hilos: int = 4) -> list[ItemSumario]:
    """Resoluciones cuyo título cumple `patron`, publicadas entre `desde` y `hasta`."""
    dias = [desde + dt.timedelta(days=i) for i in range((hasta - desde).days + 1)]
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        resultados = list(ex.map(sumario, dias))
    out = [it for lista in resultados for it in lista if patron.search(it.titulo)]
    return sorted(out, key=lambda i: (i.dia, i.identificador))


def leer_xml(contenido: bytes) -> DocumentoBOE:
    root = etree.fromstring(contenido)
    meta = root.find(".//metadatos")
    texto = root.findall(".//texto")[-1]
    parrafos: list[str] = []
    tablas: list[list[list[str]]] = []
    for el in texto.iter():
        if not isinstance(el.tag, str):
            continue
        ln = etree.QName(el).localname
        if ln == "p":
            parrafos.append(" ".join("".join(el.itertext()).split()))
        elif ln == "table":
            filas = []
            for tr in el.iter():
                if isinstance(tr.tag, str) and etree.QName(tr).localname == "tr":
                    filas.append([" ".join("".join(td.itertext()).split()) for td in tr
                                  if isinstance(td.tag, str) and etree.QName(td).localname in ("td", "th")])
            tablas.append(filas)
    fp = meta.findtext("fecha_publicacion")
    fd = meta.findtext("fecha_disposicion")
    return DocumentoBOE(
        identificador=meta.findtext("identificador"),
        titulo=meta.findtext("titulo"),
        fecha_publicacion=dt.datetime.strptime(fp, "%Y%m%d").date(),
        fecha_disposicion=dt.datetime.strptime(fd, "%Y%m%d").date() if fd else None,
        parrafos=parrafos,
        tablas=tablas,
        url_pdf=meta.findtext("url_pdf"),
    )


def documento(bid: str) -> DocumentoBOE:
    """Descarga (con caché) el XML de una disposición y guarda una copia en datos/fuentes_originales/boe."""
    cuerpo = descargar(URL_XML.format(bid=bid), cache=clave_cache("boe", "xml", f"{bid}.xml"))
    copia = DIR_ORIGINALES / "boe" / f"{bid}.xml"
    if not copia.exists():
        copia.parent.mkdir(parents=True, exist_ok=True)
        copia.write_bytes(cuerpo)
    return leer_xml(cuerpo)


def _fecha_es(texto: str) -> dt.date | None:
    m = re.search(r"(\d{1,2}) de (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) de (\d{4})", texto, re.I)
    if not m:
        return None
    return dt.date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1)))


def _num(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", "."))


# ---------------------------------------------------------------- TUR gas natural

@dataclass
class ResolucionTUR:
    identificador: str
    titulo: str
    fecha_publicacion: dt.date
    fecha_efectos: dt.date
    tarifas: dict[str, tuple[float, float]] = field(default_factory=dict)  # "TUR.2" -> (fijo €/mes, variable c€/kWh)
    descripciones: dict[str, str] = field(default_factory=dict)            # "TUR.2" -> "Consumo superior a 5.000 kWh/año e inferior…"

    @property
    def tur2_variable_ckwh(self) -> float:
        return self.tarifas["TUR.2"][1]


def _tablas_tur(doc: DocumentoBOE) -> tuple[dict[str, tuple[float, float]], dict[str, str]]:
    tarifas: dict[str, tuple[float, float]] = {}
    descripciones: dict[str, str] = {}
    for tabla in doc.tablas:
        for fila in tabla:
            fila = [c.strip().strip("«»").strip() for c in fila]
            # 2019–2020: «TUR.2 Consumo superior a…» en una sola celda; 2021: «TUR.2.»; 2023–2025: «TUR.RL2»; 2026: «TUR.2»
            m = re.match(r"^TUR\.(?:RL)?(\d+)\.?(?:\s+(.*))?$", fila[0]) if fila else None
            if m:
                nums = [c for c in fila[1:] if re.fullmatch(r"[\d.]+,\d+", c)]
                if len(nums) >= 2:
                    clave = f"TUR.{m.group(1)}"
                    if clave not in tarifas:
                        tarifas[clave] = (_num(nums[-2]), _num(nums[-1]))
                        descripciones[clave] = (m.group(2) or (fila[1] if len(fila) > 3 else "")).strip()
        if "TUR.2" in tarifas:
            break  # la primera tabla con TUR es la de precios (la siguiente es la de gas manufacturado T.RL)
    return tarifas, descripciones


def parsear_tur(doc: DocumentoBOE) -> ResolucionTUR:
    efectos = None
    for p in doc.parrafos:
        if re.search(r"surtirá efectos|en vigor desde las cero horas", p):
            f = _fecha_es(p)
            if f:
                efectos = f
                break
    if efectos is None:
        raise ValueError(f"{doc.identificador}: no se encuentra la fecha de efectos")
    tarifas, descripciones = _tablas_tur(doc)
    if not tarifas:
        raise ValueError(f"{doc.identificador}: no se encuentra ninguna tabla de tarifas TUR")
    return ResolucionTUR(doc.identificador, doc.titulo, doc.fecha_publicacion, efectos, tarifas, descripciones)


RE_CORRECCION = re.compile(r"se corrigen errores|corrección de errores", re.I)


def aplicar_correccion_tur(resoluciones: list[ResolucionTUR], doc: DocumentoBOE) -> bool:
    """Sustituye las tarifas de la resolución corregida por las de la corrección. Devuelve si se aplicó."""
    m = re.search(r"en la de (\d{1,2} de \w+ de \d{4})", doc.titulo)
    fecha_original = _fecha_es(m.group(1)) if m else None
    if fecha_original is None:
        return False
    tarifas, descripciones = _tablas_tur(doc)
    if "TUR.2" not in tarifas:
        return True  # corrección que no afecta a la TUR.2
    for r in resoluciones:
        if _fecha_es(r.titulo) == fecha_original:
            r.tarifas = tarifas
            r.descripciones = descripciones
            r.titulo = r.titulo + f" [corregida por {doc.identificador}, publicada el {doc.fecha_publicacion:%d/%m/%Y}]"
            return True
    return False


# ---------------------------------------------------------------- Butano envasado

@dataclass
class ResolucionButano:
    identificador: str
    titulo: str
    fecha_publicacion: dt.date
    fecha_efectos: dt.date
    precio_sin_impuestos_ckg: float  # c€/kg


def parsear_butano(doc: DocumentoBOE) -> ResolucionButano:
    efectos = None
    precio = None
    for p in doc.parrafos:
        # unidad escrita como «c€/Kg» (hasta 2024) o «cts.€/kg» (desde 2025)
        m = re.search(r"precio máximo de venta, antes de impuestos.*?será de ([\d.]+,\d+) (?:c€|cts\.?\s*€|cent\.?)/[Kk]g", p)
        if m:
            precio = _num(m.group(1))
            f = _fecha_es(p)
            if f:
                efectos = f
        if efectos is None and re.search(r"surtirá efectos", p):
            efectos = _fecha_es(p)
    if precio is None or efectos is None:
        raise ValueError(f"{doc.identificador}: no se encuentra el precio o la fecha de efectos del butano")
    return ResolucionButano(doc.identificador, doc.titulo, doc.fecha_publicacion, efectos, precio)


def resoluciones_tur(desde: dt.date, hasta: dt.date) -> list[ResolucionTUR]:
    items = buscar(desde, hasta, RE_TUR)
    out = []
    for it in items:
        if RE_CORRECCION.search(it.titulo):
            continue
        r = parsear_tur(documento(it.identificador))
        if "TUR.2" not in r.tarifas:
            # Desde 2023 hay resoluciones que solo revisan las TUR.4 a TUR.11 (comunidades de propietarios): no afectan a la TUR.2
            log.info("BOE %s (%s): resolución de TUR sin TUR.2 (%s); se omite", r.identificador, r.fecha_publicacion, ", ".join(sorted(r.tarifas)))
            continue
        out.append(r)
    for it in items:
        if RE_CORRECCION.search(it.titulo):
            doc = documento(it.identificador)
            if not aplicar_correccion_tur(out, doc):
                raise ValueError(f"{it.identificador}: corrección de errores de la TUR que no se ha podido aplicar; revisar a mano")
    return sorted(out, key=lambda r: r.fecha_efectos)


def resoluciones_butano(desde: dt.date, hasta: dt.date) -> list[ResolucionButano]:
    out = []
    for it in buscar(desde, hasta, RE_BUTANO):
        if RE_CORRECCION.search(it.titulo):
            raise ValueError(f"{it.identificador}: corrección de errores del butano no contemplada; revisar a mano: {it.titulo}")
        out.append(parsear_butano(documento(it.identificador)))
    return sorted(out, key=lambda r: r.fecha_efectos)
