"""Pipeline de preparación de datos.

Flujo: CSV crudo -> perfilamiento -> limpieza y tipado -> variables derivadas
-> modelo estrella (1 hecho + 6 dimensiones) -> archivos procesados + reportes.

Se ejecuta con:  python scripts/construir_datos.py
La app lo ejecuta automáticamente si no encuentra los archivos procesados.
"""
from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd

from src.config import cargar_config, ruta

# ----------------------------------------------------------------------------
# Tablas auxiliares (información externa al dataset, documentada como derivada)
# ----------------------------------------------------------------------------
COORDENADAS = {
    "Bogotá D.C.": (4.7110, -74.0721), "Medellín": (6.2442, -75.5812),
    "Cali": (3.4516, -76.5320), "Barranquilla": (10.9639, -74.7964),
    "Bucaramanga": (7.1193, -73.1227), "Cartagena": (10.3910, -75.4794),
    "Santa Marta": (11.2408, -74.1990), "Pereira": (4.8133, -75.6961),
    "Villavicencio": (4.1420, -73.6266), "Cúcuta": (7.8939, -72.5078),
    "Ibagué": (4.4389, -75.2322), "Manizales": (5.0703, -75.5138),
}

PRODUCTOS = {
    # producto: (familia, naturaleza, es_credito, orden)
    "Tarjeta de crédito": ("Rotativo", "Activo", True, 1),
    "Crédito libre inversión": ("Consumo", "Activo", True, 2),
    "Crédito vehículo": ("Vehículo", "Activo", True, 3),
    "Crédito vivienda": ("Hipotecario", "Activo", True, 4),
    "Cuenta de ahorros": ("Captación", "Pasivo", False, 5),
}

CANALES = {
    # canal: (tipo, orden)
    "App": ("Digital", 1), "Web": ("Digital", 2), "Call center": ("Remoto asistido", 3),
    "Oficina": ("Presencial", 4), "Alianza": ("Tercero", 5),
}

