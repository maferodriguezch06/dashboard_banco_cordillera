"""Pestaña 3: vista inicial con KPI, evolución temporal y composición de la cartera."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src import metrics as m
from src.charts import COLOR_ESTADO, P, linea_referencia, titular
from src.config import cargar_config
from src.formato import cop, num, pct, pp

METAS = cargar_config()["metas"]

METRICAS_TIEMPO = {
    "ICV 30+ por saldo": ("icv_saldo", "%", METAS["icv_alerta_pct"], "Referencia interna 10 %",
                          "La mora oscila alrededor de la referencia: es un problema estructural, no estacional."),
    "ICV 30+ por número": ("icv_conteo", "%", METAS["icv_alerta_pct"], "Referencia interna 10 %",
                           "Por número de obligaciones el patrón es el mismo que por saldo."),
    "Score promedio": ("score_promedio", "pts", None, "",
                       "La calidad crediticia de entrada no cambia en el periodo."),
    "NPS": ("nps", "pts", METAS["nps_objetivo"], "Neutralidad (NPS = 0)",
            "Por debajo de cero, hay más detractores que promotores en casi todo el periodo."),
}


def _tarjetas(df):
    v_icv, d_icv, et = m.variacion_trimestral(df, m.icv_saldo)
    v_sv, d_sv, _ = m.variacion_trimestral(df, m.saldo_vencido)
    v_sc, d_sc, _ = m.variacion_trimestral(df, m.score_promedio)
    v_np, d_np, _ = m.variacion_trimestral(df, m.nps)
    etq = f"último trimestre ({et})" if et else "sin trimestre previo completo"
    icv_total = m.icv_saldo(df)

    c = st.columns(4, gap="small")
    with c[0]:
        ui.kpi("ICV 30+ por saldo", pct(icv_total), "riesgo", P["ciruela"],
               delta=pp(d_icv) if et else "", delta_favorable=None if not et else d_icv <= 0,
               nota=etq, alerta=icv_total > METAS["icv_alerta_pct"])
    with c[1]:
        delta = (pct(100 * d_sv / (v_sv - d_sv)) if et and v_sv - d_sv else "")
        ui.kpi("Saldo vencido 30+", cop(m.saldo_vencido(df)), "dinero", P["tinta"],
               delta=("+" if et and d_sv > 0 else "") + delta, delta_favorable=None if not et else d_sv <= 0,
               nota=etq)
    with c[2]:
        ui.kpi("Score promedio", num(m.score_promedio(df)), "score", P["acero"],
               delta=(("+" if d_sc > 0 else "") + num(d_sc, 1) + " pts") if et else "",
               delta_favorable=None if not et else d_sc >= 0, nota=etq)
    with c[3]:
        v = m.nps(df)
        ui.kpi("NPS", num(v, 1), "cliente", P["oro"],
               delta=(("+" if d_np > 0 else "") + num(d_np, 1) + " pts") if et else "",
               delta_favorable=None if not et else d_np >= 0, nota=etq, alerta=v < METAS["nps_objetivo"])

    st.write("")
    s = st.columns(6, gap="small")
    datos = [
        ("Saldo de crédito observado", cop(m.saldo_cartera(df))),
        ("Obligaciones de crédito", num(int(df["es_credito"].sum()))),
        ("Mora severa > 60 (saldo)", pct(m.severa_saldo(df))),
        ("Obligaciones con score < 600", pct(m.pct_score_bajo(df, METAS["score_bajo"]))),
        ("Transacciones digitales / mes", num(m.tx_digitales(df), 1)),
        ("Reclamos por cada 100", num(m.reclamos_por_100(df), 1)),
    ]
    for col, (e, v) in zip(s, datos):
        with col:
            ui.mini(e, v)


def _serie_tiempo(df, metrica, grano):
    col_t = "periodo" if grano == "Mensual" else "trimestre"
    r = m.resumen_por(df, col_t).sort_values(col_t)
    campo, unidad, ref, ref_txt, sub = METRICAS_TIEMPO[metrica]
    y = r[campo]
    if grano == "Mensual":
        etiquetas = dict(zip(df["periodo"], df["etiqueta_mes"]))
        x = r[col_t].map(etiquetas)
    else:
        x = r[col_t]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers", name=metrica,
        line=dict(color=P["acero"], width=2.4), marker=dict(size=6, color=P["acero"]),
        customdata=np.stack([r["obligaciones_credito"], r["saldo_vencido_30"] / 1e9], axis=-1),
        hovertemplate="<b>%{x}</b><br>" + metrica + ": %{y:,.1f}<br>Obligaciones de crédito: %{customdata[0]:,.0f}"
                      "<br>Saldo vencido: $%{customdata[1]:,.1f} mil M<extra></extra>",
    ))
    if grano == "Mensual" and len(r) >= 3:
        fig.add_trace(go.Scatter(x=x, y=y.rolling(3).mean(), mode="lines", name="Promedio móvil 3 meses",
                                 line=dict(color=P["tinta"], width=2, dash="dash"),
                                 hovertemplate="Promedio móvil: %{y:,.1f}<extra></extra>"))
    if ref is not None:
        linea_referencia(fig, ref, ref_txt)
    var = y.max() - y.min()
    titulo = (f"{metrica}: se mueve en una franja de {num(var, 1)} {'pp' if unidad == '%' else 'pts'}"
              if len(r) > 1 else metrica)
    titular(fig, titulo, sub, 400)
    fig.update_yaxes(title_text=unidad)
    fig.update_xaxes(type="category", tickangle=-45 if grano == "Mensual" else 0, nticks=17)
    fig.update_layout(legend=dict(y=-0.24 if grano == "Mensual" else -0.12), margin=dict(b=70))
    return fig


def _composicion(df):
    c = m.cartera(df)
    r = c.groupby("estado_obligacion", observed=True)["saldo_o_monto_cop"].sum()
    fig = go.Figure(go.Pie(
        labels=r.index.astype(str), values=r.values, hole=0.62, sort=False, direction="clockwise",
        marker=dict(colors=[COLOR_ESTADO[e] for e in r.index.astype(str)], line=dict(color="#FFFFFF", width=2)),
        text=[f"{num(100 * v / r.sum(), 1)} %" if v / r.sum() > 0.05 else "" for v in r.values],
        textinfo="text", textfont=dict(size=11, color="#FFFFFF"),
        hovertemplate="<b>%{label}</b><br>Saldo: $%{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    al_dia = 100 * r.get("Al día", 0) / r.sum()
    fig.add_annotation(text=f"<b>{num(al_dia, 1)} %</b><br><span style='font-size:11px'>al día</span>",
                       showarrow=False, font=dict(size=20, color=P["tinta"]))
    titular(fig, "Composición del saldo por estado", "Ciruela marca el deterioro severo", 400)
    fig.update_layout(legend=dict(orientation="h", y=-0.04, x=0.5, xanchor="center", yanchor="top"),
                      margin=dict(l=12, r=12, t=70, b=40))
    return fig


def _por_producto(df):
    r = m.resumen_por(m.cartera(df), "producto").sort_values("saldo_credito")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=r["producto"].astype(str), x=r["saldo_credito"] / 1e9, orientation="h",
                         name="Saldo de crédito", marker_color=P["bruma"],
                         hovertemplate="<b>%{y}</b><br>Saldo: $%{x:,.1f} mil M<extra></extra>"))
    fig.add_trace(go.Bar(y=r["producto"].astype(str), x=r["saldo_vencido_30"] / 1e9, orientation="h",
                         name="Saldo vencido 30+", marker_color=P["ciruela"],
                         customdata=r["icv_saldo"],
                         hovertemplate="<b>%{y}</b><br>Vencido: $%{x:,.1f} mil M<br>ICV: %{customdata:,.1f} %"
                                       "<extra></extra>"))
    lider = r.iloc[-1]
    titular(fig, f"{lider['producto']} concentra {num(lider['participacion_vencido'], 0)} % del saldo vencido",
            "Miles de millones de COP. Barras superpuestas: total frente a vencido.", 340)
    fig.update_layout(barmode="overlay", bargap=0.35)
    fig.update_xaxes(title_text="Miles de millones de COP", showgrid=True, gridcolor="#E9EEF3")
    return fig


def render(df, df_total):
    ui.seccion("Panorama de la cartera", "Vista inicial: los cuatro KPI responden a todos los filtros de la barra "
               "lateral. La variación compara el último trimestre completo con el anterior.")
    _tarjetas(df)

    ui.seccion("Evolución en el tiempo")
    k1, k2 = st.columns([2, 1])
    with k1:
        metrica = st.segmented_control("Indicador", list(METRICAS_TIEMPO), default="ICV 30+ por saldo",
                                       key="pan_metrica") or "ICV 30+ por saldo"
    with k2:
        grano = st.segmented_control("Granularidad", ["Mensual", "Trimestral"], default="Mensual",
                                     key="pan_grano") or "Mensual"

    g1, g2 = st.columns([2, 1], gap="medium")
    with g1:
        with ui.tarjeta("panorama_1"):
            ui.grafico(_serie_tiempo(df, metrica, grano), key="pan_tiempo")
    with g2:
        with ui.tarjeta("panorama_2"):
            ui.grafico(_composicion(df), key="pan_comp")

    with ui.tarjeta("panorama_3"):
        ui.grafico(_por_producto(df), key="pan_prod")
