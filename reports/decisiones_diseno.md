# Decisiones de diseño visual

## Paleta semántica
El color tiene el mismo significado en todas las pestañas. No se usan rojo ni verde: se evita la lectura de semáforo y el tablero es legible para personas con daltonismo.

| Color | Hex | Significado |
|---|---|---|
| Navy | #14213D | Estructura, encabezados de KPI, promedio móvil, elemento seleccionado |
| Azul acero | #2F5D8A | Estado sano, serie principal, al día, promotores |
| Azul niebla | #8FAECB | Series secundarias |
| Bruma | #C9D5E1 | Contexto, pasivos, saldo total detrás del vencido |
| Ocre | #D19A2A | Atención: sobre el promedio, umbral, mora 31-60, detractores |
| Ocre claro | #E9C987 | Mora temprana 1-30 |
| Ciruela | #6B3E75 | Riesgo severo: mora > 60, prioridad alta |

Ejemplos verificables en pantalla:
- **Panorama:** el anillo usa la escala azul, ocre claro, ocre y ciruela para el avance de la mora.
- **Riesgo, segmentos y ciudades:** las barras de producto, canal, ingreso y ciudad se pintan de ocre solo si superan el promedio.
- **Matrices de calor:** van de claro (bajo riesgo) a ciruela (alto riesgo).

## Distribución: patrón Z
- **Encabezado:** marca arriba a la izquierda y contexto de periodo y usuario a la derecha.
- **KPI:** cuatro tarjetas que se leen de izquierda a derecha, con el ICV primero por ser el indicador de comité.
- **Gráficos:** el principal va abajo a la izquierda (2/3 del ancho) y la composición a la derecha (1/3).
- **Detalle:** al final, a todo el ancho.

Cada gráfico tiene un título que afirma el hallazgo y un subtítulo que explica cómo leerlo.

## Elección de gráficos
| Mensaje | Gráfico | Por qué |
|---|---|---|
| Evolución del ICV | Línea con promedio móvil | Variable temporal continua; el promedio filtra el ruido mensual |
| Parte de un todo (estado) | Anillo | Cuatro categorías ordenadas; la cifra central da la lectura principal |
| Comparar productos o canales | Barras | Comparación precisa de magnitudes entre categorías |
| Concentración en pesos | Treemap | El área muestra la participación en el saldo vencido |
| Score frente a mora y tasa | Columnas con línea en eje doble | Muestra que el riesgo baja y el precio no |
| Cruce de dos dimensiones | Mapa de calor | Detecta combinaciones que un solo corte oculta |
| Territorio | Mapa de burbujas | Tamaño = exposición, color = riesgo |
| Priorización | Dispersión con cuadrantes | Cruza volumen y riesgo para decidir el orden de acción |

## Tipografía
Se usa Montserrat en toda la interfaz y en los gráficos. Los pesos son 800 para el título del tablero, 700 para cifras KPI y títulos de gráfico, y 400 a 500 para el texto. No hay rótulos en mayúsculas sostenidas.
