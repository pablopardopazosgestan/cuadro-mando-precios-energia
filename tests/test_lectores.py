"""Lectores de cada fuente, con muestras mínimas en memoria y con los documentos originales guardados."""
import datetime as dt
import io
from pathlib import Path

import openpyxl
import pytest

from precios.fuentes import avebiom, boe, esios, mibgas, omie, wob

RAIZ = Path(__file__).resolve().parent.parent
ORIGINALES = RAIZ / "datos" / "fuentes_originales"


# ---------------------------------------------------------------- OMIE

OMIE_2022 = "MARGINALPDBC;\n" + "".join(f"2022;01;01;{h};{100 + h};{200 + h};\n" for h in range(1, 25)) + "*\n"


def test_omie_lee_fichero_horario():
    d = omie.leer_fichero(OMIE_2022)
    assert d.fecha == dt.date(2022, 1, 1) and d.periodos == 24
    assert d.media_es == pytest.approx(212.5)   # columna 6 = España
    assert d.media_pt == pytest.approx(112.5)
    assert (d.minimo_es, d.maximo_es) == (201.0, 224.0)


def test_omie_lee_fichero_cuartohorario_y_cambio_de_hora():
    texto = "MARGINALPDBC;\n" + "".join(f"2026;10;25;{p};50;60;\n" for p in range(1, 101)) + "*\n"
    assert omie.leer_fichero(texto).periodos == 100


def test_omie_rechaza_html_y_periodos_raros():
    assert omie.leer_fichero("<!DOCTYPE html><html>...") is None
    with pytest.raises(ValueError):
        omie.leer_fichero("MARGINALPDBC;\n2022;01;01;1;1;1;\n*\n")


# ---------------------------------------------------------------- MIBGAS

def _xlsx(hojas: dict[str, list[list]]) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for nombre, filas in hojas.items():
        ws = wb.create_sheet(nombre)
        for f in filas:
            ws.append(f)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_mibgas_formato_2022():
    contenido = _xlsx({"Indices": [
        ["Delivery day", "Area", "MIBGAS Index\n[EUR/MWh]", "MIBGAS Volume\n[MWh]"],
        [dt.datetime(2022, 1, 3), "ES", 66.53, 157146.0],
        [dt.datetime(2022, 1, 3), "PT", 99.0, 0.0],
        [dt.datetime(2022, 1, 2), "ES", 60.0, 1.0],
    ]})
    dias = mibgas.leer_excel(contenido)
    assert [(d.fecha, d.indice_es) for d in dias] == [(dt.date(2022, 1, 2), 60.0), (dt.date(2022, 1, 3), 66.53)]


def test_mibgas_formato_2023():
    contenido = _xlsx({"MIBGAS Indexes": [
        ["Delivery day", "MIBGAS PVB Last Price Index Day-Ahead\n[EUR/MWh]", "MIBGAS-ES Index\n[EUR/MWh]", "MIBGAS-PT Index\n[EUR/MWh]"],
        [dt.datetime(2026, 10, 25), 92.33, None, None],     # día sin índice todavía
        [dt.datetime(2026, 10, 24), 92.33, 92.87, 92.73],
    ]})
    dias = mibgas.leer_excel(contenido)
    assert [(d.fecha, d.indice_es) for d in dias] == [(dt.date(2026, 10, 24), 92.87)]


def test_mibgas_sin_hoja_de_indices():
    with pytest.raises(ValueError):
        mibgas.leer_excel(_xlsx({"Otra": [["a"]]}))


# ---------------------------------------------------------------- Weekly Oil Bulletin

def _wob_xlsx():
    cab = ["Consumer prices", "CTR", "ES_price_with_tax_euro95", "ES_price_with_tax_diesel", "ES_price_with_tax_heating_oil"]
    cab2 = [c.replace("with_tax", "wo_tax") for c in cab]
    return _xlsx({
        "Prices with taxes": [cab, [None] * 5, ["Date", None, "1000 l", "1000 l", "1000 l"],
                              [dt.datetime(2022, 1, 3), "ES_", 1479.63, 1347.15, 830.03],
                              [dt.datetime(2022, 1, 10), "ES_", 1489.51, 1359.84, None]],
        "Prices wo taxes": [cab2, [None] * 5, ["Date", None, "1000 l", "1000 l", "1000 l"],
                            [dt.datetime(2022, 1, 3), "ES_", 750.14, 734.35, 589.27]],
    })


def test_wob_lee_columnas_espanolas():
    semanas = wob.leer_excel(_wob_xlsx())
    assert semanas[0] == wob.SemanaWob(dt.date(2022, 1, 3), 1347.15, 734.35, 830.03, 589.27)
    assert semanas[1].calef_con is None and semanas[1].diesel_sin is None


def test_wob_localiza_enlace():
    html = '<a href="/document/download/abc_en?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx">x</a>'
    assert wob.localizar_url_historico(html).endswith("Prices_History_maticni_4web.xlsx")
    with pytest.raises(ValueError):
        wob.localizar_url_historico("<html></html>")


