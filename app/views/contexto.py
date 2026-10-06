"""Pestaña 1: contexto del problema, audiencia, preguntas, KPI y guía de lectura."""
from __future__ import annotations

import streamlit as st

from app import ui
from src import metrics as m
from src.config import paleta
from src.formato import cop, num, pct

P = paleta()


def render(df):
    c1, c2 = st.columns([1.55, 1], gap="medium")
    with c1:
        ui.bloque(
            "La organización y su necesidad",
            """
            <p><b>Banco Cordillera</b> es un banco simulado de servicios financieros minoristas con presencia
            en 12 ciudades y 7 regiones de Colombia. Ofrece tarjeta de crédito, crédito de libre inversión,
            de vehículo, de vivienda y cuenta de ahorros, y origina sus productos por app, web, call center,
            oficina y alianzas comerciales.</p>
            <p>La cartera vencida se mantiene cerca del 10 % del saldo desde 2024 y la gerencia no tiene una
            vista única que muestre <b>dónde se concentra el riesgo</b>, si el score lo está anticipando y si la
            experiencia del cliente se relaciona con el deterioro. Este tablero responde a esa necesidad.</p>
            """,
        )
    with c2:
        ui.bloque(
            "Audiencia y uso",
            f"""
            <p><b>Audiencia principal:</b> Gerencia de Riesgo y Gerencia de Banca Minorista.</p>
            <p><b>Uso:</b> comité mensual de riesgo, para priorizar cobranza, ajustar políticas de
            originación y precio, y orientar acciones de experiencia.</p>
            <p><b>Base analizada:</b> {num(len(df))} registros de obligaciones, {num(df['id_cliente_anonimo'].nunique())}
            clientes, 33 meses de cortes.</p>
            """,
            oscuro=True,
        )

    ui.seccion("Tres preguntas guían el recorrido",
               "Cada pregunta tiene su pestaña, sus KPI y su decisión asociada. El orden de las pestañas es el "
               "orden de la exposición.")
    preguntas = [
        ("1", "¿Dónde se concentra el riesgo de la cartera y qué tan bien lo anticipa el score?",
         "Pestaña Riesgo de cartera. KPI: ICV 30+ por saldo, saldo vencido, score promedio."),
        ("2", "¿Qué segmentos, canales y territorios requieren gestión prioritaria?",
         "Pestaña Segmentos y territorio. KPI: ICV por combinación, participación en el saldo vencido."),
        ("3", "¿La experiencia del cliente y el uso digital se relacionan con el riesgo?",
         "Pestaña Cliente y canal digital. KPI: NPS, reclamos por cada 100, transacciones digitales."),
    ]
    cols = st.columns(3, gap="medium")
    for col, (n, q, d) in zip(cols, preguntas):
        with col:
            ui.html(f'<div class="pregunta"><div class="num">{n}</div><h4>{q}</h4><p>{d}</p></div>')

    ui.seccion("Indicadores clave y cómo se calculan",
               "Los KPI de riesgo excluyen la cuenta de ahorros porque no es cartera de crédito.")
    filas = [
        ("ICV 30+ por saldo", "<code>Σ saldo con mora &gt; 30 días / Σ saldo de crédito</code>",
         pct(m.icv_saldo(df)), "Mide cuánto del dinero prestado está vencido. Es el indicador de comité."),
        ("Saldo vencido 30+", "<code>Σ saldo con mora &gt; 30 días</code>", cop(m.saldo_vencido(df)),
         "Dimensiona en pesos la exposición que debe gestionar cobranza."),
        ("Score promedio", "<code>promedio(score_riesgo)</code> en crédito", num(m.score_promedio(df), 0),
         "Calidad crediticia de la cartera; valida si el score separa buenos y malos pagadores."),
        ("NPS", "<code>% promotores (9-10) − % detractores (0-6)</code>", num(m.nps(df), 1),
         "Lealtad del cliente; se calcula solo sobre quienes respondieron la encuesta."),
        ("Reclamos por cada 100", "<code>Σ reclamos 90 días / registros × 100</code>",
         num(m.reclamos_por_100(df), 1), "Fricción en el servicio; complementa al NPS."),
    ]
    cuerpo = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in filas)
    ui.html(f'<table class="tabla-kpi"><tr><th>Indicador</th><th>Fórmula</th><th>Valor total</th>'
            f'<th>Para qué sirve</th></tr>{cuerpo}</table>')

    ui.seccion("Decisiones que habilita el tablero")
    d1, d2, d3 = st.columns(3, gap="medium")
    with d1:
        ui.bloque("Originación y precio", "<p>Ajustar puntos de corte del score y pasar a una tasa "
                  "diferenciada por nivel de riesgo.</p>")
    with d2:
        ui.bloque("Cobranza", "<p>Priorizar regiones, productos y canales con mayor ICV y mayor saldo "
                  "vencido en pesos.</p>")
    with d3:
        ui.bloque("Experiencia", "<p>Definir un plan para mover detractores a pasivos, sabiendo si la "
                  "insatisfacción está o no ligada a la mora.</p>")

   