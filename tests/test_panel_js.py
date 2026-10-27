"""Funciones puras del panel web (`precios/plantilla_panel.html`), ejecutadas con Node a partir del propio fichero:
estado en la URL, Base 100, media móvil, etiquetas finales sin solapes y CSV. Se omiten si no hay `node`."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PLANTILLA = Path(__file__).resolve().parent.parent / "precios" / "plantilla_panel.html"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="sin node")


def _bloque(desde: str, hasta: str) -> str:
    js = PLANTILLA.read_text(encoding="utf-8")
    i, j = js.index(desde), js.index(hasta)
    assert i < j, (desde, hasta)
    return js[i:j]


def _linea(prefijo: str) -> str:
    js = PLANTILLA.read_text(encoding="utf-8")
    m = re.search("^" + re.escape(prefijo) + ".*$", js, re.M)
    assert m, prefijo
    return m.group(0)


def _node(codigo: str):
    res = subprocess.run(["node", "-e", codigo], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


SHIMS = """
const ORDEN = ['omie','mibgas','gasoleo_a','pvpc','tur2','gasoleo_c','butano','pellet_saco','pellet_granel'];
const NOMBRES = Object.fromEntries(ORDEN.map(i => [i, i.toUpperCase()]));
const MAYORISTA = id => id === 'omie' || id === 'mibgas';
const fmtNum = (x, d) => (x == null || Number.isNaN(x)) ? 'n. d.' : x.toLocaleString('es-ES', { minimumFractionDigits: d, maximumFractionDigits: d });
const colores = () => Object.fromEntries(ORDEN.map(i => [i, '#000']));
const oscuro = () => false;
const window = { innerWidth: 1280 };
let salida = null;
const history = { replaceState: (a, b, u) => { salida = u; } };
"""


def test_estado_en_la_url_se_lee_y_se_escribe():
    bloque = _bloque("  const estado = {", "  leerHash();")
    r = _node(SHIMS + "const P = { fecha_referencia: '2026-10-27' };"
              "let location = { hash: '#series=gasoleo_c,pellet_saco,inventada&desde=2023-01-01&base100=1&frecuencia=mensual' };"
              + bloque + "leerHash(); const a = JSON.parse(JSON.stringify(estado)); escribirHash(); const url = salida;"
              "location = { hash: '' }; estado.series = ORDEN.slice(); estado.base100 = false; estado.mm7 = true; leerHash();"
              "console.log(JSON.stringify({ a, url, b: estado }));")
    assert r["a"]["series"] == ["gasoleo_c", "pellet_saco"]           # las desconocidas se descartan
    assert r["a"]["desde"] == "2023-01-01" and r["a"]["hasta"] == "2026-10-27"
    assert r["a"]["base100"] is True and r["a"]["mm7"] is False and r["a"]["frecuencia"] == "mensual"
    assert r["url"].startswith("#series=gasoleo_c%2Cpellet_saco&desde=2023-01-01&hasta=2026-10-27&frecuencia=mensual&base100=1")
    assert r["b"]["mm7"] is False and r["b"]["series"] == ORDEN_ESPERADO  # hash vacío = estado por defecto


ORDEN_ESPERADO = ["omie", "mibgas", "gasoleo_a", "pvpc", "tur2", "gasoleo_c", "butano", "pellet_saco", "pellet_granel"]


def test_base100_y_media_movil():
    codigo = SHIMS + _linea("  const mediaMovil =") + _linea("  const base100 =") + """
    console.log(JSON.stringify({
      b: base100([null, 50, 75, null, 100]), b0: base100([null, null]),
      m: mediaMovil([1, 2, 3, 4, 5, 6, 7, 8], 7), mg: mediaMovil([1, 2, 3, null, 5, 6, 7, 8, 9, 10, 11], 7),
    }));"""
    r = _node(codigo)
    assert r["b"] == [None, 100, 150, None, 200]       # primer valor disponible = 100; los huecos siguen siendo huecos
    assert r["b0"] == [None, None]
    assert r["m"] == [None] * 6 + [4, 5]                # media de 7 solo cuando hay 7 valores
    assert r["mg"][6:10] == [None] * 4 and r["mg"][10] == pytest.approx(8)   # un hueco invalida las 7 ventanas que lo contienen


def test_etiquetas_finales_no_se_solapan():
    bloque = _bloque("  const etiquetasFinales = (gd, trazas) => {", "  const dibujarComparativo = () => {")
    codigo = SHIMS + "const estado = { base100: false };" + bloque + """
    const gd = { _fullLayout: { yaxis: { range: [0, 1] }, height: 400, margin: { t: 50, b: 50 } } };
    const trazas = [
      { meta: 'tur2', y: [0.5, 0.5] }, { meta: 'butano', y: [0.5, 0.505] }, { meta: 'gasoleo_c', y: [0.51, 0.502] },
      { meta: 'pvpc', y: [0.9, null] }, { meta: 'omie', y: [null, null] },
    ];
    const an = etiquetasFinales(gd, trazas);
    const h = 300, mt = 50;
    console.log(JSON.stringify(an.map(a => ({ text: a.text, px: mt + (1 - a.y) * h, xref: a.xref, x: a.x }))));"""
    r = _node(codigo)
    textos = [a["text"] for a in r]
    assert len(r) == 4 and "OMIE" not in " ".join(textos)                 # la serie sin datos no lleva etiqueta
    assert any(t.startswith("PVPC 0,900") for t in textos)                   # usa el último dato no nulo
    px = sorted(a["px"] for a in r)
    assert all(b - a >= 13 - 1e-6 for a, b in zip(px, px[1:]))               # separación mínima de 13 px entre etiquetas
    assert all(a["xref"] == "paper" and a["x"] > 1 for a in r)               # fuera del área de datos, a la derecha


def test_csv_con_punto_y_coma_y_sin_estimaciones():
    bloque = _bloque("  const lineasCsv = (id, filas) => {", "  const descargarCsv = (id) => {")
    codigo = SHIMS + "const UNIDADES = { tur2: 'c€/kWh (PCS)' }; const R = { tur2: { fuente: 'BOE; DGPEM' } };" + bloque + """
    const filas = [{ fecha: '2026-10-01', periodo: '2026-10-01', original: 5.0428, sin: 0.055783, con: 0.064797 },
                   { fecha: '2026-07-01', periodo: '2026-07-01', original: 4.1198, sin: null, con: null }];
    console.log(JSON.stringify(lineasCsv('tur2', filas)));"""
    r = _node(codigo)
    assert r[0] == "fecha;periodo;valor_original;unidad;eur_kwh_sin_impuestos;eur_kwh_con_impuestos;fuente"
    assert r[1] == "2026-10-01;2026-10-01;5.0428;c€/kWh (PCS);0.055783;0.064797;BOE, DGPEM"   # el «;» del texto se sustituye
    assert r[2] == "2026-07-01;2026-07-01;4.1198;c€/kWh (PCS);;;BOE, DGPEM"                  # los n. d. quedan vacíos, no se estiman