# ---------------------------------------------------------------- BOE

@pytest.mark.skipif(not (ORIGINALES / "boe" / "BOE-A-2021-21356.xml").exists(), reason="falta el XML original")
def test_boe_tur_enero_2022():
    doc = boe.leer_xml((ORIGINALES / "boe" / "BOE-A-2021-21356.xml").read_bytes())
    r = boe.parsear_tur(doc)
    assert r.fecha_publicacion == dt.date(2021, 12, 25)
    assert r.fecha_efectos == dt.date(2022, 1, 1)
    assert r.tarifas["TUR.2"] == (10.24, 4.520114)
    assert r.tarifas["TUR.1"] == (5.44, 4.862181)


@pytest.mark.skipif(not (ORIGINALES / "boe" / "BOE-A-2026-20389.xml").exists(), reason="falta el XML original")
def test_boe_tur_octubre_2026_con_once_tramos():
    r = boe.parsear_tur(boe.leer_xml((ORIGINALES / "boe" / "BOE-A-2026-20389.xml").read_bytes()))
    assert r.fecha_efectos == dt.date(2026, 10, 1)
    assert r.tarifas["TUR.2"] == (8.17, 5.042762)


@pytest.mark.skipif(not (ORIGINALES / "boe" / "BOE-A-2022-665.xml").exists(), reason="falta el XML original")
def test_boe_butano_enero_2022():
    r = boe.parsear_butano(boe.leer_xml((ORIGINALES / "boe" / "BOE-A-2022-665.xml").read_bytes()))
    assert r.fecha_efectos == dt.date(2022, 1, 18)
    assert r.precio_sin_impuestos_ckg == 115.9037


def test_boe_patrones_de_titulo():
    r = "Resolución de 12 de enero de 2022, de la Dirección General de Política Energética y Minas, por la que se publican los nuevos "
    assert boe.RE_BUTANO.search(r + "precios máximos de venta, antes de impuestos, de los gases licuados del petróleo envasados, en envases…")
    assert boe.RE_BUTANO.search(r + "precios máximos de venta, antes de impuestos, del butano comercial envasado en envases de carga…")
    assert not boe.RE_BUTANO.search(r + "precios de venta, antes de impuestos, de los gases licuados del petróleo por canalización.")
    # Una orden ministerial que modifica el sistema de precios no es una revisión de precios
    assert not boe.RE_BUTANO.search("Orden TED/211/2025, de 4 de marzo, por la que se modifica la Orden IET/389/2015, de 5 de marzo, por la que se actualiza el sistema de determinación automática de precios máximos de venta, antes de impuestos, de los gases licuados del petróleo envasados")
    assert boe.RE_TUR.search("Resolución de 22 de diciembre de 2021, de la Dirección General de Política Energética y Minas, por la que se publica la tarifa de último recurso de gas natural.")
    assert not boe.RE_TUR.search("Orden ITC/1660/2009, de 22 de junio, por la que se establece la metodología de cálculo de la tarifa de último recurso de gas natural.")


# ---------------------------------------------------------------- AVEBIOM

PDF_3T2026 = ORIGINALES / "avebiom" / "IPB-indice-precios-PELLET-3T2026.pdf"


@pytest.mark.skipif(not PDF_3T2026.exists(), reason="falta el PDF original")
def test_avebiom_lee_pdf_3t2026():
    precios, actualizacion = avebiom.leer_pdf(PDF_3T2026.read_bytes(), PDF_3T2026.name)
    assert actualizacion == "octubre 2026"
    d = {(p.periodo, p.formato): p for p in precios}
    assert d[("2026T3", "saco")].precio == 5.92 and d[("2026T3", "saco")].ckwh_avebiom == 8.28
    assert d[("2026T3", "volquete")].precio == 370.24 and d[("2026T3", "volquete")].ckwh_avebiom == 7.77
    assert d[("2025T3", "saco")].precio == 5.12
    assert d[("2022", "saco")].precio == 6.53 and d[("2022", "volquete")].precio == 407.88
    assert d[("2024", "cisterna")].precio == 344.97


# ---------------------------------------------------------------- ESIOS

def test_esios_lee_respuesta_y_promedia_por_dia():
    import json
    valores = [{"value": 100 + h, "datetime": f"2022-01-01T{h:02d}:00:00.000+01:00", "geo_id": 8741} for h in range(24)]
    valores += [{"value": 999, "datetime": "2022-01-01T00:00:00.000+01:00", "geo_id": 8742}]  # otra zona: se ignora
    valores += [{"value": 50, "datetime": "2022-01-02T00:00:00.000+01:00", "geo_id": 8741}]
    cuerpo = json.dumps({"indicator": {"values": valores}}).encode()
    dias = esios.leer_respuesta(cuerpo)
    assert dias[0].fecha == dt.date(2022, 1, 1) and dias[0].n_valores == 24 and dias[0].media_eur_mwh == pytest.approx(111.5)
    assert dias[1].media_eur_mwh == 50


