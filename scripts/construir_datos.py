"""Reconstruye los datos procesados, el modelo estrella y los reportes.

Uso (desde la raíz del proyecto):  python scripts/construir_datos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import ejecutar  # noqa: E402

if __name__ == "__main__":
    perfil = ejecutar()
    print(f"Listo: {perfil['filas']:,} registros procesados.")
    print("Archivos en data/processed/ y reports/")
