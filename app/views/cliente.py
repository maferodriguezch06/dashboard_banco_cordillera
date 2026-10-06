"""Pestaña 6 (pregunta 3): experiencia del cliente, uso digital y su relación con el riesgo."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from app import ui
from src import metrics as m
from src.charts import COLOR_NPS, P, linea_referencia, titular
from src.formato import num, pct

DIMENSIONES = {"Segmento": "segmento", "Canal": "canal_origen", "Región": "region",
               "Producto": "producto", "Estado de la obligación": "estado_obligacion"}


def _composicion_nps(df, dim):
    r = df[df["nps_respondio"]].groupby([dim, "categoria_nps"], observed=True).size().reset_index(name="n")
    r["pct"] = 100 * r["n"] / r.groupby(dim, observed=True)["n"].transform("sum")
    resumen = m.resumen_por(df, dim).set_index(dim)["nps"]
    fig = go.Figure()
    for cat in ["Detractor", "Pasivo", "Promotor"]:
        s = r[r["categoria_nps"] == cat]
        fig.add_trace(go.Bar(y=s[dim].astype(str), x=s["pct"], orientation="h", name=cat,
                             marker_color=COLOR_NPS[cat],
                             text=[f"{num(v, 0)} %" for v in s["pct"]], textposition="inside",
                             insidetextanchor="middle",
                             textfont=dict(color="#FFFFFF" if cat != "Pasivo" else P["tinta"], size=11),
                             hovertemplate="<b>%{y}</b><br>" + cat + ": %{x:,.1f} %<extra></extra>"))
    for i, (k, v) in enumerate(resumen.items()):
        fig.add_annotation(x=1.01, xref="paper", y=str(k), text=f"NPS {num(v, 1)}", showarrow=False, xanchor="left",
                           font=dict(size=11, color=P["tinta"]))
    titular(fig, "Los detractores superan a los promotores en todos los grupos",
            "Composición de las respuestas. A la derecha, el NPS de cada grupo.", 380)
    fig.update_layout(barmode="stack", margin=dict(r=86, b=60), legend=dict(y=-0.2))
    fig.update_xaxes(range=[0, 100], title_text="% de respuestas")
    return fig


def _nps_tiempo(df):
    r = m.resumen_por(df, "trimestre").sort_values("trimestre")
    fig = go.Figure(go.Scatter(x=r["trimestre"], y=r["nps"], mode="lines+markers",
                               line=dict(color=P["tinta"], width=2.4), marker=dict(size=7, color=P["tinta"]),
                               customdata=r["respuestas"],
                               hovertemplate="<b>%{x}</b><br>NPS: %{y:,.1f}<br>Respuestas: %{customdata:,.0f}"
                                             "<extra></extra>"))
    linea_referencia(fig, 0, "NPS = 0")
    titular(fig, f"El NPS no sale de terreno negativo ({num(r['nps'].min(), 1)} a {num(r['nps'].max(), 1)})",
            "NPS trimestral.", 380)
    fig.update_xaxes(type="category")
    return fig


def _digital_riesgo(df):
    r = m.resumen_por(df, "banda_digital")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    etq = r["banda_digital"].astype(str).str.replace(" (", "<br>(", regex=False)
    fig.add_trace(go.Bar(x=etq, y=r["icv_saldo"], name="ICV por saldo",
                         marker_color=P["acero"], text=[pct(v) for v in r["icv_saldo"]], textposition="outside",
                         cliponaxis=False, customdata=r["registros"],
                         hovertemplate="<b>%{x}</b><br>ICV: %{y:,.2f} %<br>Registros: %{customdata:,.0f}"
                                       "<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=etq, y=r["nps"], name="NPS", mode="lines+markers",
                             line=dict(color=P["oro"], width=2.4), marker=dict(size=8),
                             hovertemplate="NPS: %{y:,.1f}<extra></extra>"), secondary_y=True)
    titular(fig, "Más uso digital no mejora la mora ni el NPS",
            "Bandas de transacciones digitales en 30 días.", 380)
    fig.update_yaxes(title_text="ICV %", secondary_y=False, range=[0, r["icv_saldo"].max() * 1.3])
    fig.update_yaxes(title_text="NPS", secondary_y=True, showgrid=False, range=[-30, 10], dtick=10)
    fig.update_xaxes(tickangle=0)
    return fig


def _reclamos(df):
    d = df.assign(grupo=df["reclamos_90d"].clip(upper=2).map({0: "0", 1: "1", 2: "2 o más"}))
    r = m.resumen_por(d, "grupo").sort_values("grupo")
    fig = go.Figure(go.Bar(x=r["grupo"], y=r["nps"], marker_color=[P["acero"], P["niebla"], P["oro"]][: len(r)],
                           text=[num(v, 1) for v in r["nps"]], textposition="outside", cliponaxis=False,
                           customdata=r["respuestas"],
                           hovertemplate="<b>%{x} reclamos</b><br>NPS: %{y:,.1f}<br>Respuestas: %{customdata:,.0f}"
                                         "<extra></extra>"))
    titular(fig, "Los reclamos no explican el NPS", "NPS según reclamos en 90 días. El grupo de 2 o más tiene pocas respuestas.", 380)
    lo, hi = min(r["nps"].min(), 0), max(r["nps"].max(), 0)
    fig.update_yaxes(range=[lo * 1.4 - 1, hi * 1.4 + 2], title_text="NPS")
    fig.update_xaxes(title_text="Reclamos en 90 días", type="category")
    return fig


def _distribucion(df):
    r = df["nps_0a10"].dropna().astype(int).value_counts().sort_index()
    colores = [COLOR_NPS["Detractor"] if k <= 6 else COLOR_NPS["Pasivo"] if k <= 8 else COLOR_NPS["Promotor"]
               for k in r.index]
    fig = go.Figure(go.Bar(x=r.index, y=r.values, marker_color=colores,
                           hovertemplate="Calificación %{x}: %{y:,.0f} respuestas<extra></extra>"))
    titular(fig, "Las notas 5 y 6 nutren a los detractores",
            "Distribución de la calificación de 0 a 10.", 380)
    fig.update_xaxes(dtick=1, title_text="Calificación")
    fig.update_yaxes(title_text="Respuestas")
    return fig


def render(df):
    ui.seccion("Pregunta 3. ¿La experiencia del cliente y el uso digital se relacionan con el riesgo?",
               "Incluye todos los productos, también la cuenta de ahorros. El NPS se calcula solo sobre quienes "
               "respondieron la encuesta.")
    r = df[df["nps_respondio"]]
    cols = st.columns(6, gap="small")
    datos = [
        ("NPS", num(m.nps(df), 1)),
        ("Promotores (9 y 10)", pct(100 * (r["nps_0a10"] >= 9).mean())),
        ("Detractores (0 a 6)", pct(100 * (r["nps_0a10"] <= 6).mean())),
        ("Tasa de respuesta", pct(100 * df["nps_respondio"].mean())),
        ("Transacciones digitales / mes", num(m.tx_digitales(df), 1)),
        ("Reclamos por cada 100", num(m.reclamos_por_100(df), 1)),
    ]
    for col, (e, v) in zip(cols, datos):
        with col:
            ui.mini(e, v)

    st.write("")
    dim = st.segmented_control("Comparar el NPS por", list(DIMENSIONES), default="Segmento",
                               key="cli_dim") or "Segmento"
    a, b = st.columns([1.35, 1], gap="medium")
    with a:
        with ui.tarjeta("cliente_1"):
            ui.grafico(_composicion_nps(df, DIMENSIONES[dim]), key="cli_comp")
    with b:
        with ui.tarjeta("cliente_2"):
            ui.grafico(_nps_tiempo(df), key="cli_tiempo")

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        with ui.tarjeta("cliente_3"):
            ui.grafico(_digital_riesgo(df), key="cli_digital")
    with c2:
        with ui.tarjeta("cliente_4"):
            ui.grafico(_reclamos(df), key="cli_reclamos")
    with c3:
        with ui.tarjeta("cliente_5"):
            ui.grafico(_distribucion(df), key="cli_dist")
