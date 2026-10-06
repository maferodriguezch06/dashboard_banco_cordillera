"""Definición única de KPI y agregaciones. Toda cifra del tablero sale de aquí."""
from __future__ import annotations

import numpy as np
import pandas as pd


def cartera(df: pd.DataFrame) -> pd.DataFrame:
    """Solo productos de crédito (excluye cuenta de ahorros)."""
    return df[df["es_credito"]]


def _div(a: float, b: float) -> float:
    return float(a) / float(b) if b else np.nan


# --- KPI de riesgo -----------------------------------------------------------
def icv_saldo(df: pd.DataFrame) -> float:
    """Índice de cartera vencida: saldo con más de 30 días de mora / saldo total de crédito (%)."""
    c = cartera(df)
    return 100 * _div(c["saldo_vencido_30"].sum(), c["saldo_o_monto_cop"].sum())


def icv_conteo(df: pd.DataFrame) -> float:
    """% de obligaciones de crédito con más de 30 días de mora."""
    c = cartera(df)
    return 100 * _div(c["vencida_30"].sum(), len(c))


def severa_saldo(df: pd.DataFrame) -> float:
    c = cartera(df)
    return 100 * _div(c["saldo_severo_60"].sum(), c["saldo_o_monto_cop"].sum())


def saldo_vencido(df: pd.DataFrame) -> float:
    return float(cartera(df)["saldo_vencido_30"].sum())


def saldo_cartera(df: pd.DataFrame) -> float:
    return float(cartera(df)["saldo_o_monto_cop"].sum())


def score_promedio(df: pd.DataFrame) -> float:
    return float(cartera(df)["score_riesgo"].mean())


def pct_score_bajo(df: pd.DataFrame, umbral: int = 600) -> float:
    c = cartera(df)
    return 100 * _div((c["score_riesgo"] < umbral).sum(), len(c))


# --- KPI de experiencia ------------------------------------------------------
def nps(df: pd.DataFrame) -> float:
    """NPS = % promotores (9-10) - % detractores (0-6), solo sobre quienes respondieron."""
    r = df[df["nps_respondio"]]
    if r.empty:
        return np.nan
    return 100 * ((r["nps_0a10"] >= 9).mean() - (r["nps_0a10"] <= 6).mean())


def reclamos_por_100(df: pd.DataFrame) -> float:
    return 100 * _div(df["reclamos_90d"].sum(), len(df))


def tx_digitales(df: pd.DataFrame) -> float:
    return float(df["transacciones_digitales_30d"].mean())


# --- Agregaciones ------------------------------------------------------------
def resumen_por(df: pd.DataFrame, dims: list[str] | str) -> pd.DataFrame:
    """Tabla de indicadores por una o varias dimensiones."""
    dims = [dims] if isinstance(dims, str) else dims
    base = df.assign(
        saldo_credito=np.where(df["es_credito"], df["saldo_o_monto_cop"], 0),
        venc_cred=np.where(df["es_credito"], df["saldo_vencido_30"], 0),
        sev_cred=np.where(df["es_credito"], df["saldo_severo_60"], 0),
        n_cred=df["es_credito"].astype(int),
        n_venc=(df["es_credito"] & df["vencida_30"]).astype(int),
        score_cred=np.where(df["es_credito"], df["score_riesgo"], np.nan),
        tasa_cred=np.where(df["es_credito"], df["tasa_efectiva_anual_pct"], np.nan),
        prom=(df["categoria_nps"] == "Promotor").astype(int),
        det=(df["categoria_nps"] == "Detractor").astype(int),
        resp=df["nps_respondio"].astype(int),
    )
    g = base.groupby(dims, observed=True).agg(
        registros=("id_registro", "size"),
        obligaciones_credito=("n_cred", "sum"),
        saldo_credito=("saldo_credito", "sum"),
        saldo_vencido_30=("venc_cred", "sum"),
        saldo_severo_60=("sev_cred", "sum"),
        vencidas_30=("n_venc", "sum"),
        score_promedio=("score_cred", "mean"),
        tasa_promedio=("tasa_cred", "mean"),
        promotores=("prom", "sum"),
        detractores=("det", "sum"),
        respuestas=("resp", "sum"),
        tx_digitales=("transacciones_digitales_30d", "mean"),
        reclamos=("reclamos_90d", "sum"),
    ).reset_index()
    g["icv_saldo"] = 100 * g["saldo_vencido_30"] / g["saldo_credito"].replace(0, np.nan)
    g["icv_conteo"] = 100 * g["vencidas_30"] / g["obligaciones_credito"].replace(0, np.nan)
    g["severa_saldo"] = 100 * g["saldo_severo_60"] / g["saldo_credito"].replace(0, np.nan)
    g["nps"] = 100 * (g["promotores"] - g["detractores"]) / g["respuestas"].replace(0, np.nan)
    g["reclamos_100"] = 100 * g["reclamos"] / g["registros"]
    total_venc = g["saldo_vencido_30"].sum()
    g["participacion_vencido"] = 100 * g["saldo_vencido_30"] / total_venc if total_venc else np.nan
    return g


def variacion_trimestral(df: pd.DataFrame, funcion) -> tuple[float, float, str]:
    """Valor del último trimestre del filtro, cambio vs. el anterior y etiqueta.

    Solo usa trimestres completos (3 meses con datos) para no comparar un trimestre parcial.
    """
    meses = df.groupby("trimestre")["periodo"].nunique()
    completos = meses[meses == 3].index.sort_values()
    if len(completos) < 2:
        return funcion(df), np.nan, ""
    ult, ant = completos[-1], completos[-2]
    v1 = funcion(df[df["trimestre"] == ult])
    v0 = funcion(df[df["trimestre"] == ant])
    return v1, v1 - v0, f"{ult} vs. {ant}"
