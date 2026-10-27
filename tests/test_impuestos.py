"""Tipos impositivos por fecha: cada caso cita la norma del BOE en la que se basa."""
import datetime as dt
import json

import pytest

from precios import impuestos as I

D = dt.date


@pytest.mark.parametrize("fecha, omie_mes_ant, esperado", [
    (D(2021, 6, 1), 60.0, 0.21),      # antes del RDL 12/2021
    (D(2021, 7, 1), 83.0, 0.10),      # RDL 12/2021: 10 % si el mes anterior > 45 €/MWh
    (D(2021, 7, 1), 40.0, 0.21),      # condición no cumplida
    (D(2022, 1, 15), 239.0, 0.10),    # prórroga RDL 29/2021
    (D(2022, 7, 1), 169.0, 0.05),     # RDL 11/2022 art. 18
    (D(2023, 12, 31), 72.0, 0.05),    # prórroga RDL 20/2022
    (D(2024, 2, 15), 74.0, 0.10),     # RDL 8/2023 art. 21.1 (enero 2024: 73,9 €/MWh > 45)
    (D(2024, 3, 15), 40.0, 0.21),     # febrero 2024 por debajo de 45 €/MWh → general
    (D(2024, 7, 1), 56.0, 0.10),
    (D(2025, 1, 1), 100.0, 0.21),     # fin de las medidas
    (D(2026, 3, 21), 100.0, 0.21),    # víspera de la entrada en vigor del RDL 7/2026
    (D(2026, 3, 22), 100.0, 0.10),    # RDL 7/2026 art. 42 (sin condición de 45 €/MWh)
    (D(2026, 7, 10), 100.0, 0.21),    # julio: el RDL 18/2026 no reduce el IVA
    (D(2026, 10, 24), 100.0, 0.21),   # octubre: el RDL 25/2026 no reduce el IVA
])
def test_iva_electricidad(fecha, omie_mes_ant, esperado):
    assert I.iva_electricidad(fecha, omie_mes_ant).valor == pytest.approx(esperado)


def test_iva_electricidad_sin_omie_queda_pendiente():
    t = I.iva_electricidad(D(2023, 5, 1), None)
    assert t.valor is None and "OMIE" in t.pendiente


@pytest.mark.parametrize("fecha, esperado", [
    (D(2021, 9, 15), I.IEE_GENERAL),
    (D(2021, 9, 16), 0.005),          # RDL 17/2021 (publicado el 15/09, en vigor el 16/09)
    (D(2023, 12, 31), 0.005),
    (D(2024, 1, 1), 0.025),           # RDL 8/2023 art. 22
    (D(2024, 4, 1), 0.038),
    (D(2024, 7, 1), I.IEE_GENERAL),
    (D(2026, 3, 22), 0.005),          # RDL 7/2026 art. 40
    (D(2026, 7, 1), I.IEE_GENERAL),
    (D(2026, 10, 1), I.IEE_GENERAL),
])
def test_iee(fecha, esperado):
    assert I.iee(fecha).valor == pytest.approx(esperado)


def test_cuota_minima_iee():
    # Con el 0,5 % y un precio de 100 €/MWh la cuota sería 0,5 €/MWh, por debajo del mínimo de 1 €/MWh
    assert I.cuota_iee_eur_mwh(100.0, D(2022, 6, 1)) == pytest.approx(1.0)
    assert I.cuota_iee_eur_mwh(300.0, D(2022, 6, 1)) == pytest.approx(1.5)
    assert I.cuota_iee_eur_mwh(100.0, D(2025, 6, 1)) == pytest.approx(5.11269632)


@pytest.mark.parametrize("fecha, gas, pellets", [
    (D(2022, 9, 30), 0.21, 0.21),
    (D(2022, 10, 1), 0.05, 0.05),     # RDL 17/2022 arts. 5 y 6
    (D(2023, 12, 31), 0.05, 0.05),    # RDL 20/2022 art. 1
    (D(2024, 1, 1), 0.10, 0.10),      # RDL 8/2023 art. 21.2 y 21.3
    (D(2024, 4, 1), 0.21, 0.10),      # el gas vuelve al 21 % el 01/04/2024; los pellets siguen al 10 % hasta el 30/06
    (D(2024, 7, 1), 0.21, 0.21),
    (D(2026, 4, 15), 0.10, 0.10),     # RDL 7/2026 art. 42.b
    (D(2026, 7, 15), 0.21, 0.21),
    (D(2026, 10, 15), 0.21, 0.21),
])
def test_iva_gas_y_pellets(fecha, gas, pellets):
    assert I.iva_gas_natural(fecha).valor == pytest.approx(gas)
    assert I.iva_pellets(fecha).valor == pytest.approx(pellets)


