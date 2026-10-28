import datetime as dt

import pandas as pd
import pytest

from precios import panel as P
from precios.series import COLUMNAS, _fila

D = dt.date


def _df(filas):
    return pd.DataFrame([_fila(*f) for f in filas], columns=COLUMNAS)


def test_resumen_diario_media_7_dias_y_variaciones():
    filas = []
    for i in range(400):
        f = D(2025, 9, 1) + dt.timedelta(days=i)
        v = 100.0 if f < D(2026, 9, 22) else (120.0 if f < D(2026, 9, 29) else 132.0)
        filas.append((f, f.isoformat(), v, "€/MWh", v / 1000, None, "no aplica"))
    r = P.resumen_indicador("omie", _df(filas), D(2026, 10, 5), {"estado": "ok", "series": {"omie": {"dato_nuevo": True}}})
    assert r["precio_eur_kwh"] == pytest.approx(0.132)          # media 29/09–05/10 (último dato 05/10)
    assert r["variacion_semanal_pct"] == pytest.approx(10.0)     # frente a 22–28/09 (120)
    assert r["variacion_interanual_pct"] == pytest.approx(32.0)  # frente a oct. 2025 (100)
    assert r["estado"] == "actualizado"


def test_resumen_regulado_valor_vigente_y_sin_cambio():
    filas = [(D(2025, 10, 1), "2025-10-01", 4.0, "c€/kWh", 0.04, 0.05, "calculado"),
             (D(2026, 10, 1), "2026-10-01", 5.0, "c€/kWh", 0.05, 0.07, "calculado")]
    r = P.resumen_indicador("tur2", _df(filas), D(2026, 10, 27), {"estado": "ok", "series": {"tur2": {"dato_nuevo": False}}})
    assert r["precio_eur_kwh"] == 0.07
    assert r["variacion_semanal_pct"] == 0.0                     # vigente hace 7 días: el mismo
    assert r["variacion_interanual_pct"] == pytest.approx(40.0)
    assert r["estado"] == "sin actualización en el periodo"


def test_resumen_sin_datos_y_con_impuestos_pendiente():
    r = P.resumen_indicador("pvpc", pd.DataFrame(), D(2026, 10, 27), {"estado": "error", "error": "falta ESIOS_TOKEN", "series": {}})
    assert r["precio_eur_kwh"] is None and r["estado"] == "fuente no disponible o dato pendiente" and "ESIOS" in r["detalle_estado"]
    filas = [(D(2026, 10, 20), "2026-10-20", 100.0, "€/MWh", 0.1, None, "no disponible", "", "depende del IPC")]
    r = P.resumen_indicador("pvpc", _df(filas), D(2026, 10, 21), {"estado": "ok", "series": {"pvpc": {"dato_nuevo": True}}})
    assert r["precio_eur_kwh"] is None and "IPC" in r["detalle_estado"]


def test_fuente_sin_dato_reciente_pasa_a_no_disponible():
    filas = [(D(2026, 9, 1), "2026-09-01", 100.0, "€/MWh", 0.1, None, "no aplica")]
    r = P.resumen_indicador("omie", _df(filas), D(2026, 10, 27), {"estado": "error", "error": "HTTP 500", "series": {}})
    assert r["estado"] == "fuente no disponible o dato pendiente"


def test_comentario_solo_con_datos():
    resumen = [
        {"id": "omie", "nombre_corto": "OMIE", "precio_eur_kwh": 0.1, "variacion_semanal_pct": 5.0, "variacion_interanual_pct": -10.0, "estado": "actualizado", "detalle_estado": ""},
        {"id": "butano", "nombre_corto": "Butano", "precio_eur_kwh": 0.118, "variacion_semanal_pct": 0.0, "variacion_interanual_pct": 15.8, "estado": "actualizado", "detalle_estado": ""},
        {"id": "pvpc", "nombre_corto": "PVPC", "precio_eur_kwh": None, "variacion_semanal_pct": None, "variacion_interanual_pct": None, "estado": "fuente no disponible o dato pendiente", "detalle_estado": "sin token"},
        {"id": "pellet_saco", "nombre_corto": "Pellet", "precio_eur_kwh": 0.082, "variacion_semanal_pct": 0.0, "variacion_interanual_pct": 15.6, "estado": "actualizado", "detalle_estado": ""},
    ]
    texto = " ".join(P.comentario_semanal(resumen, D(2026, 10, 27)))
    assert "OMIE +5,0 %" in texto and "Butano" in texto and "PVPC (sin token)" in texto
    assert "de menor a mayor: Pellet 0,082 €/kWh; Butano 0,118 €/kWh" in texto


@pytest.mark.skipif(not (P.DIR_SERIES / "omie.csv").exists(), reason="sin datos")
def test_panel_incluye_conjuntos_y_cambios_de_impuestos():
    panel = P.construir(D(2026, 10, 27))
    assert panel["conjuntos"]["final"] == [i for i in P.ORDEN if i not in ("omie", "mibgas")]
    assert set(panel["conjuntos"]) == {"todas", "final", "calefaccion", "electricidad", "gas", "carburantes"}
    assert set(panel["cambios_impuestos"]) == {"pvpc", "tur2", "butano", "pellet_saco", "pellet_granel"}
    tur2 = {c["fecha"]: c for c in panel["cambios_impuestos"]["tur2"]}
    assert "RDL 17/2022" in tur2["2022-10-01"]["referencia"]
    pvpc = {c["fecha"]: c["texto"] for c in panel["cambios_impuestos"]["pvpc"]}
    assert "pendiente" not in pvpc["2021-06-26"]        # el IVA de 2021 se resuelve con el OMIE mensual del panel
