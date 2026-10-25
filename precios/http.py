"""Cliente HTTP con reintentos y caché en disco.

Todas las descargas pasan por aquí para que el comportamiento (User-Agent del proyecto,
reintentos, caché) sea el mismo en todas las fuentes.
"""
from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import requests

from .config import DIR_CACHE, USER_AGENT

log = logging.getLogger(__name__)

_sesion: requests.Session | None = None


class ErrorDescarga(RuntimeError):
    """La fuente no ha respondido o ha respondido con error."""


def sesion() -> requests.Session:
    global _sesion
    if _sesion is None:
        _sesion = requests.Session()
        _sesion.headers["User-Agent"] = USER_AGENT
    return _sesion


def descargar(url: str, *, params: dict | None = None, headers: dict | None = None,
              cache: str | None = None, reintentos: int = 5, timeout: int = 120,
              aceptar_404: bool = False) -> bytes:
    """Descarga `url` y devuelve el cuerpo. Si `cache` es una clave, guarda/lee de disco.

    Lanza ErrorDescarga tras agotar los reintentos. Con `aceptar_404`, un 404 devuelve b""
    (y también se cachea), útil para días sin BOE o ficheros aún no publicados.
    """
    ruta = None
    if cache:
        ruta = DIR_CACHE / cache
        if ruta.exists():
            return ruta.read_bytes()
    ultimo = None
    for intento in range(reintentos):
        try:
            r = sesion().get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 404 and aceptar_404:
                cuerpo = b""
            elif r.status_code >= 400:
                raise ErrorDescarga(f"HTTP {r.status_code} en {r.url}")
            else:
                cuerpo = r.content
            if ruta is not None:
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_bytes(cuerpo)
            return cuerpo
        except (requests.RequestException, ErrorDescarga) as e:
            ultimo = e
            if isinstance(e, ErrorDescarga) and "HTTP 4" in str(e) and "HTTP 429" not in str(e):
                break  # un 4xx distinto de 429 no se arregla reintentando
            espera = 2 ** intento
            log.warning("fallo descargando %s (%s); reintento en %ss", url, e, espera)
            time.sleep(espera)
    raise ErrorDescarga(f"no se pudo descargar {url}: {ultimo}")


def clave_cache(*partes: str) -> str:
    """Clave de caché legible (sin caracteres raros) a partir de partes de texto."""
    texto = "/".join(partes)
    seguro = "".join(c if c.isalnum() or c in "._-/" else "_" for c in texto)
    if len(seguro) > 180:
        seguro = seguro[:150] + "_" + hashlib.sha1(texto.encode()).hexdigest()[:12]
    return seguro
