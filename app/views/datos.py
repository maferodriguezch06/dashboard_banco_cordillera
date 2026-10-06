"""Pestaña 2: origen, perfilamiento, transformación y modelo de datos."""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src.charts import P, titular
from src.config import ruta
from src.formato import num, pct


@st.cache_data
def _perfil():
    with open(ruta("reportes") / "perfil_datos.json", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _diccionario():
    return pd.read_csv(ruta("reportes") / "diccionario_datos.csv", encoding="utf-8-sig")


def render(df, tamanos):
    perfil = _perfil()
    nps_falt = next(v for v in perfil["variables"] if v["variable"] == "nps_0a10")

    c1, c2 = st.columns([1.3, 1], gap="medium")
    with c1:
        ui.bloque("Origen de los datos", f"""
            <p>Archivo <b>04_banco_minorista.csv</b>, sintético y anonimizado.
            Cubre cortes del <b>{perfil['fecha_min']}</b> al <b>{perfil['fecha_max']}</b>.</p>
            <p><b>Unidad de observación:</b> una obligación o producto de un cliente en una fecha de corte.
            El mismo cliente aparece hasta {perfil['registros_por_cliente_max']} veces y sus atributos
            (ciudad, segmento) pueden variar entre cortes, por eso cada fila se analiza como una foto
            independiente y no se construye una dimensión de cliente con atributos fijos.</p>
        """)
    with c2:
        a, b = st.columns(2)
        with a:
            ui.mini("Registros", num(perfil["filas"]))
            ui.mini("Clientes únicos", num(perfil["clientes_unicos"]))
            ui.mini("Duplicados exactos", num(perfil["duplicados_exactos"]))
        with b:
            ui.mini("Variables originales", num(perfil["columnas"]))
            ui.mini("NPS sin respuesta", f"{num(nps_falt['faltantes'])} ({pct(nps_falt['pct_faltantes'], 1)})")
            ui.mini("Ahorros con días de mora", num(perfil["ahorros_con_dias_mora"]))

    ui.seccion("Perfilamiento y decisiones de calidad",
               "Ningún registro se eliminó. Cada problema quedó resuelto con una regla documentada o una bandera.")
    revisiones = pd.DataFrame([
        ("Codificación", "El encabezado trae un BOM (carácter invisible en la primera columna)",
         "Lectura con utf-8-sig"),
        ("Faltantes", f"nps_0a10 tiene {num(nps_falt['faltantes'])} vacíos ({pct(nps_falt['pct_faltantes'])}); "
         "el resto de variables está completo", "No se imputa; se excluye solo del cálculo de NPS y se crea "
         "la categoría Sin respuesta"),
        ("Coherencia", "Estado de la obligación frente a días de mora",
         f"{num(perfil['incoherencias_estado_vs_dias'])} incoherencias; se usa dias_mora como fuente"),
        ("Regla de negocio", f"{num(perfil['ahorros_con_dias_mora'])} cuentas de ahorro registran días de mora",
         "Se interpretan como sobregiro y la cuenta de ahorros sale de los KPI de cartera"),
        ("Duplicados", f"0 exactos; {num(perfil['duplicados_cliente_fecha_producto'])} con mismo cliente, "
         "fecha y producto", "Se conservan (pueden ser dos obligaciones) y se marcan"),
        ("Atípicos", f"{num(int(df['saldo_atipico'].sum()))} saldos sobre Q3 + 1,5·IQR de su producto",
         "Se conservan: en vivienda son reales y explican el riesgo en pesos"),
        ("Rangos", "Score 350 a 900, NPS 0 a 10, días de mora 0 a 120, saldos positivos",
         "Sin valores fuera de rango"),
    ], columns=["Revisión", "Hallazgo", "Decisión"])
    st.dataframe(revisiones, hide_index=True, width="stretch")

    ui.seccion("Clasificación de variables", "Naturaleza y función analítica dentro del tablero.")
    dic = _diccionario()
    perfil_vars = pd.DataFrame(perfil["variables"])[["variable", "tipo_origen", "faltantes", "valores_unicos"]]
    tabla = dic.merge(perfil_vars, on="variable", how="left")
    st.dataframe(
        tabla, hide_index=True, width="stretch", height=360,
        column_config={
            "variable": "Variable", "naturaleza": "Naturaleza", "funcion_analitica": "Función",
            "descripcion": st.column_config.TextColumn("Descripción", width="large"),
            "tipo_origen": "Tipo original", "faltantes": "Faltantes", "valores_unicos": "Valores únicos",
        },
    )

    ui.seccion("Flujo de transformación", "Se ejecuta con scripts/construir_datos.py y queda en data/processed.")
    pasos = ["CSV crudo", "Perfilamiento", "Limpieza y tipado", "Variables derivadas",
             "Modelo estrella", "Tablero Streamlit"]
    detalle = ["57.000 filas, 17 columnas", "Tipos, rangos, faltantes, duplicados",
               "Fechas, enteros, texto sin espacios", "Banderas de mora, bandas, NPS",
               "1 tabla de hechos + 6 dimensiones", "Filtros, KPI y gráficos"]
    fig = go.Figure()
    for i, (p_, d_) in enumerate(zip(pasos, detalle)):
        color = P["tinta"] if i in (0, len(pasos) - 1) else P["acero"]
        fig.add_shape(type="rect", x0=i * 1.0, x1=i * 1.0 + 0.86, y0=0, y1=1, fillcolor=color,
                      line=dict(width=0), layer="below")
        fig.add_annotation(x=i + 0.43, y=0.66, text=f"<b>{p_}</b>", showarrow=False,
                           font=dict(color="#FFFFFF", size=12))
        fig.add_annotation(x=i + 0.43, y=0.32, text=d_, showarrow=False,
                           font=dict(color="#DCE5EE", size=10), width=130)
        if i < len(pasos) - 1:
            fig.add_annotation(x=i + 0.98, y=0.5, ax=i + 0.88, ay=0.5, xref="x", yref="y", axref="x",
                               ayref="y", showarrow=True, arrowhead=2, arrowcolor=P["oro"], arrowwidth=2, text="")
    fig.update_xaxes(visible=False, range=[-0.05, len(pasos) - 0.1])
    fig.update_yaxes(visible=False, range=[-0.1, 1.1])
    fig.update_layout(height=150, margin=dict(l=8, r=8, t=8, b=8))
    ui.grafico(fig, key="flujo")

    ui.seccion("Modelo de datos", "Esquema estrella: relaciones uno a muchos de cada dimensión hacia los hechos.")
    m1, m2 = st.columns([1.4, 1], gap="medium")
    with m1:
        dims = [("dim_fecha", "fecha_key", 1.0, 2.0), ("dim_geografia", "geo_key", 0.0, 1.3),
                ("dim_producto", "producto_key", 2.0, 1.3), ("dim_segmento", "segmento_key", 0.0, -0.3),
                ("dim_canal", "canal_key", 2.0, -0.3), ("dim_ingreso", "ingreso_key", 1.0, -1.0)]
        fig = go.Figure()
        for nombre, llave, x, y in dims:
            fig.add_shape(type="line", x0=1, y0=0.5, x1=x, y1=y, line=dict(color=P["bruma"], width=2), layer="below")
        fig.add_trace(go.Scatter(
            x=[d[2] for d in dims], y=[d[3] for d in dims], mode="markers+text",
            marker=dict(size=92, color=P["acero"], symbol="square"),
            text=[f"<b>{d[0]}</b><br>{num(tamanos[d[0]][0])} filas" for d in dims],
            textfont=dict(color="#FFFFFF", size=10), hovertext=[f"Llave: {d[1]}" for d in dims],
            hoverinfo="text", showlegend=False))
        fig.add_trace(go.Scatter(
            x=[1], y=[0.5], mode="markers+text", marker=dict(size=124, color=P["tinta"], symbol="square"),
            text=[f"<b>fact_obligacion</b><br>{num(tamanos['fact_obligacion'][0])} filas"],
            textfont=dict(color="#FFFFFF", size=11), hoverinfo="text",
            hovertext=["Grano: obligación por fecha de corte"], showlegend=False))
        fig.update_xaxes(visible=False, range=[-0.55, 2.55])
        fig.update_yaxes(visible=False, range=[-1.6, 2.6])
        fig.update_layout(height=440, margin=dict(l=8, r=8, t=8, b=8))
        ui.grafico(fig, key="modelo")
    with m2:
        ui.bloque("Lógica del modelo", """
            <p><b>Hechos:</b> una fila por obligación y fecha de corte, con medidas (saldo, score, días de mora,
            tasa, transacciones, reclamos, NPS) y banderas derivadas.</p>
            <p><b>Dimensiones:</b> fecha (calendario diario), geografía (con coordenadas añadidas para el mapa),
            producto (familia y si es crédito), segmento, canal (digital, presencial, tercero) e ingreso
            (orden ordinal).</p>
            <p>La app une los hechos con las dimensiones al cargar y todos los KPI se calculan en
            <b>src/metrics.py</b>, una sola definición para todo el tablero.</p>
        """)

    ui.seccion("Variables derivadas principales")
    st.dataframe(pd.DataFrame([
        ("vencida_30 / severa_60", "dias_mora > 30 / > 60", "Banderas para ICV y mora severa"),
        ("saldo_vencido_30", "saldo si vencida_30", "Numerador del ICV por saldo"),
        ("banda_score", "5 rangos de score", "Evaluar si el score separa el riesgo"),
        ("banda_digital", "4 rangos de transacciones 30 días", "Relación entre uso digital y riesgo"),
        ("categoria_nps", "Promotor, Pasivo, Detractor, Sin respuesta", "Cálculo y composición del NPS"),
        ("periodo / trimestre", "Desde fecha_corte", "Análisis temporal y variaciones"),
        ("alerta_ahorro_con_mora", "Ahorros con días de mora", "Calidad de datos"),
    ], columns=["Variable", "Regla", "Uso"]), hide_index=True, width="stretch")