def test_meses_2026_condicionados_al_ipc(tmp_path, monkeypatch):
    # Con las condiciones sin rellenar (null) los meses condicionados no tienen tipo…
    vacio = tmp_path / "c.json"
    vacio.write_text(json.dumps({"ipc": {m: {"electricidad": None, "gas": None, "glp": None, "carburantes": None} for m in ("2026-04", "2026-06", "2026-07", "2026-09", "2026-10")}}), encoding="utf-8")
    I.condiciones_ipc.cache_clear()
    monkeypatch.setattr(I, "RUTA_CONDICIONES", vacio)
    try:
        for f in (D(2026, 6, 15), D(2026, 8, 15), D(2026, 9, 15), D(2026, 11, 15), D(2026, 12, 15)):
            assert I.iee(f).valor is None and "IPC" in I.iee(f).pendiente
            assert I.ih_glp_eur_t(f).valor is None
    finally:
        I.condiciones_ipc.cache_clear()
    # …y con los valores del INE (abril: carburantes +15,5 %; electricidad y gas nunca > 15 % hasta septiembre)
    I.condiciones_ipc.cache_clear()
    monkeypatch.setattr(I, "RUTA_CONDICIONES", I.DIR_DATOS / "impuestos" / "condiciones_ipc_2026.json")
    try:
        c = I.condiciones_ipc()
        if c["2026-04"]["carburantes"] is True and c["2026-06"]["gas"] is False:
            assert I.iva_electricidad(D(2026, 6, 15), 100.0).valor == 0.21   # IPC electricidad abril -4,3 %
            assert I.iee(D(2026, 6, 15)).valor == I.IEE_GENERAL
            assert I.iva_gas_natural(D(2026, 6, 15)).valor == 0.21          # IPC gas abril -9,6 %
            assert I.ih_glp_eur_t(D(2026, 6, 15)).valor == 0.0              # IPC carburantes abril +15,5 %
            assert I.ih_gas_natural_eur_gj(D(2026, 6, 15)).valor == 0.30
            assert I.iva_butano(D(2026, 6, 15)).valor == 0.10
            assert I.ih_glp_eur_t(D(2026, 8, 15)).valor == 7.5              # junio glp -14,4 %
            assert I.ih_glp_eur_t(D(2026, 9, 15)).valor == 11.25            # julio -1,4 %, junio -14,4 %
            assert I.ih_gas_natural_eur_gj(D(2026, 9, 15)).valor == 0.56
            assert I.iva_electricidad(D(2026, 11, 15), 100.0).valor == 0.21  # septiembre +11,4 %
            assert I.ih_glp_eur_t(D(2026, 11, 15)).valor == 15.0            # septiembre +10,2 %
    finally:
        I.condiciones_ipc.cache_clear()


def test_hidrocarburos():
    assert I.ih_gas_natural_eur_gj(D(2022, 1, 1)).valor == 0.65
    assert I.ih_gas_natural_eur_kwh(D(2022, 1, 1)).valor == pytest.approx(0.00234)
    assert I.ih_glp_eur_t(D(2022, 1, 1)).valor == 15.0
    assert I.ih_gas_natural_eur_gj(D(2026, 4, 1)).valor == 0.30     # RDL 7/2026 art. 38
    assert I.ih_glp_eur_t(D(2026, 4, 1)).valor == 0.0
    assert I.ih_gas_natural_eur_gj(D(2026, 7, 1)).valor == 0.39     # RDL 18/2026 art. 5
    assert I.ih_glp_eur_t(D(2026, 7, 1)).valor == 3.75
    assert I.ih_gas_natural_eur_gj(D(2026, 10, 1)).valor == 0.65    # RDL 25/2026 art. 13
    assert I.ih_glp_eur_t(D(2026, 10, 1)).valor == 15.0


def test_pvpc_con_impuestos_enero_2022():
    # 200 €/MWh, IEE 0,5 % → cuota 1 €/MWh (mínimo), IVA 10 % (diciembre 2021: 239 €/MWh > 45)
    r = I.pvpc_con_impuestos(200.0, D(2022, 1, 15), 239.0)
    assert r.valor == pytest.approx(201.0 * 1.10)


def test_tur_con_impuestos_enero_2022():
    # TUR.2 4,520114 c€/kWh + 0,234 c€/kWh de hidrocarburos, IVA 21 %
    r = I.tur_con_impuestos(4.520114, D(2022, 1, 15))
    assert r.valor == pytest.approx((4.520114 + 0.234) * 1.21)


def test_butano_con_impuestos_enero_2022():
    # 115,9037 c€/kg × 12,5 kg = 14,488 € + 15 €/t × 0,0125 t = 0,1875 € → 14,6755 € × 1,21 = 17,76 €
    r = I.butano_bombona_con_impuestos(115.9037, D(2022, 1, 18))
    assert r.valor == pytest.approx(17.757, abs=0.001)


def test_butano_primavera_2026_iva_10_por_ciento():
    # Precio oficial del 19/05/2026: 15,39 € con 111,9680 c€/kg, IH 0 e IVA 10 %
    r = I.butano_bombona_con_impuestos(111.9680, D(2026, 5, 19))
    assert r.valor == pytest.approx(15.39, abs=0.01)


def test_butano_julio_y_septiembre_2026_con_condiciones_ipc():
    # 21/07/2026: 17,83 € (IH 3,75 €/t, IVA 21 %); 15/09/2026: 18,84 € (IH 11,25 €/t porque el IPC de
    # hidrocarburos licuados no superó el 15 % ni en junio ni en julio; IVA 21 %)
    assert I.butano_bombona_con_impuestos(117.5664, D(2026, 7, 21)).valor == pytest.approx(17.84, abs=0.01)
    r = I.butano_bombona_con_impuestos(123.4447, D(2026, 9, 15))
    if r.valor is not None:  # solo cuando las condiciones de IPC están rellenas
        assert r.valor == pytest.approx(18.84, abs=0.01)
