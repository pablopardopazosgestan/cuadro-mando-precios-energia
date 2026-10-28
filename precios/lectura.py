"""Lectura para dirección: qué significa cada indicador y cómo repercute en el coste de producción y en el precio del
pellet. Dos partes, separadas a propósito:

- `SIGNIFICADO`: texto fijo por indicador, redactado el 28/10/2026 a petición de Pablo (decisión en `docs/DECISIONES.md`).
  Es una explicación cualitativa y general, no un dato: se revisa a mano si cambia el negocio.
- Frases calculadas (`frase_dinamica`, `competitividad`): se construyen solo con las cifras del panel (precio actual,
  variaciones, medias mensuales). La «prima» de una alternativa es (precio alternativa ÷ precio pellet − 1), en %,
  ambos en €/kWh con impuestos: dato derivado, marcado como calculado. Nada se estima: si falta un precio, no hay frase.

El impacto en euros por tonelada de pellet depende de la estructura de consumos de cada planta (kWh eléctricos y litros
de gasóleo por tonelada) y no se incluye: el proyecto solo usa datos públicos.
"""
from __future__ import annotations

# Alternativas al pellet en calefacción, en el orden en que se presentan
ALTERNATIVAS = ["gasoleo_c", "butano", "tur2", "pvpc"]

SIGNIFICADO: dict[str, str] = {
    "omie": "Precio mayorista de la electricidad (mercado diario). Es la referencia de los contratos indexados y del PVPC. "
            "La electricidad es el principal consumo energético de la fábrica de pellet (astillado, molienda, prensado y, en "
            "parte, secado): una variación sostenida del OMIE se traslada al coste eléctrico por tonelada en los suministros "
            "indexados y, en la renovación, a los de precio fijo.",
    "mibgas": "Precio mayorista del gas natural. Marca el coste del gas industrial y del TUR, compite con el pellet en calefacción "
              "e industria y en algunas plantas es el combustible de secado. Un gas caro favorece la demanda de pellet; un gas "
              "barato la frena y presiona el precio de venta.",
    "gasoleo_a": "Precio del gasóleo de automoción con impuestos. Es el combustible del transporte: recogida de serrín y astilla y "
                 "reparto del pellet. Repercute en el coste logístico por tonelada y, por tanto, en el precio del granel puesto en destino.",
    "pvpc": "Precio regulado de la electricidad doméstica (término de energía) con impuestos. Es la referencia del coste de la "
            "calefacción eléctrica (radiadores, acumuladores, bomba de calor), que compite con el pellet en el hogar.",
    "tur2": "Gas natural regulado doméstico con impuestos; se revisa cada trimestre. Competidor directo del pellet en calefacción "
            "donde hay red de gas: cuanto mayor sea su precio frente al pellet, mayor el incentivo a instalar o mantener biomasa.",
    "gasoleo_c": "Gasóleo de calefacción con impuestos. Principal competidor del pellet en viviendas sin red de gas y el que más "
                 "condiciona la decisión de cambiar de caldera; su ventaja o desventaja frente al pellet es el argumento comercial clave.",
    "butano": "Bombona regulada de 12,5 kg con impuestos; se revisa cada dos meses según el petróleo y el tipo de cambio. "
              "Competidor del pellet en hogares pequeños y segundas residencias.",
    "pellet_saco": "Precio medio al consumidor del saco de 15 kg (IVA incluido) según AVEBIOM. Es la referencia de mercado con la que "
                   "comparar el precio propio en el canal minorista; su evolución refleja oferta, materia prima y demanda estacional.",
    "pellet_granel": "Precio medio al consumidor del granel en volquete (IVA y transporte incluidos) según AVEBIOM. Referencia para "
                     "calderas domésticas grandes, comunidades e industria; más sensible al coste logístico que el saco.",
}


def _f(x):
    return None if x is None else float(x)


def precio_hace_un_anyo(r: dict) -> float | None:
    """Precio en €/kWh de hace un año, deducido del actual y de la variación interanual (dato derivado)."""
    p, v = _f(r.get("precio_eur_kwh")), _f(r.get("variacion_interanual_pct"))
    if p is None or v is None or v <= -100:
        return None
    return p / (1 + v / 100)


