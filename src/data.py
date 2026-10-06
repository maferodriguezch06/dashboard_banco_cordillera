"""Carga del modelo estrella y aplicación de filtros."""
from __future__ import annotations

import pandas as pd

from src.config import ruta
from src.pipeline import ORDEN_ESTADO, ORDEN_INGRESO, ORDEN_SEGMENTO, PRODUCTOS, CANALES, ejecutar

TABLAS = ["fact_obligacion", "dim_fecha", "dim_geografia", "dim_producto",
          "dim_segmento", "dim_canal", "dim_ingreso"]


def _leer(nombre: str) -> pd.DataFrame:
    return pd.read_csv(ruta("modelo") / f"{nombre}.csv")


def cargar_modelo() -> dict[str, pd.DataFrame]:
    """Lee las tablas del modelo; si no existen ejecuta el pipeline."""
    if not all((ruta("modelo") / f"{t}.csv").exists() for t in TABLAS):
        ejecutar()
    return {t: _leer(t) for t in TABLAS}


def tabla_analitica(modelo: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Une hechos con dimensiones (relaciones 1:N por llave subrogada)."""
    f = modelo["fact_obligacion"]
    df = (f.merge(modelo["dim_fecha"][["fecha_key", "fecha", "anio", "trimestre", "periodo", "etiqueta_mes"]],
                  on="fecha_key", how="left")
           .merge(modelo["dim_geografia"], on="geo_key", how="left")
           .merge(modelo["dim_producto"].drop(columns="orden"), on="producto_key", how="left")
           .merge(modelo["dim_segmento"].drop(columns="orden"), on="segmento_key", how="left")
           .merge(modelo["dim_canal"].drop(columns="orden"), on="canal_key", how="left")
           .merge(modelo["dim_ingreso"].drop(columns="orden"), on="ingreso_key", how="left"))

    df["fecha"] = pd.to_datetime(df["fecha"])
    ordenes = {
        "estado_obligacion": ORDEN_ESTADO,
        "ingreso_mensual_rango": ORDEN_INGRESO,
        "segmento": ORDEN_SEGMENTO,
        "producto": list(PRODUCTOS),
        "canal_origen": list(CANALES),
    }
    for c, orden in ordenes.items():
        df[c] = pd.Categorical(df[c], categories=orden, ordered=True)
    for c in ["banda_score", "banda_digital"]:
        cats = list(dict.fromkeys(df.sort_values(
            "score_riesgo" if c == "banda_score" else "transacciones_digitales_30d")[c].dropna()))
        df[c] = pd.Categorical(df[c], categories=cats, ordered=True)
    return df


def filtrar(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    m = (df["periodo"] >= filtros["desde"]) & (df["periodo"] <= filtros["hasta"])
    for col in ["region", "producto", "segmento", "canal_origen"]:
        valores = filtros.get(col)
        if valores:
            m &= df[col].isin(valores)
    return df[m]
