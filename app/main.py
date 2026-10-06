"""Punto de entrada del tablero.

Ejecutar desde la raíz del proyecto:
    streamlit run app/main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Banco Cordillera | Riesgo minorista", page_icon="🏦",
                   layout="wide", initial_sidebar_state="expanded")

from app import ui  # noqa: E402
from app.views import cliente, contexto, datos, hallazgos, panorama, riesgo, segmentos  # noqa: E402
from src.data import cargar_modelo, filtrar, tabla_analitica  # noqa: E402
from src.formato import num  # noqa: E402


@st.cache_data(show_spinner="Cargando el modelo de datos...")
def obtener_datos():
    modelo = cargar_modelo()
    return tabla_analitica(modelo), {k: v.shape for k, v in modelo.items()}


CLAVES_FILTRO = ["f_periodo", "f_region", "f_producto", "f_segmento", "f_canal"]


def restablecer():
    for k in CLAVES_FILTRO + ["sel_producto"]:
        st.session_state.pop(k, None)


def barra_lateral(df):
    periodos = sorted(df["periodo"].unique())
    with st.sidebar:
        ui.html('<div class="lat-marca"><div class="logo">C</div><b>Banco Cordillera</b></div>')
        st.markdown("**Filtros del análisis**")
        ui.html('<div class="lat-nota">Aplican a Panorama, Riesgo, Segmentos, Cliente y Hallazgos. '
                'Vacío significa todos.</div><br>')
        desde, hasta = st.select_slider("Periodo (mes de corte)", options=periodos,
                                        value=(periodos[0], periodos[-1]), key="f_periodo")
        region = st.multiselect("Región", sorted(df["region"].unique()), key="f_region", placeholder="Todas")
        producto = st.multiselect("Producto", list(df["producto"].cat.categories), key="f_producto",
                                  placeholder="Todos")
        segmento = st.multiselect("Segmento", list(df["segmento"].cat.categories), key="f_segmento",
                                  placeholder="Todos")
        canal = st.multiselect("Canal de origen", list(df["canal_origen"].cat.categories), key="f_canal",
                               placeholder="Todos")
        st.button("Restablecer filtros", on_click=restablecer)
    return {"desde": desde, "hasta": hasta, "region": region, "producto": producto,
            "segmento": segmento, "canal_origen": canal}


def main():
    ui.aplicar_estilos()
    df, tamanos = obtener_datos()
    filtros = barra_lateral(df)
    dff = filtrar(df, filtros)

    with st.sidebar:
        ui.html(f'<div class="lat-conteo">Registros en el filtro<br><strong>{num(len(dff))}</strong> '
                f'de {num(len(df))}</div>')
        st.divider()
        ui.html('<div class="lat-nota">Datos sintéticos y anonimizados con fines académicos. '
                'Herramientas de Visualización para la Inteligencia de Negocios, 2026-2.<br><br>'
                'Maria Fernanda Rodriguez - Lorena Sofia Ostos - Laura Valentina Rairan</div>')

    ui.encabezado("Tablero de riesgo de cartera")

    pestanas = st.tabs(["Contexto", "Datos y modelo", "Panorama", "Riesgo de cartera",
                        "Segmentos y territorio", "Cliente y canal digital", "Hallazgos y decisiones"])

    with pestanas[0]:
        contexto.render(df)
    with pestanas[1]:
        datos.render(df, tamanos)

    if dff.empty or not dff["es_credito"].any():
        for p in pestanas[2:]:
            with p:
                st.info("La combinación de filtros no deja obligaciones de crédito. "
                        "Amplíe el periodo o quite algún filtro en la barra lateral.")
        return

    with pestanas[2]:
        panorama.render(dff, df)
    with pestanas[3]:
        riesgo.render(dff)
    with pestanas[4]:
        segmentos.render(dff)
    with pestanas[5]:
        cliente.render(dff)
    with pestanas[6]:
        hallazgos.render(dff)


main()
