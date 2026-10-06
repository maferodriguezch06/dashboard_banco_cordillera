# Perfilamiento y transformación de datos

Generado automáticamente por `src/pipeline.py` el 2026-10-06 01:27.

## Resumen
- Registros: 57,000 y 17 variables.
- Periodo: 2024-01-01 a 2026-09-30.
- Clientes únicos: 26,181 (hasta 8 registros por cliente).
- Unidad de observación: una obligación o producto de un cliente en una fecha de corte.

## Calidad
- Duplicados exactos: 0.
- Mismo cliente, fecha y producto: 13 (se conservan y se marcan).
- Incoherencias entre días de mora y estado: 0.
- Cuentas de ahorro con días de mora: 1,969 de 14,406 (se aíslan de los KPI de cartera).
- Score fuera de rango: 0. NPS fuera de rango: 0. Saldos no positivos: 0.
- Saldos atípicos marcados (IQR por producto): 2,407.

## Variables
| Variable | Tipo | Faltantes | % | Únicos |
|---|---|---|---|---|
| id_cliente_anonimo | str | 0 | 0.0 % | 26181 |
| fecha_corte | str | 0 | 0.0 % | 1004 |
| ciudad | str | 0 | 0.0 % | 12 |
| departamento | str | 0 | 0.0 % | 12 |
| region | str | 0 | 0.0 % | 7 |
| producto | str | 0 | 0.0 % | 5 |
| segmento | str | 0 | 0.0 % | 4 |
| canal_origen | str | 0 | 0.0 % | 5 |
| saldo_o_monto_cop | int64 | 0 | 0.0 % | 56905 |
| score_riesgo | int64 | 0 | 0.0 % | 499 |
| dias_mora | int64 | 0 | 0.0 % | 121 |
| estado_obligacion | str | 0 | 0.0 % | 4 |
| tasa_efectiva_anual_pct | float64 | 0 | 0.0 % | 3176 |
| ingreso_mensual_rango | str | 0 | 0.0 % | 4 |
| transacciones_digitales_30d | int64 | 0 | 0.0 % | 33 |
| reclamos_90d | int64 | 0 | 0.0 % | 5 |
| nps_0a10 | float64 | 855 | 1.5 % | 11 |

## Decisiones
1. Lectura con `utf-8-sig` para eliminar el BOM del encabezado.
2. NPS faltante (1.5 %) no se imputa; se excluye solo del cálculo de NPS.
3. Cuenta de ahorros sale de los indicadores de riesgo de cartera: no es crédito.
4. No se elimina ningún registro; las alertas de calidad quedan como columnas.
5. Se crea un modelo estrella: `fact_obligacion` y seis dimensiones.
