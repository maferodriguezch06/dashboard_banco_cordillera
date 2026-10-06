"""Pestaña 5 (pregunta 2): segmentos, canales y territorios que requieren gestión prioritaria."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src import metrics as m
from src.charts import ESCALA_RIESGO, P, colores_destacados, titular
from src.formato import cop, num, pct

DIMENSIONES = {
    "Segmento": "segmento", "Canal de origen": "canal_origen", "Tipo de canal": "tipo_canal",
    "Región": "region", "Rango de ingreso": "ingreso_mensual_rango", "Producto": "producto",
}


def _matriz(c, fila, col):
    r = m.resumen_por(c, [DIMENSIONES[fila], DIMENSIONES[col]])
    tabla = r.pivot(index=DIMENSIONES[fila], columns=DIMENSIONES[col], values="icv_saldo")
    n = r.pivot(index=DIMENSIONES[fila], columns=DIMENSIONES[col], values="obligaciones_credito")
    fig = go.Figure(go.Heatmap(
        z=tabla.values, x=[str(x) for x in tabla.columns], y=[str(y) for y in tabla.index],
        colorscale=ESCALA_RIESGO, xgap=3, ygap=3, customdata=n.values,
        text=[[pct(v) for v in f] for f in tabla.values], texttemplate="%{text}", textfont=dict(size=11),
        colorbar=dict(title=dict(text="ICV %", font=dict(size=11)), thickness=10),
        hovertemplate="<b>%{y}</b> | %{x}<br>ICV por saldo: %{z:,.2f} %<br>Obligaciones: %{customdata:,.0f}"
                      "<extra></extra>",
    ))
    mx = r.loc[r["icv_saldo"].idxmax()]
    titular(fig, f"Combinación más riesgosa: {mx[DIMENSIONES[fila]]} con {mx[DIMENSIONES[col]]} "
                 f"({pct(mx['icv_saldo'])})",
            f"ICV 30+ por saldo cruzando {fila.lower()} y {col.lower()}.", 420)
    return fig


def _mapa(c, tamano):
    r = m.resumen_por(c, ["ciudad", "lat", "lon", "region"])
    size_col = {"Saldo vencido": "saldo_vencido_30", "Saldo de crédito": "saldo_credito",
                "Obligaciones": "obligaciones_credito"}[tamano]
    s = r[size_col].astype(float)
    tam = 12 + 38 * np.sqrt(s / s.max()) if s.max() > 0 else np.full(len(s), 14.0)
    fig = go.Figure(go.Scattergeo(
        lat=r["lat"], lon=r["lon"], mode="markers+text", textposition="top center",
        textfont=dict(size=10, color=P["tinta"]),
        marker=dict(size=tam, color=r["icv_saldo"], colorscale=ESCALA_RIESGO, opacity=0.9,
                    line=dict(color="#FFFFFF", width=1),
                    colorbar=dict(title=dict(text="ICV %", font=dict(size=11)), thickness=10)),
        text=r["ciudad"],
        customdata=np.stack([r["region"], r["icv_saldo"], r["saldo_vencido_30"], r["obligaciones_credito"]], axis=-1),
        hovertemplate="<b>%{text}</b> (%{customdata[0]})<br>ICV: %{customdata[1]:,.1f} %"
                      "<br>Saldo vencido: $%{customdata[2]:,.0f}<br>Obligaciones: %{customdata[3]:,.0f}<extra></extra>",
    ))
    # Scattergeo no depende de mapas en línea: funciona sin internet durante la sustentación
    fig.update_geos(scope="south america", lataxis_range=[1.5, 12.8], lonaxis_range=[-79.5, -70.5],
                    showcountries=True, countrycolor=P["bruma"], showland=True, landcolor="#F3F6F9",
                    showocean=True, oceancolor="#E3EBF3", showlakes=False, showframe=False,
                    coastlinecolor=P["bruma"], projection_type="mercator", bgcolor="#FFFFFF", resolution=50)
    titular(fig, "Mapa de exposición por ciudad", f"Tamaño = {tamano.lower()}. Color = ICV por saldo.", 470)
    fig.update_layout(margin=dict(l=8, r=8, t=64, b=8))
    return fig


def _ranking_ciudad(c, promedio):
    r = m.resumen_por(c, "ciudad").sort_values("icv_saldo")
    fig = go.Figure(go.Bar(
        y=r["ciudad"], x=r["icv_saldo"], orientation="h",
        marker_color=colores_destacados(r["icv_saldo"].tolist(), promedio),
        text=[pct(v) for v in r["icv_saldo"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>ICV: %{x:,.2f} %<extra></extra>",
    ))
    fig.add_vline(x=promedio, line=dict(color=P["oro"], dash="dot", width=1.5))
    titular(fig, f"{r.iloc[-1]['ciudad']} lidera el ICV por ciudad", "Ocre: sobre el promedio del filtro.", 470)
    fig.update_xaxes(range=[0, r["icv_saldo"].max() * 1.25], title_text="%")
    return fig


def _barras_dim(c, dim, titulo, promedio):
    r = m.resumen_por(c, dim)
    etiquetas = r[dim].astype(str).tolist()
    fig = go.Figure(go.Bar(
        x=etiquetas, y=r["icv_saldo"], marker_color=colores_destacados(r["icv_saldo"].tolist(), promedio),
        text=[pct(v) for v in r["icv_saldo"]], textposition="outside", cliponaxis=False,
        customdata=r[["obligaciones_credito", "saldo_vencido_30"]].values,
        hovertemplate="<b>%{x}</b><br>ICV: %{y:,.2f} %<br>Obligaciones: %{customdata[0]:,.0f}"
                      "<br>Saldo vencido: $%{customdata[1]:,.0f}<extra></extra>",
    ))
    fig.add_hline(y=promedio, line=dict(color=P["oro"], dash="dot", width=1.5))
    mx = r.loc[r["icv_saldo"].idxmax()]
    titular(fig, titulo.format(mx=mx[dim], v=pct(mx["icv_saldo"])), "ICV 30+ por saldo. Ocre: sobre el promedio.", 340)
    fig.update_yaxes(range=[0, r["icv_saldo"].max() * 1.25], title_text="%")
    return fig


def render(df):
    c = m.cartera(df)
    promedio = m.icv_saldo(df)
    ui.seccion("Pregunta 2. ¿Qué segmentos, canales y territorios requieren gestión prioritaria?",
               f"El promedio del filtro actual es {pct(promedio)}. Cambie las dimensiones de la matriz para buscar "
               "concentraciones que un solo corte no muestra.")

    k1, k2 = st.columns(2)
    with k1:
        fila = st.selectbox("Filas de la matriz", list(DIMENSIONES), index=1, key="seg_fila")
    with k2:
        opciones = [d for d in DIMENSIONES if d != fila]
        col = st.selectbox("Columnas de la matriz", opciones, index=0, key="seg_col")
    with ui.tarjeta("segmentos_1"):
        ui.grafico(_matriz(c, fila, col), key="seg_matriz")

    e1, e2 = st.columns(2, gap="medium")
    with e1:
        with ui.tarjeta("segmentos_2"):
            ui.grafico(_barras_dim(c, "canal_origen", "Por canal, {mx} tiene el ICV más alto ({v})", promedio),
                       key="seg_canal")
    with e2:
        with ui.tarjeta("segmentos_3"):
            ui.grafico(_barras_dim(c, "ingreso_mensual_rango",
                                   "Por ingreso, el rango {mx} es el más riesgoso ({v})", promedio), key="seg_ing")

    ui.seccion("Territorio")
    tamano = st.segmented_control("Tamaño de la burbuja", ["Saldo vencido", "Saldo de crédito", "Obligaciones"],
                                  default="Saldo vencido", key="seg_tam") or "Saldo vencido"
    t1, t2 = st.columns([1.5, 1], gap="medium")
    with t1:
        with ui.tarjeta("segmentos_4"):
            ui.grafico(_mapa(c, tamano), key="seg_mapa")
    with t2:
        with ui.tarjeta("segmentos_5"):
            ui.grafico(_ranking_ciudad(c, promedio), key="seg_ciudad")

    ui.seccion("Combinaciones a priorizar",
               "Región, producto, canal y segmento. El volumen mínimo evita conclusiones con pocos casos.")
    minimo = st.slider("Obligaciones mínimas por combinación", 20, 300, 80, 10, key="seg_min")
    r = m.resumen_por(c, ["region", "producto", "canal_origen", "segmento"])
    r = r[r["obligaciones_credito"] >= minimo].sort_values("saldo_vencido_30", ascending=False)
    r = r[r["icv_saldo"] > promedio].head(15)
    if r.empty:
        st.info("Ninguna combinación supera el promedio con ese volumen mínimo. Baje el mínimo de obligaciones.")
        return
    tabla = r[["region", "producto", "canal_origen", "segmento", "obligaciones_credito", "icv_saldo",
               "saldo_vencido_30"]].copy()
    tabla["saldo_vencido_30"] = tabla["saldo_vencido_30"].map(cop)
    for col_ in ["producto", "canal_origen", "segmento"]:
        tabla[col_] = tabla[col_].astype(str)
    st.dataframe(
        tabla, hide_index=True, width="stretch",
        column_config={
            "region": "Región", "producto": "Producto", "canal_origen": "Canal", "segmento": "Segmento",
            "obligaciones_credito": st.column_config.NumberColumn("Obligaciones", format="%d"),
            "icv_saldo": st.column_config.ProgressColumn("ICV por saldo", format="%.1f %%", min_value=0,
                                                         max_value=float(max(30, r["icv_saldo"].max()))),
            "saldo_vencido_30": "Saldo vencido 30+",
        },
    )
    ui.html(f'<div class="texto-seccion">Se muestran las combinaciones con ICV sobre el promedio ({pct(promedio)}), '
            'ordenadas por saldo vencido en pesos: primero lo que más dinero expone.</div>')
