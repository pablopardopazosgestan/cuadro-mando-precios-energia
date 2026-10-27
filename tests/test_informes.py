"""Generación de informes: prueba de humo sobre los datos reales del repositorio."""
import datetime as dt
from pathlib import Path

import openpyxl
import pdfplumber
import pytest

from precios import informes

DATOS = Path(__file__).resolve().parent.parent / "datos" / "series"


@pytest.mark.skipif(not (DATOS / "omie.csv").exists(), reason="sin datos")
def test_generar_pdf_y_excel(tmp_path, monkeypatch):
    monkeypatch.setattr(informes, "DIR_INFORMES", tmp_path)
    salidas = informes.generar(hoy=dt.date(2026, 10, 27))
    pdf, xlsx = salidas
    assert pdf.exists() and xlsx.exists()
    with pdfplumber.open(pdf) as doc:
        assert len(doc.pages) >= 3
        texto = doc.pages[0].extract_text()
        assert "Claves de la semana" in texto and "OMIE" in texto and "€/kWh" in texto
        assert "Precios y variaciones" in doc.pages[1].extract_text()
        assert "Fuentes y metodología" in doc.pages[-1].extract_text()
    wb = openpyxl.load_workbook(xlsx)
    assert {"Cuadro de mando", "Anual", "Mensual", "Gráficos", "Fuentes y criterios"} <= set(wb.sheetnames)
    assert len(wb["Gráficos"]._charts) == 11            # comparativo + barras anuales + 9 individuales
    assert len(wb["Cuadro de mando"]._charts) == 1
    datos_omie = wb["Datos 1 OMIE"]
    assert "Datos_omie" in datos_omie.tables              # tabla de Excel filtrable
    assert datos_omie.max_row > 2000                      # histórico diario completo
    assert wb["Mensual"]["A2"].value == "2020-01"
    assert wb["Anual"]["A2"].value == 2020
