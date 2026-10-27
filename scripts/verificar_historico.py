"""Comprueba que la actualización conserva el histórico: ninguna serie pierde filas ni retrocede su primer
dato respecto a la versión confirmada en git (HEAD). Se ejecuta en el workflow antes de hacer commit.

    python scripts/verificar_historico.py          # código de salida 1 si algo se ha perdido
"""
from __future__ import annotations

import csv
import io
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_SERIES = RAIZ / "datos" / "series"


def _filas(texto: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(texto)))


def main() -> int:
    salida = subprocess.run(["git", "ls-tree", "--name-only", "HEAD", "datos/series/"], cwd=RAIZ, capture_output=True, text=True)
    en_git = [l.strip() for l in salida.stdout.splitlines() if l.strip().endswith(".csv")]
    problemas = []
    for ruta in en_git:
        antes = _filas(subprocess.run(["git", "show", f"HEAD:{ruta}"], cwd=RAIZ, capture_output=True, text=True).stdout)
        actual_ruta = RAIZ / ruta
        if not actual_ruta.exists():
            problemas.append(f"{ruta}: ha desaparecido")
            continue
        ahora = _filas(actual_ruta.read_text(encoding="utf-8"))
        if len(ahora) < len(antes):
            problemas.append(f"{ruta}: {len(antes)} filas antes, {len(ahora)} ahora")
        if antes and ahora and min(f["fecha"] for f in ahora) > min(f["fecha"] for f in antes):
            problemas.append(f"{ruta}: el primer dato pasa de {min(f['fecha'] for f in antes)} a {min(f['fecha'] for f in ahora)}")
        claves_antes = {(f["fecha"], f["periodo"]) for f in antes}
        claves_ahora = {(f["fecha"], f["periodo"]) for f in ahora}
        perdidas = claves_antes - claves_ahora
        if perdidas:
            problemas.append(f"{ruta}: {len(perdidas)} filas desaparecidas, p. ej. {sorted(perdidas)[:3]}")
        print(f"{ruta}: {len(antes)} → {len(ahora)} filas")
    if problemas:
        print("\nEL HISTÓRICO SE HA REDUCIDO; no se publica:")
        for p in problemas:
            print(" -", p)
        return 1
    print("\nHistórico conservado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
