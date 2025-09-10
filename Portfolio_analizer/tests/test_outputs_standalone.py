"""
Prueba standalone (sin FastAPI) para verificar generación de gráficos y archivos.

Ejecutar:
  python Portfolio_analizer/tests/test_outputs_standalone.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict

import numpy as np

# Rutas para importar módulos del proyecto
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]  # workspace root
PKG_ROOT = THIS_FILE.parents[1]      # Portfolio_analizer

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if str(PKG_ROOT) not in sys.path:
    sys.path.append(str(PKG_ROOT))

from client_data_provider import (
    get_client_portfolio,
    fetch_portfolio_market_data,
    get_default_period_dates,
)
from src.portfolio_metrics import (
    calculate_portfolio_returns,
    generate_complete_analysis,
)


def assert_file_nonempty(path: str) -> None:
    if not path:
        raise AssertionError("Ruta de archivo vacía en resultados")
    if not os.path.exists(path):
        raise AssertionError(f"No existe: {path}")
    if os.path.isdir(path):
        raise AssertionError(f"Esperado archivo, se encontró directorio: {path}")
    size = os.path.getsize(path)
    if size <= 0:
        raise AssertionError(f"Archivo vacío: {path}")


def main() -> int:
    print("🔍 Prueba de generación de outputs (standalone)")

    # 1) Portafolio por defecto via proveedor
    cfg = get_client_portfolio(client_id=None)
    tickers = cfg["tickers"]
    weights: Dict[str, float] = cfg["weights"]
    print(f"   • Activos: {len(tickers)} | Ej: {', '.join(tickers[:5])}...")

    # 2) Datos de mercado (2 años por rapidez)
    start_date, end_date = get_default_period_dates(years=2)
    prices_df, asset_returns = fetch_portfolio_market_data(
        tickers, start_date=start_date, end_date=end_date
    )
    if prices_df.empty or asset_returns.empty:
        print("❌ Descarga de datos fallida (dataframes vacíos)")
        return 1
    print(f"   • Días descargados: {len(prices_df)}")

    # 3) Retorno del portafolio
    weights_array = [weights[t] for t in tickers]
    portfolio_returns = calculate_portfolio_returns(asset_returns, np.array(weights_array))

    # 4) Ejecutar análisis completo (genera gráficos y reporte)
    outputs_dir = PKG_ROOT / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    output_files = generate_complete_analysis(
        portfolio_returns=portfolio_returns,
        asset_returns=asset_returns,
        portfolio_weights=weights,
        risk_free_rate=0.02,
        output_dir=str(outputs_dir),
        generate_api_response=True,
        generate_html=True,
    )

    # 5) Verificaciones mínimas de outputs críticos
    required_keys = [
        "rendimiento_acumulado",
        "drawdown",
        "correlacion",
        "markdown_report",
    ]

    missing = [k for k in required_keys if k not in output_files]
    if missing:
        print(f"❌ Faltan claves en resultados: {missing}")
        return 1

    errors = []
    for key in required_keys:
        try:
            path = output_files[key]
            if path:  # algunos pueden ser None si hubo fallback
                assert_file_nonempty(path)
                print(f"   ✅ {key}: {os.path.basename(path)} ({os.path.getsize(path)} bytes)")
            else:
                errors.append(f"Ruta None para {key}")
        except Exception as e:
            errors.append(f"{key}: {e}")

    if errors:
        print("❌ Validaciones con error:")
        for e in errors:
            print("   -", e)
        return 1

    print("\n🎉 Prueba exitosa: gráficos y reporte generados correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


