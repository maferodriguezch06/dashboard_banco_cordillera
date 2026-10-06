"""Componentes visuales reutilizables (HTML + CSS propios)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.config import cargar_config, paleta

P = paleta()
CSS = Path(__file__).parent / "assets" / "styles.css"

ICONOS = {
    "riesgo": '<path d="M4 17l5-5 4 4 7-8" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><path d="M15 8h5v5" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>',
    "dinero": '<text x="12" y="17" text-anchor="middle" font-size="15" font-weight="700" fill="#fff" font-family="Montserrat">$</text>',
    "score": '<rect x="5" y="12" width="3" height="7" rx="1" fill="#fff"/><rect x="10.5" y="8" width="3" height="11" rx="1" fill="#fff"/><rect x="16" y="4" width="3" height="15" rx="1" fill="#fff"/>',
    "cliente": '<circle cx="12" cy="8.5" r="3.6" fill="#fff"/><path d="M5 19c1-3.6 3.8-5.4 7-5.4s6 1.8 7 5.4" fill="#fff"/>',
}


def aplicar_estilos() -> None:
    st.markdown(f"<style>{CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def encabezado(seccion: str) -> None:
    cfg = cargar_config()["proyecto"]
    # Separa los nombres por " - " y los muestra uno por línea
    nombres = [n.strip() for n in cfg.get("nombre_estudio", "").split(" - ") if n.strip()]
    equipo = "".join(f"<span>{n}</span>" for n in nombres)
    st.markdown(
        f"""
        <div class="encabezado">
          <div class="marca">
            <div class="logo">C</div>
            <div class="marca-texto"><b>{cfg['nombre']}</b><span>{cfg['subtitulo']}</span></div>
          </div>
          <div class="equipo">
            <small>Equipo</small>
            <div class="equipo-nombres">{equipo}</div>
          </div>
          <div class="usuario">
            <span class="chip-periodo">Datos de {cfg['periodo']}</span>
            <div class="avatar">GR</div>
            <div><b>Gerencia de Riesgo</b><br>Banca minorista</div>
          </div>
        </div>
        <div class="miga"><div class="miga-titulo">{seccion}</div><span>Inicio &rsaquo; Riesgo y banca minorista</span></div>
        """,
        unsafe_allow_html=True,
    )


def kpi(titulo: str, valor: str, icono: str, color_icono: str, delta: str = "",
        delta_favorable: bool | None = None, nota: str = "", alerta: bool = False) -> None:
    clase_delta = "" if delta_favorable is None else ("d-bien" if delta_favorable else "d-mal")
    pie = f'<span class="{clase_delta}">{delta}</span> {nota}' if delta else nota
    st.markdown(
        f"""
        <div class="kpi{' alerta' if alerta else ''}">
          <div class="kpi-cab">{titulo}</div>
          <div class="kpi-cuerpo">
            <div class="kpi-valor">{valor}</div>
            <div class="kpi-icono" style="background:{color_icono}">
              <svg width="24" height="24" viewBox="0 0 24 24">{ICONOS[icono]}</svg>
            </div>
          </div>
          <div class="kpi-pie">{pie}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mini(etiqueta: str, valor: str) -> None:
    st.markdown(f'<div class="mini"><span>{etiqueta}</span><b>{valor}</b></div>', unsafe_allow_html=True)


def seccion(titulo: str, texto: str = "") -> None:
    html = f'<div class="titulo-seccion">{titulo}</div>'
    if texto:
        html += f'<div class="texto-seccion">{texto}</div>'
    st.markdown(html, unsafe_allow_html=True)


def bloque(titulo: str, cuerpo_html: str, oscuro: bool = False) -> None:
    st.markdown(f'<div class="bloque{" oscuro" if oscuro else ""}"><h3>{titulo}</h3>{cuerpo_html}</div>',
                unsafe_allow_html=True)


def html(contenido: str) -> None:
    st.markdown(contenido, unsafe_allow_html=True)


def grafico(fig, key: str | None = None, **kwargs):
    """Envuelve st.plotly_chart con la configuración común del tablero."""
    fig.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
    config = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
              "locale": "es", "topojsonURL": "app/static/topojson/"}
    return st.plotly_chart(fig, theme=None, config=config, key=key, **kwargs)


def tarjeta(clave: str):
    """Contenedor blanco con borde. La clave genera la clase CSS st-key-card_<clave>."""
    return st.container(border=True, key=f"card_{clave}")
