"""Rutas y constantes compartidas."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ / "datos"
DIR_SERIES = DIR_DATOS / "series"
DIR_MENSUAL = DIR_DATOS / "mensual"
DIR_ORIGINALES = DIR_DATOS / "fuentes_originales"
DIR_CACHE = Path(os.environ.get("PRECIOS_CACHE", RAIZ / ".cache"))

# Inicio del histórico obligatorio y del histórico ampliado (decisión 4 del 25/10/2026).
INICIO_HISTORICO = dt.date(2022, 1, 1)
INICIO_AMPLIADO = dt.date(2020, 1, 1)

USER_AGENT = (
    "cuadro-mando-precios-energia/0.2 (descarga automatizada de datos publicos; "
    "https://github.com/pablopardopazosgestan/cuadro-mando-precios-energia)"
)