def prima(alternativa: dict, pellet: dict) -> tuple[float | None, float | None]:
    """(prima actual, prima hace un año) en %: cuánto más (o menos) cuesta el kWh de la alternativa que el del pellet."""
    pa, pp = _f(alternativa.get("precio_eur_kwh")), _f(pellet.get("precio_eur_kwh"))
    actual = None if pa is None or not pp else (pa / pp - 1) * 100
    pa1, pp1 = precio_hace_un_anyo(alternativa), precio_hace_un_anyo(pellet)
    hace_un_anyo = None if pa1 is None or not pp1 else (pa1 / pp1 - 1) * 100
    return actual, hace_un_anyo


def competitividad(resumen: dict[str, dict], pellet_id: str = "pellet_saco") -> list[dict]:
    """Prima de cada alternativa frente al pellet, hoy y hace un año. Solo con precios disponibles."""
    out = []
    pellet = resumen.get(pellet_id, {})
    for id_ in ALTERNATIVAS:
        r = resumen.get(id_)
        if not r:
            continue
        hoy, antes = prima(r, pellet)
        if hoy is None:
            continue
        out.append({"id": id_, "nombre": r["nombre_corto"], "prima_pct": hoy, "prima_hace_un_anyo_pct": antes})
    return out


def _pct(x: float | None, dec: int = 0) -> str:
    if x is None:
        return "n. d."
    s = f"{x:+.{dec}f}".replace(".", ",")
    return s.replace("-", "−") + " %"


def _signo(v: float | None, umbral: float = 1.0) -> str:
    if v is None:
        return "sin dato"
    if v > umbral:
        return "sube"
    if v < -umbral:
        return "baja"
    return "se mantiene"


def frase_dinamica(id_: str, resumen: dict[str, dict]) -> str:
    """Frase con cifras del panel para la lectura de dirección. Vacía si falta el precio."""
    r = resumen.get(id_)
    if not r or r.get("precio_eur_kwh") is None:
        return "Sin precio disponible en la fecha de referencia: no se puede valorar."
    sem, inter = _f(r.get("variacion_semanal_pct")), _f(r.get("variacion_interanual_pct"))
    base = f"Esta semana {_signo(sem)} ({_pct(sem, 1)}); frente a hace un año, {_signo(inter)} ({_pct(inter, 1)})."
    if id_ in ALTERNATIVAS:
        hoy, antes = prima(r, resumen.get("pellet_saco", {}))
        if hoy is not None:
            mas = "más" if hoy >= 0 else "menos"
            frase = f" Su kWh cuesta hoy un {abs(hoy):.0f} % {mas} que el del pellet en saco"
            if antes is not None:
                tendencia = "amplía" if abs(hoy) > abs(antes) + 1 and hoy >= 0 else "reduce" if hoy >= 0 and abs(hoy) < abs(antes) - 1 else "mantiene"
                frase += f" (hace un año, {abs(antes):.0f} % {'más' if antes >= 0 else 'menos'}): la ventaja del pellet se {tendencia}."
            else:
                frase += "."
            base += frase.replace(",", ",")
        return base
    if id_ == "omie":
        return base + (" Un OMIE más alto que hace un año encarece el coste eléctrico de fabricación en los suministros indexados." if inter and inter > 5
                       else " Un OMIE más bajo que hace un año abarata el coste eléctrico de fabricación en los suministros indexados." if inter and inter < -5
                       else " Coste eléctrico de fabricación estable respecto al año pasado.")
    if id_ == "mibgas":
        return base + (" Gas más caro que hace un año: favorece la competitividad del pellet frente al gas." if inter and inter > 5
                       else " Gas más barato que hace un año: presión sobre la competitividad del pellet frente al gas." if inter and inter < -5
                       else " Sin cambio relevante en la posición del pellet frente al gas.")
    if id_ == "gasoleo_a":
        return base + (" Encarece el transporte de materia prima y el reparto." if inter and inter > 5
                       else " Abarata el transporte de materia prima y el reparto." if inter and inter < -5
                       else " Coste de transporte estable respecto al año pasado.")
    if id_.startswith("pellet"):
        comp = competitividad(resumen, id_)
        if comp:
            mas_barato = [c for c in comp if c["prima_pct"] > 0]
            if len(mas_barato) == len(comp):
                return base + f" El pellet es hoy la opción más barata frente a {', '.join(c['nombre'] for c in comp)}."
            caras = ", ".join(c["nombre"] for c in comp if c["prima_pct"] <= 0)
            return base + f" Es más barato que {', '.join(c['nombre'] for c in mas_barato) or 'ninguna alternativa'}; {caras} resulta más barato que el pellet."
        return base
    return base
