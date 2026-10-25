"""Factores de conversión a €/kWh (sobre poder calorífico inferior, PCI) y su procedencia.

Los cuatro factores son los del boletín de referencia (que cita al IDAE). Decisión 9 y 10 del
25/10/2026: pellet a 4,8 kWh/kg (AVEBIOM usa 4,76 kWh/kg; se guarda también su c€/kWh), y el
gasóleo de automoción se convierte con el mismo factor que el de calefacción.
La verificación directa en las publicaciones del IDAE queda pendiente (idae.es no es accesible
desde el entorno de trabajo); así consta en docs/METODOLOGIA.md.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Factor:
    nombre: str
    valor: float
    unidad: str          # p. ej. "kWh/kg"
    procedencia: str


PELLET_KWH_KG = Factor("Pellet de madera, PCI", 4.8, "kWh/kg",
                       "Boletín de referencia (fuente citada: IDAE). AVEBIOM usa 4.100 kcal/kg = 4,76 kWh/kg en su índice.")
PELLET_AVEBIOM_KWH_KG = Factor("Pellet de madera, PCI usado por AVEBIOM", 4.76, "kWh/kg",
                               "Índice de precios AVEBIOM: «poder calorífico del pellet de 4100 kcal/kg (4,76 kWh/kg)».")
GASOLEO_KWH_L = Factor("Gasóleo (automoción y calefacción), PCI", 10.28, "kWh/l",
                       "Boletín de referencia (fuente citada: IDAE). Decisión 10: mismo factor para gasóleo A y C.")
BUTANO_KWH_KG = Factor("Butano, PCI", 12.73, "kWh/kg",
                       "Boletín de referencia (fuente citada: IDAE).")
GAS_NATURAL_PCI_PCS = Factor("Gas natural, relación PCI/PCS", 0.904, "adimensional",
                             "Boletín de referencia (fuente citada: IDAE). La TUR se factura en kWh sobre PCS.")

MASA_BOMBONA_KG = 12.5
KG_POR_SACO_PELLET = 15.0


def eur_mwh_a_eur_kwh(precio: float) -> float:
    return precio / 1000.0


def eur_1000l_a_eur_kwh(precio: float, factor: Factor = GASOLEO_KWH_L) -> float:
    """€/1.000 l → €/kWh (PCI)."""
    return precio / 1000.0 / factor.valor


def eur_litro_a_eur_kwh(precio: float, factor: Factor = GASOLEO_KWH_L) -> float:
    return precio / factor.valor


def ckwh_pcs_a_eur_kwh_pci(precio_ckwh_pcs: float) -> float:
    """c€/kWh (PCS, como factura la TUR) → €/kWh sobre PCI."""
    return precio_ckwh_pcs / 100.0 / GAS_NATURAL_PCI_PCS.valor


def eur_kg_a_eur_kwh(precio_eur_kg: float, factor: Factor) -> float:
    return precio_eur_kg / factor.valor


def eur_bombona_a_eur_kwh(precio_bombona: float) -> float:
    return precio_bombona / MASA_BOMBONA_KG / BUTANO_KWH_KG.valor


def eur_saco_a_eur_kwh(precio_saco: float, factor: Factor = PELLET_KWH_KG) -> float:
    return precio_saco / KG_POR_SACO_PELLET / factor.valor


def eur_tonelada_a_eur_kwh(precio_t: float, factor: Factor = PELLET_KWH_KG) -> float:
    return precio_t / 1000.0 / factor.valor
