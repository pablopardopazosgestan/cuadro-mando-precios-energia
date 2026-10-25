import datetime as dt

import pandas as pd
import pytest

from precios import series as S
from precios.fuentes import avebiom


def _df(filas):
    return pd.DataFrame([S._fila(*f) for f in filas], columns=S.COLUMNAS)


def test_fusionar_conserva_historico_y_sustituye_repetidos():
    viejo = _df([(dt.date(2022, 1, 1), "2022-01-01", 1.0, "u", 1.0, None, "x"), (dt.date(2022, 1, 2), "2022-01-02", 2.0, "u", 2.0, None, "x")])
    nuevo = _df([(dt.date(2022, 1, 2), "2022-01-02", 2.5, "u", 2.5, None, "x"), (dt.date(2022, 1, 3), "2022-01-03", 3.0, "u", 3.0, None, "x")])
    f = S.fusionar(viejo, nuevo).sort_values("fecha")
    assert list(f["valor_original"]) == [1.0, 2.5, 3.0]


def test_media_mensual_regulado_pondera_por_dias():
    # TUR 2 cambia el 16 de enero: 10 días a 4 y 15... no: 15 días a 4 (1–15) y 16 días a 6 (16–31)
    s = _df([(dt.date(2021, 12, 1), "2021-12-01", 4.0, "c€/kWh", 0.04, 0.05, "calculado"),
             (dt.date(2022, 1, 16), "2022-01-16", 6.0, "c€/kWh", 0.06, 0.07, "calculado")])
    mm = S.media_mensual("tur2", s, dt.date(2022, 1, 31))
    ene = mm[mm["mes"] == "2022-01"].iloc[0]
    assert ene["media_original"] == pytest.approx((15 * 4 + 16 * 6) / 31)
    assert ene["n_datos"] == 31


def test_media_mensual_diaria_sin_impuestos_incompletos():
    s = _df([(dt.date(2022, 1, 1), "2022-01-01", 100.0, "€/MWh", 0.1, 0.12, "calculado"),
             (dt.date(2022, 1, 2), "2022-01-02", 200.0, "€/MWh", 0.2, None, "no disponible")])
    mm = S.media_mensual("pvpc", s, dt.date(2022, 1, 31))
    assert mm.iloc[0]["media_original"] == 150.0
    assert pd.isna(mm.iloc[0]["media_eur_kwh_con_impuestos"])


def test_construir_pellet_prefiere_trimestres_y_usa_anual_solo_sin_trimestres():
    p = avebiom.PrecioPellet
    inf1 = avebiom.InformePellet("4T2025.pdf", "u", dt.date(2026, 2, 4), "enero 2026",
                                 (p("2022", "saco", 6.53, 9.14, "4T2025.pdf"), p("2024", "saco", 5.25, 7.35, "4T2025.pdf"),
                                  p("2025", "saco", 5.15, 7.21, "4T2025.pdf"),
                                  p("2024T4", "saco", 5.17, 7.23, "4T2025.pdf"), p("2025T1", "saco", 5.04, 7.05, "4T2025.pdf"),
                                  p("2025T2", "saco", 5.14, 7.19, "4T2025.pdf"), p("2025T3", "saco", 5.12, 7.17, "4T2025.pdf"),
                                  p("2025T4", "saco", 5.31, 7.43, "4T2025.pdf")))
    inf2 = avebiom.InformePellet("3T2026.pdf", "u", dt.date(2026, 10, 20), "octubre 2026",
                                 (p("2025T4", "saco", 5.31, 7.43, "3T2026.pdf"), p("2026T3", "saco", 5.92, 8.28, "3T2026.pdf")))
    df = S.construir_pellet([inf1, inf2], "saco")
    periodos = list(df["periodo"])
    assert "2022" in periodos                      # anual: no hay trimestres de 2022
    assert "2024" in periodos                      # 2024 solo tiene el 4T: la media anual cubre los meses restantes
    assert "2025" not in periodos                  # 2025 completo por trimestres
    assert periodos[-1] == "2026T3"
    fila = df[df["periodo"] == "2026T3"].iloc[0]
    assert fila["referencia"] == "3T2026.pdf" and fila["eur_kwh_con_impuestos"] == pytest.approx(5.92 / 15 / 4.8)


def test_media_mensual_pellet_trimestre_manda_sobre_anual():
    s = _df([(dt.date(2024, 1, 1), "2024", 5.25, "€/saco", None, 0.0729, "original"),
             (dt.date(2024, 10, 1), "2024T4", 5.17, "€/saco", None, 0.0718, "original")])
    mm = S.media_mensual("pellet_saco", s, dt.date(2024, 12, 31)).set_index("mes")
    assert len(mm) == 12
    assert mm.loc["2024-03", "media_original"] == 5.25 and "anual" in mm.loc["2024-03", "metodo"]
    assert mm.loc["2024-11", "media_original"] == 5.17 and "trimestre" in mm.loc["2024-11", "metodo"]
