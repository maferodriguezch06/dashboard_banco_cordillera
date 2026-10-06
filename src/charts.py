"""Tema visual de Plotly y constructores de gráficos reutilizables.

Regla de color del proyecto: ninguna línea ni serie usa rojo o verde.
- Azul acero / navy: estado sano, serie principal, estructura.
- Ocre dorado: atención, umbral, valor por encima del promedio.
- Ciruela: riesgo severo.
- Bruma: contexto o valores neutros.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from src.config import paleta

P = paleta()
FUENTE = "Montserrat, 'Segoe UI', Arial, sans-serif"

COLOR_ESTADO = {
    "Al día": P["acero"], "Mora 1-30": P["oro_claro"],
    "Mora 31-60": P["oro"], "Mora >60": P["ciruela"],
}
COLOR_NPS = {"Promotor": P["acero"], "Pasivo": P["bruma"], "Detractor": P["oro"]}
CATEGORICA = [P["tinta"], P["acero"], P["niebla"], P["oro"], P["ciruela"], "#A3672B", "#9AA9BA"]
# Escala secuencial de riesgo: claro (bajo) -> acero -> navy -> ciruela (alto)
ESCALA_RIESGO = [[0.0, "#EEF2F7"], [0.35, "#A9C0D8"], [0.6, P["acero"]],
                 [0.82, "#3A3F6E"], [1.0, P["ciruela"]]]

pio.templates["cordillera"] = go.layout.Template(
    layout=dict(
        font=dict(family=FUENTE, size=12, color=P["tinta"]),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        colorway=CATEGORICA,
        separators=",.",
        margin=dict(l=12, r=16, t=70, b=40),
        title=dict(x=0.01, xanchor="left", font=dict(size=15, color=P["tinta"], family=FUENTE)),
        xaxis=dict(automargin=True, showgrid=False, linecolor=P["borde"], ticks="", zeroline=False,
                   title=dict(font=dict(size=11, color=P["texto_suave"]))),
        yaxis=dict(automargin=True, gridcolor="#E9EEF3", zeroline=False, linecolor=P["borde"],
                   title=dict(font=dict(size=11, color=P["texto_suave"]))),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)", title_text=""),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=P["tinta"],
                        font=dict(family=FUENTE, size=12, color=P["tinta"])),
        bargap=0.28,
    )
)
pio.templates.default = "cordillera"


def titular(fig: go.Figure, titulo: str, subtitulo: str = "", alto: int = 380) -> go.Figure:
    """Título analítico (afirma el hallazgo) y subtítulo descriptivo."""
    texto = f"<b>{titulo}</b>"
    if subtitulo:
        texto += f"<br><span style='font-size:11.5px;color:{P['texto_suave']}'>{subtitulo}</span>"
    fig.update_layout(title_text=texto, height=alto)
    return fig


def linea_referencia(fig: go.Figure, valor: float, texto: str, eje: str = "y") -> go.Figure:
    fig.add_hline(y=valor, line=dict(color=P["oro"], width=1.5, dash="dot"),
                  annotation_text=texto, annotation_position="top right",
                  annotation_font=dict(color=P["oro"], size=11), yref=eje)
    return fig


def colores_destacados(valores, referencia: float, alto=None, normal=None, seleccion=None, etiquetas=None):
    """Ocre si el valor supera la referencia; acero en otro caso. Navy si está seleccionado."""
    alto = alto or P["oro"]
    normal = normal or P["acero"]
    out = []
    for i, v in enumerate(valores):
        if seleccion is not None and etiquetas is not None and etiquetas[i] == seleccion:
            out.append(P["tinta"])
        else:
            out.append(alto if v > referencia else normal)
    return out
