import datetime as dt

import pytest

from precios import conversiones as cv


def test_omie_eur_mwh_a_kwh():
    assert cv.eur_mwh_a_eur_kwh(201.72) == pytest.approx(0.20172)


def test_gasoleo_1000l_a_kwh():
    # 1.347,15 €/1.000 l (gasóleo A, 03/01/2022, con impuestos) → 1,34715 €/l → 0,13104 €/kWh con 10,28 kWh/l
    assert cv.eur_1000l_a_eur_kwh(1347.15) == pytest.approx(1.34715 / 10.28)
    assert cv.eur_litro_a_eur_kwh(1.34715) == pytest.approx(0.131045, abs=1e-6)


def test_tur_pcs_a_pci():
    # 4,520114 c€/kWh PCS → 0,04520114 €/kWh PCS → /0,904 = 0,0500013 €/kWh PCI
    assert cv.ckwh_pcs_a_eur_kwh_pci(4.520114) == pytest.approx(0.0500013, abs=1e-6)


def test_butano_bombona_a_kwh():
    # 17,757 € la bombona de 12,5 kg → 1,4206 €/kg → /12,73 = 0,11159 €/kWh
    assert cv.eur_bombona_a_eur_kwh(17.757) == pytest.approx(17.757 / 12.5 / 12.73)


def test_pellet_saco_y_tonelada():
    # AVEBIOM 3T2026: 5,92 €/saco = 8,28 c€/kWh con 4,76 kWh/kg; con 4,8 kWh/kg sale 8,22 c€/kWh
    assert cv.eur_saco_a_eur_kwh(5.92, cv.PELLET_AVEBIOM_KWH_KG) * 100 == pytest.approx(8.29, abs=0.01)
    assert cv.eur_saco_a_eur_kwh(5.92) * 100 == pytest.approx(8.22, abs=0.01)
    assert cv.eur_tonelada_a_eur_kwh(370.24, cv.PELLET_AVEBIOM_KWH_KG) * 100 == pytest.approx(7.78, abs=0.01)
    assert cv.eur_tonelada_a_eur_kwh(370.24) * 100 == pytest.approx(7.71, abs=0.01)


def test_factores_tienen_procedencia():
    for f in (cv.PELLET_KWH_KG, cv.GASOLEO_KWH_L, cv.BUTANO_KWH_KG, cv.GAS_NATURAL_PCI_PCS, cv.PELLET_AVEBIOM_KWH_KG):
        assert f.procedencia and f.valor > 0
