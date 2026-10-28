"""Definición de los ocho indicadores del encargo (nueve series: el pellet tiene dos formatos)."""
from __future__ import annotations

from dataclasses import dataclass

from . import conversiones as cv
from .fuentes import avebiom, esios, mibgas, omie, wob


@dataclass(frozen=True)
class Indicador:
    id: str
    numero: int                 # número en el encargo (1–8)
    nombre: str
    nombre_corto: str
    unidad_original: str
    frecuencia: str             # diaria | semanal | trimestral | bimestral | horaria→diaria
    fuente: str
    url_fuente: str
    impuestos_original: str     # «sin impuestos (mayorista)», «con impuestos», «sin impuestos»
    conversion: str             # texto que explica el paso a €/kWh
    nota: str = ""


INDICADORES: dict[str, Indicador] = {
    "omie": Indicador(
        "omie", 1, "Electricidad: precio del mercado diario OMIE, España", "OMIE", "€/MWh",
        "diaria (media aritmética de los periodos horarios o cuarto-horarios del día)",
        omie.FUENTE, omie.URL_FUENTE, "sin impuestos (precio mayorista)",
        "€/MWh ÷ 1.000 = €/kWh",
        "Precio mayorista: no se le aplican impuestos (decisión 1).",
    ),
    "mibgas": Indicador(
        "mibgas", 2, "Gas natural: MIBGAS-ES Index", "MIBGAS", "€/MWh", "diaria (por día de gas)",
        mibgas.FUENTE, mibgas.URL_FUENTE, "sin impuestos (precio mayorista)",
        "€/MWh ÷ 1.000 = €/kWh (el índice se expresa sobre PCS, como todo el mercado gasista)",
        "Precio mayorista: no se le aplican impuestos (decisión 1).",
    ),
    "gasoleo_a": Indicador(
        "gasoleo_a", 3, "Gasóleo de automoción: precio medio en España", "Gasóleo A", "€/l",
        "semanal (precio del lunes)", wob.FUENTE, wob.URL_PAGINA, "con impuestos (y también sin impuestos)",
        f"€/l ÷ {cv.GASOLEO_KWH_L.valor} kWh/l (PCI; decisión 10)",
        "De abril a diciembre de 2022 el Boletín no descuenta la bonificación de 20 c€/l del RDL 6/2022 (decisión 11).",
    ),
    "pvpc": Indicador(
        "pvpc", 4, "Electricidad PVPC: término de energía, tarifa 2.0TD (Península)", "PVPC 2.0TD", "€/MWh",
        "diaria (media aritmética de los valores horarios o cuarto-horarios del día)",
        esios.FUENTE, esios.URL_FUENTE, "sin impuestos",
        "€/MWh ÷ 1.000 = €/kWh; con impuestos: (precio + cuota IEE) × (1 + IVA) vigentes en la fecha",
        "Indicador 1001 de ESIOS. Requiere ESIOS_TOKEN. Existe desde el 01/06/2021 (inicio de la 2.0TD).",
    ),
    "tur2": Indicador(
        "tur2", 5, "Gas natural TUR 2: término variable", "TUR 2", "c€/kWh (PCS)",
        "trimestral (valor vigente desde la fecha de efectos de cada resolución)",
        "BOE, resoluciones de la DGPEM por las que se publica la tarifa de último recurso de gas natural",
        "https://www.boe.es/", "sin impuestos",
        f"c€/kWh (PCS) ÷ 100 ÷ {cv.GAS_NATURAL_PCI_PCS.valor} = €/kWh (PCI); con impuestos: (precio + IH gas) × (1 + IVA) vigentes",
        "Consumo entre 5.000 y 15.000 kWh/año.",
    ),
    "gasoleo_c": Indicador(
        "gasoleo_c", 6, "Gasóleo de calefacción: precio medio en España", "Gasóleo C", "€/l",
        "semanal (precio del lunes)", wob.FUENTE, wob.URL_PAGINA, "con impuestos (y también sin impuestos)",
        f"€/l ÷ {cv.GASOLEO_KWH_L.valor} kWh/l (PCI)",
        "De abril a diciembre de 2022 el Boletín no descuenta la bonificación de 20 c€/l del RDL 6/2022 (decisión 11).",
    ),
    "butano": Indicador(
        "butano", 7, "Butano: bombona regulada de 12,5 kg", "Butano", "c€/kg (antes de impuestos)",
        "bimestral (valor vigente desde el tercer martes de ene/mar/may/jul/sep/nov)",
        "BOE, resoluciones de la DGPEM con los precios máximos de venta, antes de impuestos, de los GLP envasados",
        "https://www.boe.es/", "sin impuestos",
        f"bombona: c€/kg ÷ 100 × 12,5 kg (+ IH GLP, × (1 + IVA)); €/kWh = € ÷ 12,5 kg ÷ {cv.BUTANO_KWH_KG.valor} kWh/kg (PCI)",
        "El BOE solo publica el precio antes de impuestos; el precio de la bombona con impuestos es calculado.",
    ),
    "pellet_saco": Indicador(
        "pellet_saco", 8, "Pellet: precio medio en España del saco de 15 kg", "Pellet saco 15 kg", "€/saco",
        "trimestral (medias anuales antes de 4T2024)", avebiom.FUENTE, avebiom.URL_PAGINA,
        "con impuestos (IVA incluido según AVEBIOM)",
        f"€/saco ÷ 15 kg ÷ {cv.PELLET_KWH_KG.valor} kWh/kg (PCI; decisión 9). Se guarda también el c€/kWh de AVEBIOM (4,76 kWh/kg).",
        "Trimestral solo desde 4T2024 (PDF disponibles); 2020–2024: medias anuales publicadas por AVEBIOM (decisión 6).",
    ),
    "pellet_granel": Indicador(
        "pellet_granel", 8, "Pellet: precio medio en España a granel en volquete", "Pellet granel", "€/t",
        "trimestral (medias anuales antes de 4T2024)", avebiom.FUENTE, avebiom.URL_PAGINA,
        "con impuestos (IVA y transporte incluidos según AVEBIOM)",
        f"€/t ÷ 1.000 ÷ {cv.PELLET_KWH_KG.valor} kWh/kg (PCI; decisión 9). Se guarda también el c€/kWh de AVEBIOM.",
        "Trimestral solo desde 4T2024 (PDF disponibles); 2020–2024: medias anuales publicadas por AVEBIOM (decisión 6).",
    ),
}

ORDEN = ["omie", "mibgas", "gasoleo_a", "pvpc", "tur2", "gasoleo_c", "butano", "pellet_saco", "pellet_granel"]
