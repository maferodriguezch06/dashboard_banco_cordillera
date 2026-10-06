"""Formatos numéricos en convención colombiana (punto de miles, coma decimal)."""
from __future__ import annotations

import math


def _es(x: str) -> str:
    return x.replace(",", "_").replace(".", ",").replace("_", ".")


def num(v: float, dec: int = 0) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "Sin dato"
    return _es(f"{v:,.{dec}f}")


def pct(v: float, dec: int = 1) -> str:
    return "Sin dato" if v is None or math.isnan(v) else f"{num(v, dec)} %"


def pp(v: float, dec: int = 1) -> str:
    if v is None or math.isnan(v):
        return ""
    signo = "+" if v > 0 else ""
    return f"{signo}{num(v, dec)} pp"


def cop(v: float) -> str:
    if v is None or math.isnan(v):
        return "Sin dato"
    a = abs(v)
    if a >= 1e12:
        return f"${num(v / 1e12, 2)} billones"
    if a >= 1e9:
        return f"${num(v / 1e9, 1)} mil M"
    if a >= 1e6:
        return f"${num(v / 1e6, 1)} M"
    return f"${num(v, 0)}"
