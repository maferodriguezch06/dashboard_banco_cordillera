# Banco Cordillera: tablero de riesgo y banca minorista

Proyecto final 2026-2 de Herramientas de Visualización para la Inteligencia de Negocios (grupo 4, contexto banco de servicios financieros minoristas).
El tablero está hecho en **Streamlit** y es, a la vez, la herramienta de análisis y la presentación de la sustentación: sus 7 pestañas siguen el orden de la exposición.

## Cómo ejecutarlo en Visual Studio Code

1. Abra la carpeta `banco-minorista-bi` con *Archivo > Abrir carpeta*.
2. Abra una terminal (*Terminal > Nueva terminal*) y cree un entorno virtual:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```
3. Instale las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. (Opcional) Reconstruya los datos procesados y los reportes:
   ```bash
   python scripts/construir_datos.py
   ```
   Si no lo hace, la app los genera sola la primera vez.
5. Ejecute el tablero **desde la raíz del proyecto**:
   ```bash
   streamlit run app/main.py
   ```
   También puede usar *Ejecutar y depurar > Streamlit: dashboard* (configurado en `.vscode/launch.json`).

Requiere Python 3.10 o superior. El mapa usa archivos locales (`app/static/topojson/`), así que funciona sin internet. Solo la tipografía Montserrat se descarga de Google Fonts; sin conexión se usa una fuente de respaldo.

## Estructura

```
banco-minorista-bi/
├── app/                      Aplicación Streamlit
│   ├── main.py               Punto de entrada: filtros laterales y pestañas
│   ├── ui.py                 Componentes visuales (encabezado, tarjetas KPI, bloques)
│   ├── assets/styles.css     Estilos: Montserrat, barra lateral navy, tarjetas
│   ├── static/topojson/      Mapa base de Sudamérica para uso sin internet
│   └── views/                Una vista por pestaña
│       ├── contexto.py       1. Problema, audiencia, preguntas, KPI y guía de lectura
│       ├── datos.py          2. Origen, perfilamiento, transformación y modelo
│       ├── panorama.py       3. Vista inicial: KPI, evolución temporal, composición
│       ├── riesgo.py         4. Pregunta 1: concentración de riesgo y score
│       ├── segmentos.py      5. Pregunta 2: segmentos, canales y territorio
│       ├── cliente.py        6. Pregunta 3: experiencia y uso digital
│       └── hallazgos.py      7. Hallazgos, matriz de priorización y plan
├── src/                      Lógica reutilizable (sin Streamlit)
│   ├── pipeline.py           Perfilamiento, limpieza, derivadas, modelo estrella
│   ├── data.py               Carga del modelo, unión de tablas y filtros
│   ├── metrics.py            Definición única de todos los KPI
│   ├── charts.py             Tema Plotly y paleta semántica
│   ├── formato.py            Números en formato colombiano
│   └── config.py             Lectura de config/settings.yaml
├── config/settings.yaml      Rutas, umbrales, bandas de score y paleta
├── data/
│   ├── raw/                  04_banco_minorista.csv (original, sin modificar)
│   └── processed/
│       ├── banco_minorista_procesado.csv   Versión procesada (tabla plana)
│       └── modelo/           fact_obligacion + 6 dimensiones (esquema estrella)
├── notebooks/01_perfilamiento_datos.ipynb  Perfilamiento paso a paso
├── reports/
│   ├── perfilamiento_datos.md   Reporte automático de calidad
│   ├── diccionario_datos.csv    Naturaleza y función de cada variable
│   ├── perfil_datos.json        Perfil usado por la pestaña Datos
│   ├── guion_sustentacion.md    Guion de la exposición
│   └── decisiones_diseno.md     Justificación de color, distribución y gráficos
├── scripts/construir_datos.py   Ejecuta el pipeline completo
├── .streamlit/config.toml       Tema base y servidor
├── .vscode/                     Configuración de ejecución
└── requirements.txt
```

No hay carpeta `models/` porque el proyecto no entrena modelos predictivos. El modelo **de datos** (esquema estrella) está en `data/processed/modelo/`.

## Decisiones de datos

| Tema | Decisión |
|---|---|
| Codificación | El CSV trae BOM; se lee con `utf-8-sig`. |
| Unidad de observación | Obligación de un cliente en una fecha de corte (el cliente se repite hasta 8 veces). |
| NPS faltante (855, 1,5 %) | No se imputa; se excluye solo del cálculo de NPS. |
| Cuenta de ahorros con mora (1.969) | Se interpreta como sobregiro; la cuenta de ahorros sale de los KPI de cartera. |
| Duplicados | 0 exactos; 13 de mismo cliente, fecha y producto, conservados y marcados. |
| Atípicos (2.407) | Se conservan y se marcan: son saldos de vivienda reales. |
| Registros eliminados | Ninguno. |

## KPI

| KPI | Fórmula |
|---|---|
| ICV 30+ por saldo | Σ saldo con mora > 30 días / Σ saldo de crédito |
| ICV 30+ por número | Obligaciones con mora > 30 / obligaciones de crédito |
| Saldo vencido 30+ | Σ saldo con mora > 30 días |
| Score promedio | Promedio de score en productos de crédito |
| NPS | % promotores (9-10) − % detractores (0-6), sobre quienes respondieron |
| Reclamos por cada 100 | Σ reclamos 90 días / registros × 100 |

## Interactividad

- **Filtros globales** en la barra lateral: periodo, región, producto, segmento y canal. Incluye un botón para restablecerlos.
- **Selección cruzada:** clic en un producto en *Riesgo de cartera* filtra los gráficos de score y estados.
- **Controles por pestaña:** indicador y granularidad del gráfico temporal, medida del ICV, dimensiones de la matriz, tamaño de burbuja del mapa, volumen mínimo de la tabla y cruce de la matriz de prioridad.
- **Tooltips** en español con formato de pesos y porcentaje en todos los gráficos.

Datos sintéticos y anonimizados con fines académicos.
Para acceder al streamlit: https://dashboardbancocordillera-adqtet7ndqk7mckn88ccwu.streamlit.app/
