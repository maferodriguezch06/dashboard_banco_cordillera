"""Carga de configuración y rutas del proyecto."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_CONFIG = RAIZ / "config" / "settings.yaml"


@lru_cache(maxsize=1)
def cargar_config() -> dict:
    with open(ARCHIVO_CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ruta(clave: str) -> Path:
    """Devuelve una ruta absoluta definida en settings.yaml > rutas."""
    return RAIZ / cargar_config()["rutas"][clave]


def paleta() -> dict:
    return cargar_config()["paleta"]
