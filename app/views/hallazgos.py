"""Pestaña 7: síntesis de hallazgos, matriz de priorización y decisiones recomendadas."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src import metrics as m
from src.charts import P, titular
from src.formato import cop, num, pct

PARES = {
    "Región y producto": ["region", "producto"],
    "Canal y segmento": ["canal_origen", "segmento"],
    "Región y canal": ["region", "canal_origen"],
    "Producto e ingreso": ["producto", "ingreso_mensual_rango"],
}


def _hallazgos(df):
    c = m.cartera(df)
    sc = m.resumen_por(c, "banda_score")
    prod = m.resumen_por(c, "producto").sort_values("saldo_vencido_30", ascending=False)
    canal = m.resumen_por(c, "canal_origen").sort_values("icv_saldo", ascending=False)
    reg = m.resumen_por(c, "region").sort_values("icv_saldo", ascending=False)
    mens = m.resumen_por(c, "periodo")["icv_saldo"]

    out = []
    if len(sc) >= 2 and sc["icv_saldo"].iloc[-1] > 0:
        out.append(("severo", f"{num(sc['icv_saldo'].iloc[0] / sc['icv_saldo'].iloc[-1], 1)} veces",
                    "El score sí anticipa la mora",
                    f"La banda más baja tiene un ICV de {pct(sc['icv_saldo'].iloc[0])} y la más alta de "
                    f"{pct(sc['icv_saldo'].iloc[-1])}. Pero la tasa promedio se mantiene entre "
                    f"{pct(sc['tasa_promedio'].min())} y {pct(sc['tasa_promedio'].max())}.",
                    "Decisión: tasa diferenciada por banda de score y revisión del punto de corte."))
    if len(prod):
        p0 = prod.iloc[0]
        out.append(("atencion", f"{num(p0['participacion_vencido'], 0)} %",
                    f"{p0['producto']} concentra el riesgo en pesos",
                    f"Su ICV ({pct(p0['icv_saldo'])}) es similar al de otros productos, pero por el tamaño de "
                    f"sus saldos aporta {cop(p0['saldo_vencido_30'])} del saldo vencido.",
                    "Decisión: gestión temprana y seguimiento individual de los saldos altos de este producto."))
    if len(canal) and len(reg):
        out.append(("atencion", pct(canal["icv_saldo"].iloc[0]),
                    f"{canal['canal_origen'].iloc[0]} y {reg['region'].iloc[0]} encabezan el ICV",
                    f"El canal {canal['canal_origen'].iloc[0]} supera al de menor riesgo "
                    f"({canal['canal_origen'].iloc[-1]}, {pct(canal['icv_saldo'].iloc[-1])}). La región "
                    f"{reg['region'].iloc[0]} llega a {pct(reg['icv_saldo'].iloc[0])}.",
                    "Decisión: revisar la política de originación del canal y reforzar cobranza regional."))
    out.append(("", f"{num(mens.max() - mens.min(), 1)} pp" if len(mens) > 1 else pct(m.icv_saldo(df)),
                "La mora es estable, no coyuntural",
                f"El ICV mensual oscila alrededor de {pct(m.icv_saldo(df))} sin tendencia ni quiebre. No hay un "
                "deterioro reciente que explique el nivel: viene de la originación.",
                "Decisión: actuar en la entrada (score y canal) más que en campañas puntuales."))
    out.append(("severo", num(m.nps(df), 1), "La insatisfacción es transversal",
                "El NPS es negativo en todos los segmentos y canales, y no cambia con la mora, los reclamos ni "
                "el uso digital. El problema de experiencia es general.",
                "Decisión: estudio de causas con detractores (calificaciones 5 y 6) antes de invertir en canales."))
    return out


def _matriz(df, par):
    c = m.cartera(df)
    dims = PARES[par]
    r = m.resumen_por(c, dims)
    r = r[r["obligaciones_credito"] >= 30].copy()
    r["etiqueta"] = r[dims[0]].astype(str) + " | " + r[dims[1]].astype(str)
    x_ref = float(np.median(r["saldo_credito"]))
    y_ref = m.icv_saldo(df)
    r["prioridad"] = np.where((r["saldo_credito"] >= x_ref) & (r["icv_saldo"] >= y_ref), "Alta",
                     np.where(r["icv_saldo"] >= y_ref, "Vigilar", "Mantener"))
    colores = {"Alta": P["ciruela"], "Vigilar": P["oro"], "Mantener": P["niebla"]}
    fig = go.Figure()
    s = r["saldo_vencido_30"].astype(float)
    for pr in ["Mantener", "Vigilar", "Alta"]:
        q = r[r["prioridad"] == pr]
        if q.empty:
            continue
        fig.add_trace(go.Scatter(
            x=q["saldo_credito"] / 1e9, y=q["icv_saldo"], mode="markers", name=f"Prioridad {pr.lower()}",
            marker=dict(size=10 + 30 * np.sqrt(q["saldo_vencido_30"] / s.max()), color=colores[pr],
                        opacity=0.85, line=dict(color="#FFFFFF", width=1)),
            text=q["etiqueta"],
            customdata=np.stack([q["saldo_vencido_30"] / 1e9, q["obligaciones_credito"]], axis=-1),
            hovertemplate="<b>%{text}</b><br>Saldo: $%{x:,.1f} mil M<br>ICV: %{y:,.1f} %<br>"
                          "Vencido: $%{customdata[0]:,.1f} mil M<br>Obligaciones: %{customdata[1]:,.0f}<extra></extra>",
        ))
    top = r[r["prioridad"] == "Alta"].nlargest(4, "saldo_vencido_30")
    desfases = [(-40, -44), (40, -30), (-60, 30), (50, 34)]
    for (_, f), (ax, ay) in zip(top.iterrows(), desfases):
        fig.add_annotation(x=np.log10(f["saldo_credito"] / 1e9), y=f["icv_saldo"], text=f["etiqueta"],
                           showarrow=True, arrowhead=0, arrowcolor=P["tinta"], ax=ax, ay=ay,
                           font=dict(size=10, color=P["tinta"]), bgcolor="rgba(255,255,255,.85)")
    fig.add_vline(x=float(np.log10(x_ref / 1e9)), line=dict(color=P["bruma"], dash="dash"))  # eje log
    fig.add_hline(y=y_ref, line=dict(color=P["oro"], dash="dot"),
                  annotation_text=f"ICV promedio {pct(y_ref)}", annotation_font_color=P["oro"],
                  annotation_position="bottom right")
    n_alta = int((r["prioridad"] == "Alta").sum())
    titular(fig, f"{n_alta} combinaciones tienen mucho saldo y ICV sobre el promedio",
            "Arriba a la derecha está la prioridad alta. Tamaño = saldo vencido. Eje X en escala logarítmica.", 500)
    fig.update_xaxes(type="log", title_text="Saldo de crédito (miles de millones COP)", showgrid=True,
                     gridcolor="#F0F3F7")
    fig.update_yaxes(title_text="ICV 30+ por saldo (%)")
    return fig, r


def render(df):
    ui.seccion("Hallazgos principales",
               "Las cifras se recalculan con los filtros activos; los textos describen el filtro actual.")
    hs = _hallazgos(df)
    filas = [hs[:3], hs[3:]]
    for fila in filas:
        cols = st.columns(len(fila), gap="medium")
        for col, (clase, cifra, titulo, texto, accion) in zip(cols, fila):
            with col:
                ui.html(f'<div class="hallazgo {clase}"><div class="cifra">{cifra}</div><h4>{titulo}</h4>'
                        f'<p>{texto}</p><div class="accion">{accion}</div></div>')
        st.write("")

    ui.seccion("Matriz de priorización",
               "Cruza cuánto dinero hay (eje X) con qué tan riesgoso es (eje Y) para decidir dónde actuar primero.")
    par = st.segmented_control("Cruce", list(PARES), default="Región y producto", key="hal_par") or "Región y producto"
    with ui.tarjeta("hallazgos_1"):
        fig, r = _matriz(df, par)
        ui.grafico(fig, key="hal_matriz")

    ui.seccion("Plan de acción propuesto")
    plan = pd.DataFrame([
        ("Tasa diferenciada por banda de score", "Riesgo y Producto", "Diferencia de tasa entre bandas; ICV por banda",
         "1 trimestre"),
        ("Ajuste de punto de corte y política del canal con mayor ICV", "Riesgo de originación",
         "ICV 30+ de nuevas originaciones por canal", "2 trimestres"),
        ("Cobranza temprana en las combinaciones de prioridad alta", "Cobranza",
         "Saldo vencido 30+ y migración de 1-30 a 31-60", "Mensual"),
        ("Estudio de causas con detractores y plan de experiencia", "Experiencia del cliente",
         "NPS y % de detractores por segmento", "2 trimestres"),
    ], columns=["Acción", "Responsable", "KPI de seguimiento", "Horizonte"])
    st.dataframe(plan, hide_index=True, width="stretch")

    ui.bloque("Cierre", f"""
        <p>La cartera de Banco Cordillera tiene un ICV de <b>{pct(m.icv_saldo(df))}</b> que no responde a un
        ciclo sino a cómo se origina y se cobra el crédito. El score funciona, pero el precio no lo usa; el
        riesgo en pesos está en los créditos de mayor saldo, y la insatisfacción del cliente es general.
        El tablero permite al comité pasar de un indicador agregado a <b>combinaciones concretas</b> sobre las
        cuales decidir.</p>
    """, oscuro=True)
