"""Línea de órdenes: `python -m precios actualizar [--solo id,id] [--fecha AAAA-MM-DD]`."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys

from .series import actualizar


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="precios")
    sub = p.add_subparsers(dest="orden", required=True)
    a = sub.add_parser("actualizar", help="descarga los datos nuevos y reconstruye series, medias mensuales y metadatos")
    a.add_argument("--solo", help="ids de series separados por comas (p. ej. omie,tur2)")
    a.add_argument("--fecha", help="fecha de referencia (por defecto hoy)")
    a.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    hoy = dt.date.fromisoformat(args.fecha) if args.fecha else None
    solo = set(args.solo.split(",")) if args.solo else None
    estado = actualizar(hoy=hoy, solo=solo)
    for fuente, r in estado["fuentes"].items():
        print(f"{fuente}: {r['estado']}" + (f" — {r['error']}" if r["error"] else ""))
        for id_, s in r["series"].items():
            print(f"   {id_}: último dato {s['ultimo_dato']}, {s['n_datos']} filas" + (" (dato nuevo)" if s["dato_nuevo"] else ""))
    return 0 if all(r["estado"] == "ok" for r in estado["fuentes"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