def test_esios_sin_token(monkeypatch):
    monkeypatch.delenv("ESIOS_TOKEN", raising=False)
    with pytest.raises(esios.FaltaToken):
        esios.token()


@pytest.mark.skipif(not (ORIGINALES / "boe" / "BOE-A-2023-15235.xml").exists(), reason="falta el XML original")
def test_boe_correccion_de_errores_tur_junio_2023():
    original = boe.ResolucionTUR("BOE-A-2023-X", "Resolución de 27 de junio de 2023, de la Dirección General de Política Energética y Minas, por la que se publica la tarifa de último recurso de gas natural.",
                                 dt.date(2023, 6, 29), dt.date(2023, 7, 1), {"TUR.2": (9.48, 9.99)})
    doc = boe.leer_xml((ORIGINALES / "boe" / "BOE-A-2023-15235.xml").read_bytes())
    assert boe.RE_CORRECCION.search(doc.titulo)
    assert boe.aplicar_correccion_tur([original], doc)
    assert original.tarifas["TUR.2"] == (9.48, 4.020647)
    assert "corregida por BOE-A-2023-15235" in original.titulo


def test_avebiom_solo_consulta_cuando_puede_haber_trimestre_nuevo(monkeypatch):
    p = avebiom.PrecioPellet("2026T3", "saco", 5.92, 8.28, "3T2026.pdf")
    inf = avebiom.InformePellet("3T2026.pdf", "u", dt.date(2026, 10, 20), "octubre 2026", (p,))
    assert avebiom.ultimo_trimestre([inf]) == (2026, 3)
    assert not avebiom.toca_consultar([inf], dt.date(2026, 12, 31))       # el 4T2026 aún no ha cerrado
    assert not avebiom.toca_consultar([inf], dt.date(2027, 1, 14))        # cerrado, pero dentro del plazo de publicación
    assert avebiom.toca_consultar([inf], dt.date(2027, 1, 15))
    assert avebiom.toca_consultar([], dt.date(2026, 1, 1))                # sin PDF guardados, siempre
    p4 = avebiom.PrecioPellet("2026T4", "saco", 6.0, None, "4T2026.pdf")
    assert avebiom.ultimo_trimestre([inf, avebiom.InformePellet("4T2026.pdf", "u", None, None, (p4,))]) == (2026, 4)

    llamadas = []
    monkeypatch.setattr(avebiom, "informes_locales", lambda: [inf])
    monkeypatch.setattr(avebiom, "listar_pdfs", lambda: llamadas.append("web") or [(dt.date(2027, 1, 20), "https://x/4T2026.pdf"), (dt.date(2026, 10, 20), "https://x/3T2026.pdf")])
    monkeypatch.setattr(avebiom, "descargar_informe", lambda f, u: avebiom.InformePellet(u.rsplit("/", 1)[-1], u, f, None, ()))
    assert avebiom.descargar_todo(dt.date(2026, 10, 27)) == [inf] and llamadas == []          # no toca: solo los locales
    res = avebiom.descargar_todo(dt.date(2027, 1, 20))
    assert llamadas == ["web"] and [i.nombre_pdf for i in res] == ["3T2026.pdf", "4T2026.pdf"]  # solo descarga el nuevo
    assert len(avebiom.descargar_todo(dt.date(2026, 10, 27), forzar=True)) == 2 and llamadas == ["web", "web"]


def test_avebiom_reintenta_el_listado_y_falla_con_error_claro(monkeypatch):
    from precios.http import ErrorDescarga
    intentos = []
    monkeypatch.setattr(avebiom, "ESPERAS_TRAS_FALLO", (0, 0))
    monkeypatch.setattr(avebiom, "listar_pdfs", lambda: intentos.append(1) or (_ for _ in ()).throw(ErrorDescarga("captcha")))
    with pytest.raises(ErrorDescarga, match="captcha"):
        avebiom.listar_pdfs_con_reintentos()
    assert len(intentos) == 3
    intentos.clear()
    monkeypatch.setattr(avebiom, "listar_pdfs", lambda: intentos.append(1) or ([(dt.date(2026, 1, 1), "https://x/a.pdf")] if len(intentos) == 2 else (_ for _ in ()).throw(ErrorDescarga("captcha"))))
    assert avebiom.listar_pdfs_con_reintentos() == [(dt.date(2026, 1, 1), "https://x/a.pdf")] and len(intentos) == 2


def test_avebiom_informes_locales_leen_el_indice():
    locales = avebiom.informes_locales()
    nombres = {i.nombre_pdf: i for i in locales}
    assert "IPB-indice-precios-PELLET-3T2026.pdf" in nombres
    assert nombres["IPB-indice-precios-PELLET-3T2026.pdf"].fecha_subida == dt.date(2026, 10, 20)
    assert avebiom.ultimo_trimestre(locales) >= (2026, 3)
