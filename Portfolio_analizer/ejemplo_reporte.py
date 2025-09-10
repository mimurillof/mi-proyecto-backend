# ejemplo_reporte.py
"""
Ejemplo de uso completo del Portfolio Analyzer.

Este script demuestra cómo utilizar todas las funcionalidades del sistema
para generar un análisis completo de portafolio, incluyendo:
- Análisis de rendimiento y riesgo
- Optimización de portafolios
- Generación de gráficos profesionales
- Reportes automáticos en Markdown

Uso:
    python ejemplo_reporte.py

Autor: Portfolio Analyzer Team
Fecha: Julio 2025
Versión: 2.0.0
"""

import pandas as pd
import numpy as np
from src.portfolio_metrics import generate_complete_analysis, calculate_portfolio_returns
from src.data_manager import calculate_returns, get_current_asset_info
import sys
import os

# Habilitar import del proveedor de datos ubicado en la raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
from client_data_provider import (
    get_client_portfolio,
    fetch_portfolio_market_data,
)
from datetime import datetime, timedelta
import os

def ejemplo_reporte_completo():
    """
    Ejemplo completo de cómo generar un reporte profesional de análisis de portafolio.
    
    Este ejemplo:
    1. Define un portafolio de ejemplo con activos tecnológicos
    2. Descarga datos reales de mercado de Yahoo Finance
    3. Calcula métricas de rendimiento y riesgo
    4. Genera gráficos profesionales
    5. Crea un reporte completo en Markdown
    """
    
    print("🚀 Iniciando análisis completo de portafolio...")
    print("=" * 60)
    
    # 1. Configuración del portafolio (centralizado en proveedor)
    print("⚙️ Configurando portafolio (Proveedor)...")
    cfg = get_client_portfolio(client_id=None)
    symbols = cfg['tickers']
    weights = cfg['weights']
    
    print(f"   • Activos: {', '.join(symbols)}")
    print(f"   • Pesos: {', '.join([f'{w*100:.0f}%' for w in weights.values()])}")

    # 2.5. Obtener información actual de cada activo
    print("\nℹ️  Obteniendo información de precios en tiempo real...")
    current_assets_info = {}
    for symbol in symbols:
        info = get_current_asset_info(symbol)
        current_assets_info[symbol] = info
        if "error" in info:
            print(f"   • {symbol}: {info['error']}")
        else:
            # Formatear market cap y volumen para mejor legibilidad
            market_cap_val = info.get('market_cap')
            volume_val = info.get('volume')
            market_cap_str = f"MC: ${market_cap_val / 1e9:.2f}B" if market_cap_val else "MC: N/A"
            volume_str = f"Vol: {volume_val / 1e6:.2f}M" if volume_val else "Vol: N/A"
            print(f"   • {info['ticker']:<7} | Precio: ${info.get('current_price', 0):<8.2f} ({info.get('percent_change', 0):>6.2f}%) | {market_cap_str:<15} | {volume_str}")

    # 2. Descarga de datos de mercado (proveedor)
    print("\n📊 Descargando datos de mercado (Proveedor)...")
    
    try:
        asset_data, asset_returns = fetch_portfolio_market_data(symbols, period="5y")
        
        print(f"   ✅ Descargados {len(asset_data)} días de datos")
        
        # 3. Calcular retornos del portafolio
        print("\n🔢 Calculando retornos del portafolio...")
        weights_array = np.array([weights[symbol] for symbol in symbols])
        portfolio_returns = calculate_portfolio_returns(asset_returns, weights_array)
        
        print(f"   • Retorno promedio diario: {portfolio_returns.mean():.4f}")
        print(f"   • Volatilidad diaria: {portfolio_returns.std():.4f}")
        
        # 4. Generar análisis completo
        print("\n🔍 Generando análisis completo...")
        print("   • Calculando métricas de rendimiento...")
        print("   • Optimizando portafolios...")
        print("   • Generando gráficos...")
        print("   • Creando reporte en Markdown...")
        
        output_files = generate_complete_analysis(
            portfolio_returns=portfolio_returns,
            asset_returns=asset_returns,
            portfolio_weights=weights,
            risk_free_rate=0.02,  # 2% anual (tasa libre de riesgo típica)
            output_dir="outputs",
            generate_api_response=True  # Activar generación de respuesta JSON para API
        )
        
        # 5. Mostrar resultados
        print("\n" + "=" * 60)
        print("✅ ¡Análisis completado exitosamente!")
        print("=" * 60)
        
        print("\n📁 Archivos generados:")
        for file_type, path in output_files.items():
            if path: # Asegurarse de que la ruta no sea None
                is_image = any(ext in path for ext in ['.png', '.html'])
                is_json = path.endswith('.json')
                try:
                    file_size = os.path.getsize(path)
                    size_str = f"{file_size / 1024:.2f} KB"
                except (OSError, TypeError):
                    size_str = "N/A"

                if 'interactive' in file_type:
                    print(f"   🌐 {file_type}: {path} (Interactivo, {size_str})")
                elif is_json:
                    print(f"   📊 {file_type}: {path} (JSON API, {size_str})")
                elif is_image:
                    print(f"   🖼️ {file_type}: {path} (Imagen, {size_str})")
                else:
                    print(f"   📄 {file_type}: {path} (Reporte, {size_str})")

        print(f"\n🎯 Acciones recomendadas:")
        print(f"   1. Abrir y revisar el reporte principal: {output_files.get('markdown_report')}")
        print(f"   2. Explorar los gráficos interactivos (archivos .html) en la carpeta 'outputs/'")
        print(f"   3. Considerar las recomendaciones de optimización del reporte.")
        
        print(f"\n💡 Próximos pasos:")
        print(f"   • Personaliza los pesos del portafolio según tus preferencias")
        print(f"   • Experimenta con diferentes activos")
        print(f"   • Compara con un benchmark (ej. S&P 500)")
        
        return output_files
        
    except Exception as e:
        print(f"\n❌ Error durante el análisis: {e}")
        print("\n🔧 Posibles soluciones:")
        print("   • Verifica tu conexión a internet")
        print("   • Comprueba que los símbolos de activos sean válidos")
        print("   • Asegúrate de que las dependencias estén instaladas")
        print("   • Ejecuta: pip install -r requirements.txt")
        
        import traceback
        print(f"\n🐛 Detalles técnicos del error:")
        traceback.print_exc()
        
        return None

if __name__ == "__main__":
    print("🏦 Analizador de Portafolios de Inversión")
    print("📈 Generación de Reportes Profesionales")
    print()
    
    result = ejemplo_reporte_completo()
    
    if result:
        print("\n🎉 ¡Análisis completado! Revisa los archivos generados.")
    else:
        print("\n⚠️ El análisis no pudo completarse. Revisa los errores mostrados.")
    
    print("\nGracias por usar el Analizador de Portafolios 🚀")