ORDEN_INGRESO = ["<2 SMMLV", "2-4 SMMLV", "4-8 SMMLV", ">8 SMMLV"]
ORDEN_ESTADO = ["Al día", "Mora 1-30", "Mora 31-60", "Mora >60"]
ORDEN_SEGMENTO = ["Joven", "Masivo", "Microempresario", "Preferente"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

COLUMNAS_ESPERADAS = [
    "id_cliente_anonimo", "fecha_corte", "ciudad", "departamento", "region", "producto",
    "segmento", "canal_origen", "saldo_o_monto_cop", "score_riesgo", "dias_mora",
    "estado_obligacion", "tasa_efectiva_anual_pct", "ingreso_mensual_rango",
    "transacciones_digitales_30d", "reclamos_90d", "nps_0a10",
]


# ----------------------------------------------------------------------------
# 1. Lectura
# ----------------------------------------------------------------------------
def leer_crudo() -> pd.DataFrame:
    # utf-8-sig elimina el BOM que trae el archivo en la primera columna
    df = pd.read_csv(ruta("raw"), encoding="utf-8-sig")
    faltan = set(COLUMNAS_ESPERADAS) - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en el archivo crudo: {sorted(faltan)}")
    return df


# ----------------------------------------------------------------------------
# 2. Perfilamiento
# ----------------------------------------------------------------------------
def perfilar(df: pd.DataFrame) -> dict:
    cfg = cargar_config()["reglas_negocio"]
    perfil: dict = {"filas": int(len(df)), "columnas": int(df.shape[1])}

    variables = []
    for c in df.columns:
        s = df[c]
        numerica = pd.api.types.is_numeric_dtype(s)
        variables.append({
            "variable": c,
            "tipo_origen": str(s.dtype),
            "faltantes": int(s.isna().sum()),
            "pct_faltantes": round(float(s.isna().mean() * 100), 2),
            "valores_unicos": int(s.nunique()),
            "minimo": float(s.min()) if numerica else None,
            "maximo": float(s.max()) if numerica else None,
        })
    perfil["variables"] = variables

    perfil["duplicados_exactos"] = int(df.duplicated().sum())
    perfil["duplicados_cliente_fecha_producto"] = int(
        df.duplicated(["id_cliente_anonimo", "fecha_corte", "producto"]).sum()
    )
    perfil["clientes_unicos"] = int(df["id_cliente_anonimo"].nunique())
    perfil["registros_por_cliente_max"] = int(df.groupby("id_cliente_anonimo").size().max())

    # Coherencia entre dias_mora y estado_obligacion
    esperado = pd.cut(df["dias_mora"], [-1, 0, 30, 60, 10_000], labels=ORDEN_ESTADO).astype(str)
    perfil["incoherencias_estado_vs_dias"] = int((esperado != df["estado_obligacion"]).sum())

    no_credito = df["producto"].isin(cfg["productos_no_credito"])
    perfil["ahorros_con_dias_mora"] = int((no_credito & (df["dias_mora"] > 0)).sum())
    perfil["ahorros_total"] = int(no_credito.sum())

    perfil["fecha_min"] = str(df["fecha_corte"].min())
    perfil["fecha_max"] = str(df["fecha_corte"].max())
    perfil["score_fuera_rango"] = int(((df["score_riesgo"] < 300) | (df["score_riesgo"] > 900)).sum())
    perfil["nps_fuera_rango"] = int(((df["nps_0a10"] < 0) | (df["nps_0a10"] > 10)).sum())
    perfil["saldos_no_positivos"] = int((df["saldo_o_monto_cop"] <= 0).sum())
    return perfil


# ----------------------------------------------------------------------------
# 3. Limpieza, tipado y variables derivadas
# ----------------------------------------------------------------------------
def _bandas(serie: pd.Series, bandas: list[dict]) -> pd.Series:
    cortes = [b["min"] for b in bandas] + [bandas[-1]["max"]]
    etiquetas = [b["etiqueta"] for b in bandas]
    return pd.cut(serie, bins=cortes, labels=etiquetas, right=False)


def limpiar_y_derivar(df: pd.DataFrame) -> pd.DataFrame:
    cfg = cargar_config()["reglas_negocio"]
    d = df.copy()

    # Texto: quitar espacios sobrantes
    for c in ["ciudad", "departamento", "region", "producto", "segmento", "canal_origen",
              "estado_obligacion", "ingreso_mensual_rango", "id_cliente_anonimo"]:
        d[c] = d[c].astype(str).str.strip()

    # Tipado
    d["fecha_corte"] = pd.to_datetime(d["fecha_corte"], format="%Y-%m-%d")
    for c in ["saldo_o_monto_cop", "score_riesgo", "dias_mora",
              "transacciones_digitales_30d", "reclamos_90d"]:
        d[c] = pd.to_numeric(d[c], downcast="integer")
    d["tasa_efectiva_anual_pct"] = d["tasa_efectiva_anual_pct"].astype(float)

    # Llave única de registro (el id de cliente se repite en varios cortes)
    d.insert(0, "id_registro", np.arange(1, len(d) + 1))

    # Banderas de riesgo
    d["es_credito"] = ~d["producto"].isin(cfg["productos_no_credito"])
    d["en_mora"] = d["dias_mora"] > 0
    d["vencida_30"] = d["dias_mora"] > cfg["dias_vencida"]
    d["severa_60"] = d["dias_mora"] > cfg["dias_severa"]
    d["saldo_vencido_30"] = np.where(d["vencida_30"], d["saldo_o_monto_cop"], 0)
    d["saldo_severo_60"] = np.where(d["severa_60"], d["saldo_o_monto_cop"], 0)

    # Inconsistencia: una cuenta de ahorros no genera mora. Se interpreta como sobregiro
    # y se aísla de los indicadores de cartera (no se borra el registro).
    d["alerta_ahorro_con_mora"] = (~d["es_credito"]) & d["en_mora"]

    # Bandas analíticas
    d["banda_score"] = _bandas(d["score_riesgo"], cfg["bandas_score"])
    d["banda_digital"] = _bandas(d["transacciones_digitales_30d"], cfg["bandas_digital"])

    # NPS: no se imputa (imputar una opinión sesga el indicador). Se clasifica.
    d["nps_respondio"] = d["nps_0a10"].notna()
    d["categoria_nps"] = np.select(
        [d["nps_0a10"] >= 9, d["nps_0a10"] >= 7, d["nps_0a10"] >= 0],
        ["Promotor", "Pasivo", "Detractor"], default="Sin respuesta",
    )

    # Atípicos de saldo por producto (regla IQR). Se marcan, no se eliminan:
    # en vivienda los saldos altos son reales y concentran el riesgo en pesos.
    q1 = d.groupby("producto")["saldo_o_monto_cop"].transform(lambda s: s.quantile(0.25))
    q3 = d.groupby("producto")["saldo_o_monto_cop"].transform(lambda s: s.quantile(0.75))
    d["saldo_atipico"] = d["saldo_o_monto_cop"] > q3 + 1.5 * (q3 - q1)

    # Posibles duplicados de negocio (mismo cliente, fecha y producto): se conservan
    # porque pueden ser dos obligaciones distintas del mismo tipo; quedan marcados.
    d["posible_duplicado"] = d.duplicated(["id_cliente_anonimo", "fecha_corte", "producto"], keep=False)

    # Tiempo
    d["periodo"] = d["fecha_corte"].dt.to_period("M").astype(str)
    d["trimestre"] = d["fecha_corte"].dt.year.astype(str) + "-T" + d["fecha_corte"].dt.quarter.astype(str)
    return d


# ----------------------------------------------------------------------------
# 4. Modelo estrella
# ----------------------------------------------------------------------------
def construir_modelo(d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    # dim_fecha: calendario completo del periodo
    cal = pd.DataFrame({"fecha": pd.date_range(d["fecha_corte"].min().replace(day=1),
                                                d["fecha_corte"].max(), freq="D")})
    cal["fecha_key"] = cal["fecha"].dt.strftime("%Y%m%d").astype(int)
    cal["anio"] = cal["fecha"].dt.year
    cal["trimestre"] = cal["anio"].astype(str) + "-T" + cal["fecha"].dt.quarter.astype(str)
    cal["mes"] = cal["fecha"].dt.month
    cal["periodo"] = cal["fecha"].dt.to_period("M").astype(str)
    cal["etiqueta_mes"] = cal["mes"].map(lambda m: MESES[m - 1]) + " " + cal["anio"].astype(str)
    dim_fecha = cal[["fecha_key", "fecha", "anio", "trimestre", "mes", "periodo", "etiqueta_mes"]]

    geo = d[["ciudad", "departamento", "region"]].drop_duplicates().sort_values(["region", "ciudad"])
    geo = geo.reset_index(drop=True)
    geo.insert(0, "geo_key", np.arange(1, len(geo) + 1))
    geo["lat"] = geo["ciudad"].map(lambda c: COORDENADAS.get(c, (np.nan, np.nan))[0])
    geo["lon"] = geo["ciudad"].map(lambda c: COORDENADAS.get(c, (np.nan, np.nan))[1])

    prod = pd.DataFrame([
        {"producto": p, "familia": v[0], "naturaleza": v[1], "es_credito": v[2], "orden": v[3]}
        for p, v in PRODUCTOS.items()
    ])
    prod.insert(0, "producto_key", np.arange(1, len(prod) + 1))

    seg = pd.DataFrame({"segmento": ORDEN_SEGMENTO, "orden": range(1, len(ORDEN_SEGMENTO) + 1)})
    seg.insert(0, "segmento_key", np.arange(1, len(seg) + 1))

    can = pd.DataFrame([{"canal_origen": c, "tipo_canal": v[0], "orden": v[1]} for c, v in CANALES.items()])
    can.insert(0, "canal_key", np.arange(1, len(can) + 1))

    ing = pd.DataFrame({"ingreso_mensual_rango": ORDEN_INGRESO, "orden": range(1, len(ORDEN_INGRESO) + 1)})
    ing.insert(0, "ingreso_key", np.arange(1, len(ing) + 1))

    f = d.copy()
    f["fecha_key"] = f["fecha_corte"].dt.strftime("%Y%m%d").astype(int)
    f = (f.merge(geo[["geo_key", "ciudad"]], on="ciudad", how="left")
          .merge(prod[["producto_key", "producto"]], on="producto", how="left")
          .merge(seg[["segmento_key", "segmento"]], on="segmento", how="left")
          .merge(can[["canal_key", "canal_origen"]], on="canal_origen", how="left")
          .merge(ing[["ingreso_key", "ingreso_mensual_rango"]], on="ingreso_mensual_rango", how="left"))

    llaves = ["geo_key", "producto_key", "segmento_key", "canal_key", "ingreso_key"]
    if f[llaves].isna().any().any():
        raise ValueError("Hay registros sin correspondencia en alguna dimensión.")

    hechos = f[[
        "id_registro", "id_cliente_anonimo", "fecha_key", *llaves,
        "saldo_o_monto_cop", "score_riesgo", "dias_mora", "estado_obligacion",
        "tasa_efectiva_anual_pct", "transacciones_digitales_30d", "reclamos_90d", "nps_0a10",
        "vencida_30", "severa_60", "en_mora", "saldo_vencido_30", "saldo_severo_60",
        "alerta_ahorro_con_mora", "banda_score", "banda_digital", "nps_respondio",
        "categoria_nps", "saldo_atipico", "posible_duplicado",
    ]].sort_values("id_registro")

    return {
        "fact_obligacion": hechos, "dim_fecha": dim_fecha, "dim_geografia": geo,
        "dim_producto": prod, "dim_segmento": seg, "dim_canal": can, "dim_ingreso": ing,
    }


# ----------------------------------------------------------------------------
# 5. Reportes
# ----------------------------------------------------------------------------
DESCRIPCIONES = {
    "id_registro": ("Derivada", "Llave", "Consecutivo único por fila, creado en el pipeline"),
    "id_cliente_anonimo": ("Categórica", "Identificador", "Cliente anonimizado; se repite en varios cortes"),
    "fecha_corte": ("Temporal", "Dimensión / filtro", "Fecha de corte de la obligación"),
    "ciudad": ("Geográfica", "Dimensión / filtro", "Ciudad de la obligación"),
    "departamento": ("Geográfica", "Dimensión", "Departamento"),
    "region": ("Geográfica", "Dimensión / filtro", "Región comercial"),
    "producto": ("Categórica", "Dimensión / filtro", "Producto financiero"),
    "segmento": ("Categórica", "Dimensión / filtro", "Segmento comercial del cliente"),
    "canal_origen": ("Categórica", "Dimensión / filtro", "Canal por el que se originó el producto"),
    "saldo_o_monto_cop": ("Numérica continua", "Métrica", "Saldo de la obligación o monto de la cuenta (COP)"),
    "score_riesgo": ("Numérica discreta", "Métrica / banda", "Puntaje de riesgo 350 a 900; mayor es mejor"),
    "dias_mora": ("Numérica discreta", "Métrica", "Días de atraso 0 a 120"),
    "estado_obligacion": ("Categórica ordinal", "Dimensión", "Al día, Mora 1-30, 31-60, >60"),
    "tasa_efectiva_anual_pct": ("Numérica continua", "Métrica", "Tasa efectiva anual (%)"),
    "ingreso_mensual_rango": ("Categórica ordinal", "Dimensión", "Rango de ingreso en salarios mínimos"),
    "transacciones_digitales_30d": ("Numérica discreta", "Métrica / banda", "Transacciones digitales últimos 30 días"),
    "reclamos_90d": ("Numérica discreta", "Métrica", "Reclamos radicados en 90 días"),
    "nps_0a10": ("Numérica ordinal", "Métrica", "Recomendación 0 a 10; tiene faltantes"),
    "vencida_30": ("Derivada", "Bandera KPI", "dias_mora > 30"),
    "severa_60": ("Derivada", "Bandera KPI", "dias_mora > 60"),
    "saldo_vencido_30": ("Derivada", "Métrica KPI", "Saldo si la obligación está vencida a más de 30 días"),
    "banda_score": ("Derivada", "Dimensión", "Score agrupado en 5 bandas"),
    "banda_digital": ("Derivada", "Dimensión", "Transacciones digitales agrupadas en 4 bandas"),
    "categoria_nps": ("Derivada", "Dimensión", "Promotor 9-10, Pasivo 7-8, Detractor 0-6, Sin respuesta"),
    "alerta_ahorro_con_mora": ("Derivada", "Calidad de datos", "Cuenta de ahorros con días de mora (sobregiro)"),
    "saldo_atipico": ("Derivada", "Calidad de datos", "Saldo sobre Q3 + 1,5·IQR dentro de su producto"),
    "posible_duplicado": ("Derivada", "Calidad de datos", "Mismo cliente, fecha y producto"),
}


def escribir_reportes(perfil: dict, d: pd.DataFrame) -> None:
    carpeta = ruta("reportes")
    carpeta.mkdir(parents=True, exist_ok=True)

    with open(carpeta / "perfil_datos.json", "w", encoding="utf-8") as f:
        json.dump(perfil, f, ensure_ascii=False, indent=2)

    dic = pd.DataFrame([
        {"variable": k, "naturaleza": v[0], "funcion_analitica": v[1], "descripcion": v[2]}
        for k, v in DESCRIPCIONES.items()
    ])
    dic.to_csv(carpeta / "diccionario_datos.csv", index=False, encoding="utf-8-sig")

    vars_md = "\n".join(
        f"| {v['variable']} | {v['tipo_origen']} | {v['faltantes']} | {v['pct_faltantes']} % | {v['valores_unicos']} |"
        for v in perfil["variables"]
    )
    md = f"""# Perfilamiento y transformación de datos

Generado automáticamente por `src/pipeline.py` el {datetime.now():%Y-%m-%d %H:%M}.

## Resumen
- Registros: {perfil['filas']:,} y {perfil['columnas']} variables.
- Periodo: {perfil['fecha_min']} a {perfil['fecha_max']}.
- Clientes únicos: {perfil['clientes_unicos']:,} (hasta {perfil['registros_por_cliente_max']} registros por cliente).
- Unidad de observación: una obligación o producto de un cliente en una fecha de corte.

## Calidad
- Duplicados exactos: {perfil['duplicados_exactos']}.
- Mismo cliente, fecha y producto: {perfil['duplicados_cliente_fecha_producto']} (se conservan y se marcan).
- Incoherencias entre días de mora y estado: {perfil['incoherencias_estado_vs_dias']}.
- Cuentas de ahorro con días de mora: {perfil['ahorros_con_dias_mora']:,} de {perfil['ahorros_total']:,} (se aíslan de los KPI de cartera).
- Score fuera de rango: {perfil['score_fuera_rango']}. NPS fuera de rango: {perfil['nps_fuera_rango']}. Saldos no positivos: {perfil['saldos_no_positivos']}.
- Saldos atípicos marcados (IQR por producto): {int(d['saldo_atipico'].sum()):,}.

## Variables
| Variable | Tipo | Faltantes | % | Únicos |
|---|---|---|---|---|
{vars_md}

## Decisiones
1. Lectura con `utf-8-sig` para eliminar el BOM del encabezado.
2. NPS faltante ({perfil['variables'][-1]['pct_faltantes']} %) no se imputa; se excluye solo del cálculo de NPS.
3. Cuenta de ahorros sale de los indicadores de riesgo de cartera: no es crédito.
4. No se elimina ningún registro; las alertas de calidad quedan como columnas.
5. Se crea un modelo estrella: `fact_obligacion` y seis dimensiones.
"""
    (carpeta / "perfilamiento_datos.md").write_text(md, encoding="utf-8")


# ----------------------------------------------------------------------------
# Orquestación
# ----------------------------------------------------------------------------
def ejecutar() -> dict:
    crudo = leer_crudo()
    perfil = perfilar(crudo)
    limpio = limpiar_y_derivar(crudo)
    modelo = construir_modelo(limpio)

    carpeta_modelo = ruta("modelo")
    carpeta_modelo.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in modelo.items():
        tabla.to_csv(carpeta_modelo / f"{nombre}.csv", index=False, encoding="utf-8")

    limpio.to_csv(ruta("procesado"), index=False, encoding="utf-8")
    escribir_reportes(perfil, limpio)
    return perfil


if __name__ == "__main__":
    print(json.dumps(ejecutar(), ensure_ascii=False, indent=2)[:1500])
