"""Tabla de comprobaciones: compara valores de la base de datos con valores de control tomados de la fuente.

Los valores de control se anotaron a mano leyendo la fuente original (fase 1 y 2, 25/10/2026) y están
documentados en docs/COMPROBACIONES.md. Ejecutar tras `python -m precios actualizar`:

    python scripts/comprobaciones.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from precios.config import DIR_MENSUAL, DIR_SERIES  # noqa: E402

# (serie, tipo, clave, columna, valor de control, tolerancia, origen del valor de control)
CONTROLES = [
    ("omie", "serie", "2022-01-01", "valor_original", 122.63, 0.01, "fichero marginalpdbc_20220101.1 (media de 24 horas, col. España)"),
    ("omie", "mensual", "2022-01", "media_original", 201.72, 0.01, "OMIE: precio medio del mercado diario, España, enero 2022"),
    ("omie", "mensual", "2026-09", "media_original", 143.25, 0.01, "OMIE, Informe mensual septiembre 2026, España"),
    ("omie", "serie", "2026-10-24", "valor_original", 137.19, 0.01, "fichero marginalpdbc_20261024.1 (media de 96 cuartos de hora)"),
    ("mibgas", "serie", "2022-01-03", "valor_original", 66.53, 0.001, "MIBGAS_Data_2022.xlsx, hoja Indices, ES"),
    ("mibgas", "serie", "2026-10-24", "valor_original", 92.87, 0.001, "web de MIBGAS, gráfica «Índice de precio y volumen del día de gas»"),
    ("gasoleo_a", "serie", "2022-01-03", "valor_original", 1.34715, 1e-5, "Weekly Oil Bulletin, ES_price_with_tax_diesel = 1.347,15 €/1.000 l"),
    ("gasoleo_a", "serie", "2022-01-03", "eur_kwh_sin_impuestos", 0.73435 / 10.28, 1e-6, "734,35 €/1.000 l sin impuestos ÷ 10,28 kWh/l"),
    ("gasoleo_c", "serie", "2022-01-03", "valor_original", 0.83003, 1e-5, "Weekly Oil Bulletin, ES_price_with_tax_heating_oil = 830,03 €/1.000 l"),
    ("gasoleo_c", "serie", "2026-10-19", "valor_original", 1.52133, 1e-5, "Weekly Oil Bulletin (histórico descargado el 25/10/2026)"),
    ("tur2", "serie", "2022-01-01", "valor_original", 4.520114, 1e-6, "BOE-A-2021-21356, tabla TUR.2, variable cent/kWh"),
    ("tur2", "serie", "2022-01-01", "eur_kwh_con_impuestos", (4.520114 + 0.234) * 1.21 / 100 / 0.904, 1e-6, "(4,520114 + 0,234) × 1,21 c€/kWh PCS → €/kWh PCI"),
    ("tur2", "serie", "2026-10-01", "valor_original", 5.042762, 1e-6, "BOE-A-2026-20389, tabla TUR.2"),
    ("butano", "serie", "2022-01-18", "valor_original", 115.9037, 1e-4, "BOE-A-2022-665: 115,9037 c€/kg"),
    ("butano", "serie", "2022-01-18", "eur_kwh_con_impuestos", 17.757309625 / 12.5 / 12.73, 1e-6, "bombona 17,76 € con impuestos (calculado) ÷ 12,5 kg ÷ 12,73 kWh/kg"),
    ("pellet_saco", "serie", "2026-07-01", "valor_original", 5.92, 1e-6, "AVEBIOM IPB pellet 3T2026, saco 15 kg"),
    ("pellet_granel", "serie", "2026-07-01", "valor_original", 370.24, 1e-6, "AVEBIOM IPB pellet 3T2026, granel en volquete"),
    ("pellet_saco", "serie", "2022-01-01", "valor_original", 6.53, 1e-6, "AVEBIOM IPB pellet (media anual 2022)"),
]


def main() -> int:
    fallos = 0
    print("| Serie | Clave | Columna | Base de datos | Control | Origen del control | Resultado |")
    print("|---|---|---|---|---|---|---|")
    for serie, tipo, clave, col, control, tol, origen in CONTROLES:
        try:
            if tipo == "serie":
                df = pd.read_csv(DIR_SERIES / f"{serie}.csv", dtype={"periodo": str})
                fila = df[df["fecha"] == clave]
            else:
                df = pd.read_csv(DIR_MENSUAL / f"{serie}.csv", dtype={"mes": str})
                fila = df[df["mes"] == clave]
            valor = float(fila.iloc[0][col]) if not fila.empty else None
        except FileNotFoundError:
            valor = None
        ok = valor is not None and abs(valor - control) <= tol
        fallos += 0 if ok else 1
        v = "no disponible" if valor is None else f"{valor:.6f}"
        print(f"| {serie} | {clave} | {col} | {v} | {control:.6f} | {origen} | {'OK' if ok else 'FALLA'} |")
    print(f"\n{len(CONTROLES) - fallos} de {len(CONTROLES)} comprobaciones correctas")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
