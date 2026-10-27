"""Impuestos vigentes en cada fecha, con su referencia al BOE.

Todos los tramos proceden de la lectura de los textos en el BOE (fase 2, 25/10/2026). Las
normas de 2026 (RDL 7/2026, 18/2026 y 25/2026) condicionan varios tipos a la variación del IPC
que publica el INE; esas condiciones se leen de `datos/impuestos/condiciones_ipc_2026.json` y,
mientras no estén comprobadas, el tipo se devuelve como «no disponible» (valor None) en lugar
de suponerlo.

Referencias (identificadores del BOE):
- Ley 37/1992 (IVA), art. 90: tipo general 21 %.
- Ley 38/1992 (Impuestos Especiales), art. 50 (hidrocarburos: epígrafes 1.8 GLP usos distintos de
  carburante, 15 €/t; 1.10.1 gas natural usos distintos de carburante, 0,65 €/GJ) y arts. 99 y 102
  (electricidad: 5,11269632 %, cuota mínima 1 €/MWh en usos no industriales).
- RDL 12/2021 (BOE-A-2021-10584): IVA electricidad 10 % desde 26/06/2021 (contratos ≤10 kW, si el
  precio medio del mercado mayorista del mes anterior supera 45 €/MWh).
- RDL 17/2021 (BOE-A-2021-14974): IEE 0,5 % desde 16/09/2021.
- RDL 29/2021 (BOE-A-2021-21096) y RDL 6/2022 (BOE-A-2022-4972): prórrogas hasta 30/06/2022.
- RDL 11/2022 (BOE-A-2022-10557): IVA electricidad 5 % desde 01/07/2022; IEE 0,5 % hasta 31/12/2022.
- RDL 17/2022 (BOE-A-2022-15354): IVA gas natural y pellets 5 % desde 01/10/2022.
- RDL 20/2022 (BOE-A-2022-22685): prórroga de todo lo anterior hasta 31/12/2023.
- RDL 8/2023 (BOE-A-2023-26452): 2024: IVA electricidad 10 % (condición 45 €/MWh) todo el año; IVA gas
  10 % hasta 31/03/2024; IVA pellets 10 % hasta 30/06/2024; IEE 2,5 % (1T) y 3,8 % (2T).
- RDL 7/2026 (BOE-A-2026-6544, en vigor 22/03/2026): hasta 30/06/2026 IEE 0,5 %, IVA 10 % electricidad
  (<10 kW), gas natural y pellets; hidrocarburos: gas 1.10.1 a 0,30 €/GJ y GLP 1.8 a 0 €/t. En junio,
  solo si el IPC de abril superó el 15 % interanual.
- RDL 18/2026 (BOE-A-2026-14112): julio–septiembre de 2026 (tipos mensuales de hidrocarburos; IVA e IEE
  reducidos en agosto/septiembre solo si el IPC de junio/julio superó el 15 %).
- RDL 25/2026 (BOE-A-2026-20265): octubre–diciembre de 2026 (igual esquema; noviembre y diciembre según
  el IPC de septiembre y octubre).
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import DIR_DATOS

IVA_GENERAL = 0.21
IEE_GENERAL = 0.0511269632
IEE_CUOTA_MINIMA_EUR_MWH = 1.0        # Ley 38/1992 art. 99.2.b (usos no industriales)
IH_GAS_GENERAL_EUR_GJ = 0.65           # epígrafe 1.10.1
IH_GLP_GENERAL_EUR_T = 15.0            # epígrafe 1.8
GJ_POR_KWH = 0.0036
UMBRAL_OMIE_EUR_MWH = 45.0

RDL7_2026_VIGOR = dt.date(2026, 3, 22)
RUTA_CONDICIONES = DIR_DATOS / "impuestos" / "condiciones_ipc_2026.json"


@dataclass(frozen=True)
class Tipo:
    """Un tipo impositivo aplicable en una fecha. `valor` None = no disponible (ver `pendiente`)."""
    valor: float | None
    referencia: str
    pendiente: str | None = None

    @property
    def disponible(self) -> bool:
        return self.valor is not None


@lru_cache(maxsize=1)
def condiciones_ipc() -> dict:
    """Condiciones de IPC leídas del JSON (la ruta se resuelve en cada llamada para poder sustituirla en pruebas)."""
    return json.loads(RUTA_CONDICIONES.read_text(encoding="utf-8"))["ipc"]


def _ipc(mes: str, subclase: str) -> bool | None:
    return condiciones_ipc().get(mes, {}).get(subclase)


def _pendiente(mes: str, subclase: str) -> str:
    return f"depende de si el IPC de {subclase} de {mes} superó el 15 % interanual; dato del INE no comprobado"


def _condicional(fecha_mes: str, mes_ipc: str, subclase: str, si: float, no: float, ref: str) -> Tipo:
    c = _ipc(mes_ipc, subclase)
    if c is None:
        return Tipo(None, ref, _pendiente(mes_ipc, subclase))
    return Tipo(si if c else no, ref)


def _condicional_doble(mes_ipc: str, mes_ipc_previo: str, subclase: str, si: float, si_previo: float, no: float, ref: str) -> Tipo:
    """Tipo que depende del IPC de un mes y, si no se cumple, del IPC del mes anterior (hidrocarburos)."""
    c = _ipc(mes_ipc, subclase)
    if c is None:
        return Tipo(None, ref, _pendiente(mes_ipc, subclase))
    if c:
        return Tipo(si, ref)
    p = _ipc(mes_ipc_previo, subclase)
    if p is None:
        return Tipo(None, ref, _pendiente(mes_ipc_previo, subclase))
    return Tipo(si_previo if p else no, ref)


def _ym(fecha: dt.date) -> str:
    return f"{fecha:%Y-%m}"


# ------------------------------------------------------------------ IVA electricidad

def iva_electricidad(fecha: dt.date, omie_mes_anterior: float | None) -> Tipo:
    """IVA de la electricidad para un consumidor doméstico (≤10 kW) en `fecha`.

    `omie_mes_anterior`: precio medio aritmético del mercado diario (€/MWh) del mes natural anterior,
    necesario entre 26/06/2021 y 31/12/2024 (condición de los 45 €/MWh).
    """
    if fecha < dt.date(2021, 6, 26):
        return Tipo(IVA_GENERAL, "Ley 37/1992 art. 90")
    if fecha <= dt.date(2024, 12, 31):
        if fecha <= dt.date(2022, 6, 30):
            reducido, ref = 0.10, "RDL 12/2021 art. 1 (prorrogado por RDL 29/2021 y RDL 6/2022)"
        elif fecha <= dt.date(2023, 12, 31):
            reducido, ref = 0.05, "RDL 11/2022 art. 18 (prorrogado por RDL 20/2022)"
        else:
            reducido, ref = 0.10, "RDL 8/2023 art. 21.1"
        if omie_mes_anterior is None:
            return Tipo(None, ref, "falta el precio medio de OMIE del mes anterior para aplicar la condición de 45 €/MWh")
        return Tipo(reducido if omie_mes_anterior > UMBRAL_OMIE_EUR_MWH else IVA_GENERAL, ref + " (condición: mes anterior > 45 €/MWh)")
    if fecha < RDL7_2026_VIGOR:
        return Tipo(IVA_GENERAL, "Ley 37/1992 art. 90 (sin medidas vigentes)")
    return _iva_2026(fecha, "electricidad", "IVA electricidad", 0.10)


def _iva_2026(fecha: dt.date, subclase: str, nombre: str, reducido: float) -> Tipo:
    m = _ym(fecha)
    if m in ("2026-03", "2026-04", "2026-05"):
        return Tipo(reducido, f"RDL 7/2026 art. 42 ({nombre} 10 % hasta 30/06/2026)")
    if m == "2026-06":
        return _condicional(m, "2026-04", subclase, reducido, IVA_GENERAL, "RDL 7/2026 art. 42 (junio: condición IPC de abril)")
    if m == "2026-07":
        return Tipo(IVA_GENERAL, "Ley 37/1992 art. 90 (RDL 18/2026 no reduce el IVA en julio)")
    if m == "2026-08":
        return _condicional(m, "2026-06", subclase, reducido, IVA_GENERAL, "RDL 18/2026 art. 10 (agosto: condición IPC de junio)")
    if m == "2026-09":
        return _condicional(m, "2026-07", subclase, reducido, IVA_GENERAL, "RDL 18/2026 art. 11 (septiembre: condición IPC de julio)")
    if m == "2026-10":
        return Tipo(IVA_GENERAL, "Ley 37/1992 art. 90 (RDL 25/2026 no reduce el IVA en octubre)")
    if m == "2026-11":
        return _condicional(m, "2026-09", subclase, reducido, IVA_GENERAL, "RDL 25/2026 art. 18 (noviembre: condición IPC de septiembre)")
    if m == "2026-12":
        return _condicional(m, "2026-10", subclase, reducido, IVA_GENERAL, "RDL 25/2026 art. 19 (diciembre: condición IPC de octubre)")
    return Tipo(None, "sin norma leída", f"no hay tabla de impuestos para {m}: hay que revisar el BOE")


# ------------------------------------------------------------------ Impuesto especial sobre la electricidad

def iee(fecha: dt.date) -> Tipo:
    if fecha < dt.date(2021, 9, 16):
        return Tipo(IEE_GENERAL, "Ley 38/1992 art. 99")
    if fecha <= dt.date(2023, 12, 31):
        return Tipo(0.005, "RDL 17/2021 DA 6ª (prorrogado por RDL 29/2021, 6/2022, 11/2022 y 20/2022)")
    if fecha <= dt.date(2024, 3, 31):
        return Tipo(0.025, "RDL 8/2023 art. 22.1")
    if fecha <= dt.date(2024, 6, 30):
        return Tipo(0.038, "RDL 8/2023 art. 22.1")
    if fecha < RDL7_2026_VIGOR:
        return Tipo(IEE_GENERAL, "Ley 38/1992 art. 99 (sin medidas vigentes)")
    m = _ym(fecha)
    if m in ("2026-03", "2026-04", "2026-05"):
        return Tipo(0.005, "RDL 7/2026 art. 40.Uno")
    if m == "2026-06":
        return _condicional(m, "2026-04", "electricidad", 0.005, IEE_GENERAL, "RDL 7/2026 art. 40.Dos (junio: condición IPC de abril)")
    if m == "2026-07":
        return Tipo(IEE_GENERAL, "Ley 38/1992 art. 99 (RDL 18/2026 no reduce el IEE en julio)")
    if m == "2026-08":
        return _condicional(m, "2026-06", "electricidad", 0.005, IEE_GENERAL, "RDL 18/2026 art. 12")
    if m == "2026-09":
        return _condicional(m, "2026-07", "electricidad", 0.005, IEE_GENERAL, "RDL 18/2026 art. 13")
    if m == "2026-10":
        return Tipo(IEE_GENERAL, "Ley 38/1992 art. 99 (RDL 25/2026 no reduce el IEE en octubre)")
    if m == "2026-11":
        return _condicional(m, "2026-09", "electricidad", 0.005, IEE_GENERAL, "RDL 25/2026 art. 20")
    if m == "2026-12":
        return _condicional(m, "2026-10", "electricidad", 0.005, IEE_GENERAL, "RDL 25/2026 art. 21")
    return Tipo(None, "sin norma leída", f"no hay tabla de impuestos para {m}: hay que revisar el BOE")


def cuota_iee_eur_mwh(base_eur_mwh: float, fecha: dt.date) -> float | None:
    """Cuota del IEE por MWh sobre un importe base (€/MWh), con la cuota mínima de 1 €/MWh.

    Aproximación documentada: en la factura real la base del IEE incluye también el término de
    potencia; aquí se aplica solo al término de energía, que es lo que mide el indicador.
    """
    t = iee(fecha)
    if t.valor is None:
        return None
    return max(base_eur_mwh * t.valor, IEE_CUOTA_MINIMA_EUR_MWH)


# ------------------------------------------------------------------ IVA gas natural y pellets

def iva_gas_natural(fecha: dt.date) -> Tipo:
    if fecha < dt.date(2022, 10, 1):
        return Tipo(IVA_GENERAL, "Ley 37/1992 art. 90")
    if fecha <= dt.date(2023, 12, 31):
        return Tipo(0.05, "RDL 17/2022 art. 5 (prorrogado por RDL 20/2022 art. 1)")
    if fecha <= dt.date(2024, 3, 31):
        return Tipo(0.10, "RDL 8/2023 art. 21.2")
    if fecha < RDL7_2026_VIGOR:
        return Tipo(IVA_GENERAL, "Ley 37/1992 art. 90 (sin medidas vigentes)")
    return _iva_2026(fecha, "gas", "IVA gas natural", 0.10)


def iva_pellets(fecha: dt.date) -> Tipo:
    if fecha < dt.date(2022, 10, 1):
        return Tipo(IVA_GENERAL, "Ley 37/1992 art. 90")
    if fecha <= dt.date(2023, 12, 31):
        return Tipo(0.05, "RDL 17/2022 art. 6 (prorrogado por RDL 20/2022 art. 1)")
    if fecha <= dt.date(2024, 6, 30):
        return Tipo(0.10, "RDL 8/2023 art. 21.3")
    if fecha < RDL7_2026_VIGOR:
        return Tipo(IVA_GENERAL, "Ley 37/1992 art. 90 (sin medidas vigentes)")
    return _iva_2026(fecha, "gas", "IVA pellets (misma letra que el gas natural)", 0.10)


def iva_butano(fecha: dt.date) -> Tipo:
    """IVA del butano envasado: 21 %, salvo el 10 % del RDL 7/2026 art. 42.c (22/03–31/05/2026 y junio
    según el IPC de carburantes de abril). Que el 42.c se aplicó al butano envasado lo confirma el precio
    oficial de la bombona del 19/05/2026 (15,39 € = 111,9680 c€/kg × 12,5 kg × 1,10) y la subida de julio
    «por el fin de la rebaja del IVA»."""
    if RDL7_2026_VIGOR <= fecha <= dt.date(2026, 5, 31):
        return Tipo(0.10, "RDL 7/2026 art. 42.c (epígrafe 1.8)")
    if _ym(fecha) == "2026-06":
        return _condicional("2026-06", "2026-04", "carburantes", 0.10, IVA_GENERAL, "RDL 7/2026 art. 42.c (junio: condición IPC de carburantes de abril)")
    return Tipo(IVA_GENERAL, "Ley 37/1992 art. 90")


# ------------------------------------------------------------------ Impuesto sobre hidrocarburos

def ih_gas_natural_eur_gj(fecha: dt.date) -> Tipo:
    """Epígrafe 1.10.1 (gas natural para usos distintos del carburante), €/GJ sobre PCS."""
    if fecha < RDL7_2026_VIGOR:
        return Tipo(IH_GAS_GENERAL_EUR_GJ, "Ley 38/1992 art. 50, epígrafe 1.10.1")
    m = _ym(fecha)
    ref7 = "RDL 7/2026 art. 38"
    if m in ("2026-03", "2026-04", "2026-05"):
        return Tipo(0.30, ref7)
    if m == "2026-06":
        return _condicional(m, "2026-04", "carburantes", 0.30, IH_GAS_GENERAL_EUR_GJ, ref7 + ".Dos (junio: condición IPC de carburantes de abril)")
    if m == "2026-07":
        return Tipo(0.39, "RDL 18/2026 art. 5")
    if m == "2026-08":
        return _condicional(m, "2026-06", "gas", 0.30, 0.48, "RDL 18/2026 art. 6")
    if m == "2026-09":
        return _condicional_doble("2026-07", "2026-06", "gas", 0.30, 0.39, 0.56, "RDL 18/2026 art. 7")
    if m == "2026-10":
        return Tipo(IH_GAS_GENERAL_EUR_GJ, "RDL 25/2026 art. 13")
    if m == "2026-11":
        return _condicional(m, "2026-09", "gas", 0.30, IH_GAS_GENERAL_EUR_GJ, "RDL 25/2026 art. 14")
    if m == "2026-12":
        return _condicional_doble("2026-10", "2026-09", "gas", 0.30, 0.42, IH_GAS_GENERAL_EUR_GJ, "RDL 25/2026 art. 15")
    return Tipo(None, "sin norma leída", f"no hay tabla de impuestos para {m}: hay que revisar el BOE")


def ih_gas_natural_eur_kwh(fecha: dt.date) -> Tipo:
    t = ih_gas_natural_eur_gj(fecha)
    return Tipo(None if t.valor is None else t.valor * GJ_POR_KWH, t.referencia, t.pendiente)


def ih_glp_eur_t(fecha: dt.date) -> Tipo:
    """Epígrafe 1.8 (GLP para usos distintos del carburante), €/tonelada."""
    if fecha < RDL7_2026_VIGOR:
        return Tipo(IH_GLP_GENERAL_EUR_T, "Ley 38/1992 art. 50, epígrafe 1.8")
    m = _ym(fecha)
    ref7 = "RDL 7/2026 art. 38"
    if m in ("2026-03", "2026-04", "2026-05"):
        return Tipo(0.0, ref7)
    if m == "2026-06":
        return _condicional(m, "2026-04", "carburantes", 0.0, IH_GLP_GENERAL_EUR_T, ref7 + ".Dos (junio: condición IPC de carburantes de abril)")
    if m == "2026-07":
        return Tipo(3.75, "RDL 18/2026 art. 5")
    if m == "2026-08":
        return _condicional(m, "2026-06", "glp", 0.0, 7.5, "RDL 18/2026 art. 6")
    if m == "2026-09":
        return _condicional_doble("2026-07", "2026-06", "glp", 0.0, 3.75, 11.25, "RDL 18/2026 art. 7")
    if m == "2026-10":
        return Tipo(IH_GLP_GENERAL_EUR_T, "RDL 25/2026 art. 13")
    if m == "2026-11":
        return _condicional(m, "2026-09", "glp", 0.0, IH_GLP_GENERAL_EUR_T, "RDL 25/2026 art. 14")
    if m == "2026-12":
        return _condicional_doble("2026-10", "2026-09", "glp", 0.0, 5.25, IH_GLP_GENERAL_EUR_T, "RDL 25/2026 art. 15")
    return Tipo(None, "sin norma leída", f"no hay tabla de impuestos para {m}: hay que revisar el BOE")


# ------------------------------------------------------------------ Precios con impuestos

@dataclass(frozen=True)
class ConImpuestos:
    valor: float | None
    detalle: str          # p. ej. "IEE 0,5 % (RDL 17/2021…) + IVA 5 % (RDL 11/2022…)"
    pendiente: str | None = None


def _pct(x: float) -> str:
    return f"{x * 100:g} %"


def pvpc_con_impuestos(precio_eur_mwh: float, fecha: dt.date, omie_mes_anterior: float | None) -> ConImpuestos:
    t_iee = iee(fecha)
    t_iva = iva_electricidad(fecha, omie_mes_anterior)
    pendientes = [p for p in (t_iee.pendiente, t_iva.pendiente) if p]
    detalle = f"IEE {_pct(t_iee.valor) if t_iee.valor is not None else '?'} con cuota mínima 1 €/MWh ({t_iee.referencia}) + IVA {_pct(t_iva.valor) if t_iva.valor is not None else '?'} ({t_iva.referencia})"
    if pendientes:
        return ConImpuestos(None, detalle, "; ".join(pendientes))
    cuota = max(precio_eur_mwh * t_iee.valor, IEE_CUOTA_MINIMA_EUR_MWH)
    return ConImpuestos((precio_eur_mwh + cuota) * (1 + t_iva.valor), detalle)


def tur_con_impuestos(precio_ckwh_pcs: float, fecha: dt.date) -> ConImpuestos:
    """TUR en c€/kWh (PCS) sin impuestos → c€/kWh (PCS) con hidrocarburos e IVA."""
    t_ih = ih_gas_natural_eur_kwh(fecha)
    t_iva = iva_gas_natural(fecha)
    pendientes = [p for p in (t_ih.pendiente, t_iva.pendiente) if p]
    detalle = f"IH gas natural {t_ih.valor * 100:.4f} c€/kWh ({t_ih.referencia}) + IVA {_pct(t_iva.valor) if t_iva.valor is not None else '?'} ({t_iva.referencia})" if t_ih.valor is not None else f"IH gas natural ? ({t_ih.referencia}) + IVA ? ({t_iva.referencia})"
    if pendientes:
        return ConImpuestos(None, detalle, "; ".join(pendientes))
    return ConImpuestos((precio_ckwh_pcs + t_ih.valor * 100) * (1 + t_iva.valor), detalle)


def butano_bombona_con_impuestos(precio_ckg: float, fecha: dt.date, kg: float = 12.5) -> ConImpuestos:
    """Precio máximo antes de impuestos (c€/kg) → precio de la bombona (€) con hidrocarburos e IVA."""
    t_ih = ih_glp_eur_t(fecha)
    t_iva = iva_butano(fecha)
    pendientes = [p for p in (t_ih.pendiente, t_iva.pendiente) if p]
    detalle = f"IH GLP {t_ih.valor if t_ih.valor is not None else '?'} €/t ({t_ih.referencia}) + IVA {_pct(t_iva.valor) if t_iva.valor is not None else '?'} ({t_iva.referencia})"
    if pendientes:
        return ConImpuestos(None, detalle, "; ".join(pendientes))
    base = precio_ckg / 100 * kg + t_ih.valor / 1000 * kg
    return ConImpuestos(base * (1 + t_iva.valor), detalle)
