"""Pestaña 4 (pregunta 1): dónde se concentra el riesgo y qué tan bien lo anticipa el score.

Interacción clave: al hacer clic en una barra de producto, los gráficos de score y de estados
se filtran por ese producto (selección cruzada).
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from app import ui
from src import metrics as m
from src.charts import COLOR_ESTADO, ESCALA_RIESGO, P, colores_destacados, titular
from src.formato import num, pct

MEDIDAS = {"Por saldo": ("icv_saldo", "ICV por saldo"), "Por número": ("icv_conteo", "ICV por número")}


def _seleccion_producto(evento) -> str | None:
    try:
        puntos = evento.selection.points  # type: ignore[attr-defined]
    except AttributeError:
        puntos = (evento or {}).get("selection", {}).get("points", []) if isinstance(evento, dict) else []
    if puntos:
        return puntos[0].get("y")
    return None


def _barras_producto(c, campo, etiqueta, promedio, seleccion):
    r = m.resumen_por(c, "producto").sort_values(campo)
    etiquetas = r["producto"].astype(str).tolist()
    fig = go.Figure(go.Bar(
        y=etiquetas, x=r[campo], orientation="h",
        marker_color=colores_destacados(r[campo].tolist(), promedio, seleccion=seleccion, etiquetas=etiquetas),
        text=[pct(v) for v in r[campo]], textposition="outside", cliponaxis=False,
        customdata=r[["obligaciones_credito", "saldo_vencido_30"]].values,
        hovertemplate="<b>%{y}</b><br>" + etiqueta + ": %{x:,.2f} %<br>Obligaciones: %{customdata[0]:,.0f}"
                      "<br>Saldo vencido: $%{customdata[1]:,.0f}<extra></extra>",
    ))
    fig.add_vline(x=promedio, line=dict(color=P["oro"], dash="dot", width=1.5),
                  annotation_text=f"Promedio {pct(promedio)}", annotation_font_color=P["oro"],
                  annotation_position="bottom right")
    rango = r[campo].max() - r[campo].min()
    titular(fig, f"Entre productos el ICV solo varía {num(rango, 1)} pp",
            "Haga clic en un producto para filtrar los gráficos de la derecha y de abajo. Ocre: sobre el promedio.",
            340)
    fig.update_xaxes(range=[0, r[campo].max() * 1.22], title_text="%")
    fig.update_layout(clickmode="event+select")
    return fig


def _treemap(c):
    r = m.resumen_por(c, ["familia", "producto"])
    fig = go.Figure(go.Treemap(
        labels=r["producto"].astype(str), parents=[""] * len(r), values=r["saldo_vencido_30"],
        marker=dict(colors=r["icv_saldo"], colorscale=ESCALA_RIESGO, line=dict(color="#FFFFFF", width=2),
                    pad=dict(t=0, l=0, r=0, b=0),
                    colorbar=dict(title=dict(text="ICV %", font=dict(size=11)), thickness=10, len=0.8)),
        customdata=r[["participacion_vencido", "icv_saldo"]].values,
        texttemplate="<b>%{label}</b><br>%{customdata[0]:,.1f} % del vencido",
        hovertemplate="<b>%{label}</b><br>Saldo vencido: $%{value:,.0f}<br>Participación: %{customdata[0]:,.1f} %"
                      "<br>ICV: %{customdata[1]:,.1f} %<extra></extra>",
        textfont=dict(color="#FFFFFF"), root_color="#FFFFFF", pathbar=dict(visible=False),
    ))
    titular(fig, "En pesos, el riesgo está en vivienda y vehículo",
            "Área = saldo vencido 30+. Color = ICV del producto.", 340)
    fig.update_layout(margin=dict(l=8, r=8, t=64, b=8))
    return fig


def _score(c, campo, etiqueta):
    r = m.resumen_por(c, "banda_score")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colores = [P["ciruela"], "#5B4A80", P["acero"], P["niebla"], P["bruma"]][: len(r)]
    fig.add_trace(go.Bar(x=r["banda_score"].astype(str), y=r[campo], name=etiqueta, marker_color=colores,
                         text=[pct(v) for v in r[campo]], textposition="outside", cliponaxis=False,
                         customdata=r["obligaciones_credito"],
                         hovertemplate="<b>Score %{x}</b><br>" + etiqueta + ": %{y:,.2f} %"
                                       "<br>Obligaciones: %{customdata:,.0f}<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=r["banda_score"].astype(str), y=r["tasa_promedio"], name="Tasa E.A. promedio",
                             mode="lines+markers", line=dict(color=P["oro"], width=2.4),
                             marker=dict(size=8, color=P["oro"]),
                             hovertemplate="Tasa promedio: %{y:,.2f} %<extra></extra>"), secondary_y=True)
    if len(r) >= 2:
        titulo = f"El score separa el riesgo: de {pct(r[campo].iloc[0])} a {pct(r[campo].iloc[-1])}"
    else:
        titulo = "ICV por banda de score"
    titular(fig, titulo, "La tasa (línea ocre) casi no cambia entre bandas: el precio no refleja el riesgo.", 380)
    fig.update_yaxes(title_text="ICV %", secondary_y=False, range=[0, r[campo].max() * 1.25])
    fig.update_yaxes(title_text="Tasa E.A. %", secondary_y=True, showgrid=False,
                     range=[0, max(r["tasa_promedio"].max() * 1.6, 1)], tickformat=".0f")
    fig.update_xaxes(title_text="Banda de score")
    return fig


def _estados(c):
    t = c.groupby(["producto", "estado_obligacion"], observed=True).size().reset_index(name="n")
    t["pct"] = 100 * t["n"] / t.groupby("producto", observed=True)["n"].transform("sum")
    fig = go.Figure()
    for e in [x for x in COLOR_ESTADO if x != "Al día"]:
        s = t[t["estado_obligacion"] == e]
        if s.empty:
            continue
        fig.add_trace(go.Bar(x=s["producto"].astype(str).str.replace(" ", "<br>", n=1), y=s["pct"], name=e,
                             marker_color=COLOR_ESTADO[e],
                             hovertemplate="<b>%{x}</b><br>" + e + ": %{y:,.1f} %<extra></extra>"))
    titular(fig, "Cerca de la mitad de la mora ya supera 60 días",
            "% de obligaciones de cada producto en cada tramo de mora. El resto está al día.", 380)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="% de obligaciones del producto")
    return fig


def _mapa_calor(c, campo, etiqueta):
    r = m.resumen_por(c, ["region", "producto"])
    tabla = r.pivot(index="region", columns="producto", values=campo)
    fig = go.Figure(go.Heatmap(
        z=tabla.values, x=[str(x) for x in tabla.columns], y=tabla.index.tolist(), colorscale=ESCALA_RIESGO,
        text=[[pct(v) for v in fila] for fila in tabla.values], texttemplate="%{text}",
        textfont=dict(size=11), xgap=3, ygap=3,
        colorbar=dict(title=dict(text="%", font=dict(size=11)), thickness=10),
        hovertemplate="<b>%{y}</b> | %{x}<br>" + etiqueta + ": %{z:,.2f} %<extra></extra>",
    ))
    mx = r.loc[r[campo].idxmax()]
    titular(fig, f"Punto más crítico: {mx['producto']} en {mx['region']} ({pct(mx[campo])})",
            "Celdas más oscuras = mayor ICV. Cruce de región y producto.", 420)
    return fig


def render(df):
    c = m.cartera(df)
    ui.seccion("Pregunta 1. ¿Dónde se concentra el riesgo y qué tan bien lo anticipa el score?",
               "Seleccione cómo medir el ICV. Por saldo pondera por el dinero expuesto; por número cuenta "
               "obligaciones.")
    medida = st.segmented_control("Medida", list(MEDIDAS), default="Por saldo", key="rie_medida") or "Por saldo"
    campo, etiqueta = MEDIDAS[medida]
    promedio = m.icv_saldo(df) if campo == "icv_saldo" else m.icv_conteo(df)

    seleccion = st.session_state.get("sel_producto")
    a, b = st.columns([1.15, 1], gap="medium")
    with a:
        with ui.tarjeta("riesgo_1"):
            evento = ui.grafico(_barras_producto(c, campo, etiqueta, promedio, seleccion), key="rie_barras",
                                on_select="rerun", selection_mode="points")
            # Solo se aplica cuando el clic cambia; así "Quitar selección" no se revierte
            nueva = _seleccion_producto(evento)
            if nueva != st.session_state.get("rie_ultimo_clic"):
                st.session_state["rie_ultimo_clic"] = nueva
                if nueva:
                    st.session_state["sel_producto"] = nueva
                else:
                    st.session_state.pop("sel_producto", None)
                st.rerun()
    with b:
        with ui.tarjeta("riesgo_2"):
            ui.grafico(_treemap(c), key="rie_tree")

    seleccion = st.session_state.get("sel_producto")
    sub = c[c["producto"] == seleccion] if seleccion else c
    if seleccion:
        f1, f2 = st.columns([4, 1])
        with f1:
            ui.html(f'<span class="filtro-activo">Selección cruzada: {seleccion}</span>')
        with f2:
            if st.button("Quitar selección", key="rie_quitar"):
                st.session_state.pop("sel_producto", None)
                st.rerun()

    d1, d2 = st.columns([1.15, 1], gap="medium")
    with d1:
        with ui.tarjeta("riesgo_3"):
            ui.grafico(_score(sub, campo, etiqueta), key="rie_score")
    with d2:
        with ui.tarjeta("riesgo_4"):
            ui.grafico(_estados(sub), key="rie_estados")

    with ui.tarjeta("riesgo_5"):
        ui.grafico(_mapa_calor(c, campo, etiqueta), key="rie_calor")
