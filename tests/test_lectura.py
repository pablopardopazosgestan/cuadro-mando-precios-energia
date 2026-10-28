"""Lectura para dirección: primas frente al pellet y frases calculadas (`precios/lectura.py`)."""
from precios import lectura
from precios.indicadores import ORDEN


def _r(id_, precio, sem, inter, nombre=None):
    return {"id": id_, "nombre_corto": nombre or id_, "precio_eur_kwh": precio, "variacion_semanal_pct": sem, "variacion_interanual_pct": inter}


RESUMEN = {
    "pellet_saco": _r("pellet_saco", 0.080, 0.0, 10.0, "Pellet saco 15 kg"),
    "gasoleo_c": _r("gasoleo_c", 0.144, 5.0, 60.0, "Gasóleo C"),      # hace un año: 0,090 → prima 23,75 % (pellet hace un año 0,07273)
    "butano": _r("butano", 0.120, 0.0, None, "Butano"),
    "tur2": _r("tur2", 0.070, 0.0, 10.0, "TUR 2"),
    "pvpc": _r("pvpc", None, None, None, "PVPC 2.0TD"),
    "omie": _r("omie", 0.15, -8.6, 128.5, "OMIE"),
    "mibgas": _r("mibgas", 0.09, 5.1, -20.0, "MIBGAS"),
    "gasoleo_a": _r("gasoleo_a", 0.18, 0.0, 2.0, "Gasóleo A"),
}


def test_textos_fijos_para_todos_los_indicadores():
    assert set(lectura.SIGNIFICADO) == set(ORDEN)
    assert all(len(t) > 80 for t in lectura.SIGNIFICADO.values())


def test_prima_hoy_y_hace_un_anyo():
    hoy, antes = lectura.prima(RESUMEN["gasoleo_c"], RESUMEN["pellet_saco"])
    assert round(hoy, 1) == 80.0
    assert round(antes, 1) == round((0.144 / 1.6) / (0.080 / 1.1) * 100 - 100, 1)   # 23,75 %
    assert lectura.prima(RESUMEN["butano"], RESUMEN["pellet_saco"]) == (50.0, None)   # sin interanual no hay prima de hace un año
    assert lectura.prima(RESUMEN["pvpc"], RESUMEN["pellet_saco"]) == (None, None)     # sin precio, nada
    assert lectura.precio_hace_un_anyo(_r("x", 0.1, 0, -100)) is None


def test_competitividad_solo_con_precios_disponibles():
    comp = lectura.competitividad(RESUMEN)
    assert [c["id"] for c in comp] == ["gasoleo_c", "butano", "tur2"]              # el PVPC sin precio queda fuera
    assert round(comp[2]["prima_pct"], 6) == -12.5                                              # el TUR 2 es más barato que el pellet


def test_frases_calculadas():
    f = lectura.frase_dinamica("gasoleo_c", RESUMEN)
    assert "sube (+5,0\u00a0%)" in f and "80\u00a0% más que el del pellet en saco" in f and "se amplía" in f
    assert "12\u00a0% menos que el del pellet" in lectura.frase_dinamica("tur2", RESUMEN)
    assert "no se puede valorar" in lectura.frase_dinamica("pvpc", RESUMEN)
    assert "encarece el coste eléctrico" in lectura.frase_dinamica("omie", RESUMEN)
    assert "presión sobre la competitividad" in lectura.frase_dinamica("mibgas", RESUMEN)
    assert "estable" in lectura.frase_dinamica("gasoleo_a", RESUMEN)
    fp = lectura.frase_dinamica("pellet_saco", RESUMEN)
    assert "más barato que Gasóleo C, Butano" in fp and "TUR 2 resulta más barato" in fp
