# src/portfolio_metrics.py
"""
Módulo de métricas y análisis de portafolio de inversión.

Este módulo proporciona funcionalidades completas para el análisis de portafolios financieros,
incluyendo cálculo de métricas de rendimiento, optimización de portafolios usando la Teoría
Moderna de Portafolios, y generación automática de reportes profesionales.

Funciones principales:
- calculate_portfolio_returns: Calcula retornos del portafolio
- generate_performance_summary: Genera métricas de rendimiento completas
- find_optimal_portfolios: Optimización usando frontera eficiente
- generate_markdown_report: Crea reportes profesionales en Markdown
- generate_complete_analysis: Función principal para análisis completo

Autor: Portfolio Analyzer Team
Fecha: Julio 2025
Versión: 2.0.0
"""

import pandas as pd
import numpy as np

# Parchear quantstats para evitar el error de IPython
import sys
def patch_quantstats():
    try:
        from IPython import get_ipython
        ipython = get_ipython()
        if ipython:
            # Crear un mock de la función magic que no haga nada
            def dummy_magic(line):
                pass
            ipython.magic = dummy_magic
    except:
        pass

patch_quantstats()
import quantstats as qs

from pypfopt import EfficientFrontier, risk_models, expected_returns
from typing import Dict
import os
from datetime import datetime
from pathlib import Path
from .api_responses import format_for_fastapi, PortfolioAPIResponse
from .interactive_charts import (
    plot_cumulative_returns,
    plot_donut_chart,
    plot_breakdown_chart,
    plot_correlation_matrix,
    plot_drawdown_underwater
)

def calculate_portfolio_returns(
    asset_returns: pd.DataFrame, 
    weights: np.ndarray
) -> pd.Series:
    """
    Calcula los retornos diarios de un portafolio a partir de los retornos de sus activos.

    Args:
        asset_returns (pd.DataFrame): DataFrame de retornos de los activos.
        weights (np.ndarray): Array de numpy con los pesos de cada activo.

    Returns:
        pd.Series: Una serie de pandas con los retornos diarios del portafolio.
    """
    return asset_returns.dot(weights)


def generate_performance_summary(
    portfolio_returns: pd.Series,
    risk_free_rate: float = 0.0,
) -> Dict[str, float]:
    """
    Calcula un resumen de los KPIs más importantes del portafolio usando QuantStats.

    Args:
        portfolio_returns (pd.Series): Serie de retornos diarios del portafolio.
        risk_free_rate (float): Tasa libre de riesgo anual.

    Returns:
        Dict[str, float]: Un diccionario con las métricas clave.
    """
    # Asegurarse de que el índice sea DatetimeIndex
    portfolio_returns.index = pd.to_datetime(portfolio_returns.index)
    
    # Usar funciones individuales de QuantStats
    summary = {
        "Rendimiento Anualizado (%)": qs.stats.cagr(portfolio_returns) * 100,
        "Volatilidad Anualizada (%)": qs.stats.volatility(portfolio_returns) * 100,
        "Ratio de Sharpe": qs.stats.sharpe(portfolio_returns, rf=risk_free_rate),
        "Ratio de Sortino": qs.stats.sortino(portfolio_returns, rf=risk_free_rate),
        "Ratio de Calmar": qs.stats.calmar(portfolio_returns),
        "Máximo Drawdown (%)": qs.stats.max_drawdown(portfolio_returns) * 100,
        "Skewness (Asimetría)": qs.stats.skew(portfolio_returns),
        "Kurtosis (Curtosis)": qs.stats.kurtosis(portfolio_returns),
        "Valor en Riesgo (VaR) Diario (%)": qs.stats.var(portfolio_returns) * 100,
    }
    
    # Redondear valores para una mejor presentación
    summary = {key: round(value, 2) for key, value in summary.items()}
    
    return summary
    

def find_optimal_portfolios(
    asset_returns: pd.DataFrame,
    risk_free_rate: float = 0.0
) -> Dict:
    """
    Calcula la Frontera Eficiente y encuentra los portafolios de Máximo Sharpe y Mínima Volatilidad.

    Args:
        asset_returns (pd.DataFrame): DataFrame de retornos diarios de los activos.
        risk_free_rate (float): Tasa libre de riesgo anual.

    Returns:
        Dict: Un diccionario que contiene:
              - 'max_sharpe': Pesos y rendimiento/riesgo del portafolio de Máximo Sharpe.
              - 'min_vol': Pesos y rendimiento/riesgo del portafolio de Mínima Volatilidad.
    """
    # PyPortfolioOpt necesita suficientes datos para una matriz de covarianza estable.
    if asset_returns.shape[0] < 30:
        raise ValueError("Datos insuficientes después de la limpieza. Se necesitan al menos 30 días.")

    # 1. Calcular los retornos esperados y la matriz de covarianza.
    # Es crucial indicar a PyPortfolioOpt que estamos pasando retornos, no precios.
    mu = expected_returns.mean_historical_return(asset_returns, returns_data=True)
    S = risk_models.sample_cov(asset_returns, returns_data=True)
    
    # Regularizar la matriz de covarianza para asegurar que sea semidefinida positiva.
    S = risk_models.fix_nonpositive_semidefinite(S, fix_method='spectral')

    # 2. Optimizar para el máximo Ratio de Sharpe
    ef_sharpe = EfficientFrontier(mu, S)
    weights_sharpe = ef_sharpe.max_sharpe(risk_free_rate=risk_free_rate)
    cleaned_weights_sharpe = ef_sharpe.clean_weights()
    perf_sharpe = ef_sharpe.portfolio_performance(verbose=False, risk_free_rate=risk_free_rate)

    # 3. Optimizar para la mínima volatilidad
    ef_vol = EfficientFrontier(mu, S)
    weights_vol = ef_vol.min_volatility()
    cleaned_weights_vol = ef_vol.clean_weights()
    perf_vol = ef_vol.portfolio_performance(verbose=False, risk_free_rate=risk_free_rate)

    results = {
        "max_sharpe": {
            "weights": cleaned_weights_sharpe,
            "performance": {
                "return": perf_sharpe[0],
                "volatility": perf_sharpe[1],
                "sharpe_ratio": perf_sharpe[2]
            }
        },
        "min_vol": {
            "weights": cleaned_weights_vol,
            "performance": {
                "return": perf_vol[0],
                "volatility": perf_vol[1],
                "sharpe_ratio": perf_vol[2]
            }
        }
    }
    
    return results


def generate_markdown_report(
    portfolio_returns: pd.Series,
    asset_returns: pd.DataFrame,
    portfolio_weights: Dict[str, float],
    performance_summary: Dict[str, float],
    optimal_portfolios: Dict,
    saved_charts: Dict[str, str],
    output_dir: str = "outputs"
) -> str:
    """
    Genera un reporte completo en formato Markdown con todas las métricas y análisis.

    Args:
        portfolio_returns (pd.Series): Retornos del portafolio.
        asset_returns (pd.DataFrame): Retornos de los activos.
        portfolio_weights (Dict[str, float]): Pesos del portafolio actual.
        performance_summary (Dict[str, float]): Resumen de métricas de rendimiento.
        optimal_portfolios (Dict): Resultados de optimización de portafolios.
        saved_charts (Dict[str, str]): Rutas de los gráficos guardados.
        output_dir (str): Directorio donde guardar el reporte.

    Returns:
        str: Ruta del archivo Markdown generado.
    """
    # Importar el controlador de generación diaria
    from .daily_generation_control import DailyGenerationController
    
    # Crear controlador con el directorio de salida
    daily_controller = DailyGenerationController(output_dir)
    
    # Preparar archivo con control diario (sobreescribe archivos del mismo día)
    filepath = daily_controller.prepare_daily_file("markdown_report", "md")
    
    # Calcular estadísticas adicionales
    start_date = portfolio_returns.index.min().strftime("%Y-%m-%d")
    end_date = portfolio_returns.index.max().strftime("%Y-%m-%d")
    total_days = len(portfolio_returns)
    
    # Generar contenido del reporte
    markdown_content = f"""# Reporte de Análisis de Portafolio

**Fecha de generación:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Período analizado:** {start_date} a {end_date}  
**Total de días:** {total_days}

---

## 📊 Resumen Ejecutivo

### Composición del Portafolio
| Activo | Peso (%) |
|--------|----------|
"""
    
    # Agregar tabla de pesos
    for asset, weight in portfolio_weights.items():
        markdown_content += f"| {asset} | {weight*100:.2f}% |\n"
    
    # Agregar información actual de cada activo
    markdown_content += f"""

### 📈 Información Actual de Mercado
| Activo | Precio | Cambio ($) | Cambio (%) | Cap. Mercado | Sector |
|--------|--------|------------|------------|--------------|--------|
"""
    
    # Importar la función para obtener información actual
    try:
        from .data_manager import get_current_asset_info
    except ImportError:
        # Si no se puede importar, usar valores por defecto
        def get_current_asset_info(asset):
            return {"error": "No se pudo obtener información actual"}
    
    for asset in portfolio_weights.keys():
        current_info = get_current_asset_info(asset)
        if "error" not in current_info:
            price = current_info.get('current_price', 'N/A')
            change = current_info.get('price_change', 'N/A')
            pct_change = current_info.get('percent_change', 'N/A')
            market_cap = current_info.get('market_cap')
            sector = current_info.get('sector', 'N/A')
            
            # Formatear capitalización de mercado
            if market_cap:
                if market_cap >= 1e12:
                    mc_str = f"${market_cap/1e12:.2f}T"
                elif market_cap >= 1e9:
                    mc_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    mc_str = f"${market_cap/1e6:.2f}M"
                else:
                    mc_str = f"${market_cap:,.0f}"
            else:
                mc_str = "N/A"
            
            # Formatear cambio con color semántico
            change_str = f"+${change:.2f}" if change >= 0 else f"-${abs(change):.2f}" if change != 'N/A' else 'N/A'
            pct_str = f"+{pct_change:.2f}%" if pct_change >= 0 else f"{pct_change:.2f}%" if pct_change != 'N/A' else 'N/A'
            
            markdown_content += f"| {asset} | ${price} | {change_str} | {pct_str} | {mc_str} | {sector} |\n"
        else:
            markdown_content += f"| {asset} | Error | - | - | - | - |\n"

    markdown_content += f"""

### Métricas de Rendimiento Clave
| Métrica | Valor |
|---------|-------|
"""
    
    # Agregar métricas de rendimiento
    for metric, value in performance_summary.items():
        if "%" in metric:
            markdown_content += f"| {metric} | {value:.2f}% |\n"
        else:
            markdown_content += f"| {metric} | {value:.2f} |\n"
    
    markdown_content += f"""

---

## 🎯 Optimización de Portafolios

### Portafolio de Máximo Ratio de Sharpe
**Rendimiento Anualizado:** {optimal_portfolios['max_sharpe']['performance']['return']*100:.2f}%  
**Volatilidad Anualizada:** {optimal_portfolios['max_sharpe']['performance']['volatility']*100:.2f}%  
**Ratio de Sharpe:** {optimal_portfolios['max_sharpe']['performance']['sharpe_ratio']:.2f}

#### Composición Óptima (Máximo Sharpe)
| Activo | Peso Óptimo (%) |
|--------|-----------------|
"""
    
    # Agregar pesos del portafolio de máximo Sharpe
    for asset, weight in optimal_portfolios['max_sharpe']['weights'].items():
        markdown_content += f"| {asset} | {weight*100:.2f}% |\n"
    
    markdown_content += f"""

### Portafolio de Mínima Volatilidad
**Rendimiento Anualizado:** {optimal_portfolios['min_vol']['performance']['return']*100:.2f}%  
**Volatilidad Anualizada:** {optimal_portfolios['min_vol']['performance']['volatility']*100:.2f}%  
**Ratio de Sharpe:** {optimal_portfolios['min_vol']['performance']['sharpe_ratio']:.2f}

#### Composición Óptima (Mínima Volatilidad)
| Activo | Peso Óptimo (%) |
|--------|-----------------|
"""
    
    # Agregar pesos del portafolio de mínima volatilidad
    for asset, weight in optimal_portfolios['min_vol']['weights'].items():
        markdown_content += f"| {asset} | {weight*100:.2f}% |\n"
    
    markdown_content += f"""

---

## 📈 Análisis de Correlaciones

### Matriz de Correlación de Activos
"""
    
    # Calcular matriz de correlación
    corr_matrix = asset_returns.corr()
    
    # Agregar tabla de correlación
    markdown_content += "| Activo |"
    for col in corr_matrix.columns:
        markdown_content += f" {col} |"
    markdown_content += "\n|--------|"
    for _ in corr_matrix.columns:
        markdown_content += "--------|"
    markdown_content += "\n"
    
    for idx in corr_matrix.index:
        markdown_content += f"| {idx} |"
        for col in corr_matrix.columns:
            markdown_content += f" {corr_matrix.loc[idx, col]:.3f} |"
        markdown_content += "\n"
    
    markdown_content += f"""

---

## 📊 Gráficos de Análisis

### Rendimiento Acumulado
"""
    
    # Verificar si el archivo es PNG o HTML
    cumulative_file = saved_charts['rendimiento_acumulado']
    if cumulative_file.endswith('.html'):
        markdown_content += f"[Ver Gráfico Interactivo - Rendimiento Acumulado]({os.path.basename(cumulative_file)})\n\n"
    else:
        markdown_content += f"![Rendimiento Acumulado]({os.path.basename(cumulative_file)})\n\n"

    markdown_content += "### Análisis de Drawdown\n"
    drawdown_file = saved_charts['drawdown']
    if drawdown_file.endswith('.html'):
        markdown_content += f"[Ver Gráfico Interactivo - Drawdown]({os.path.basename(drawdown_file)})\n\n"
    else:
        markdown_content += f"![Drawdown]({os.path.basename(drawdown_file)})\n\n"

    markdown_content += "### Matriz de Correlación (Heatmap)\n"
    correlation_file = saved_charts['correlacion']
    if correlation_file.endswith('.html'):
        markdown_content += f"[Ver Gráfico Interactivo - Correlación]({os.path.basename(correlation_file)})\n\n"
    else:
        markdown_content += f"![Correlación]({os.path.basename(correlation_file)})\n\n"

    markdown_content += f"""

---

## 🔍 Análisis Detallado

### Estadísticas de Riesgo
- **Valor en Riesgo (VaR) Diario:** {performance_summary.get('Valor en Riesgo (VaR) Diario (%)', 0):.2f}%
- **Máximo Drawdown:** {performance_summary.get('Máximo Drawdown (%)', 0):.2f}%
- **Skewness (Asimetría):** {performance_summary.get('Skewness (Asimetría)', 0):.2f}
- **Kurtosis (Curtosis):** {performance_summary.get('Kurtosis (Curtosis)', 0):.2f}

### Ratios de Rendimiento Ajustado por Riesgo
- **Ratio de Sharpe:** {performance_summary.get('Ratio de Sharpe', 0):.2f}
- **Ratio de Sortino:** {performance_summary.get('Ratio de Sortino', 0):.2f}
- **Ratio de Calmar:** {performance_summary.get('Ratio de Calmar', 0):.2f}

---

## 💡 Conclusiones y Recomendaciones

### Análisis del Portafolio Actual
"""
    
    # Agregar análisis automático basado en métricas
    sharpe_ratio = performance_summary.get('Ratio de Sharpe', 0)
    max_drawdown = performance_summary.get('Máximo Drawdown (%)', 0)
    volatility = performance_summary.get('Volatilidad Anualizada (%)', 0)
    
    if sharpe_ratio > 1.0:
        markdown_content += "✅ **Excelente rendimiento ajustado por riesgo** - El ratio de Sharpe superior a 1.0 indica una buena compensación riesgo-rendimiento.\n\n"
    elif sharpe_ratio > 0.5:
        markdown_content += "⚠️ **Rendimiento moderado** - El ratio de Sharpe sugiere un rendimiento aceptable, pero hay margen de mejora.\n\n"
    else:
        markdown_content += "❌ **Rendimiento bajo** - El ratio de Sharpe indica que el portafolio no está generando suficiente rendimiento por el riesgo asumido.\n\n"
    
    if abs(max_drawdown) > 20:
        markdown_content += "🚨 **Alto riesgo de pérdidas** - El máximo drawdown superior al 20% indica alta volatilidad y riesgo.\n\n"
    elif abs(max_drawdown) > 10:
        markdown_content += "⚠️ **Riesgo moderado** - El drawdown está en niveles manejables pero requiere monitoreo.\n\n"
    else:
        markdown_content += "✅ **Bajo riesgo de pérdidas** - El drawdown controlado indica una gestión de riesgo efectiva.\n\n"
    
    markdown_content += f"""
### Recomendaciones de Optimización
- **Para maximizar el ratio de Sharpe:** Considere ajustar los pesos según la composición óptima mostrada arriba.
- **Para minimizar riesgo:** La composición de mínima volatilidad puede ser más apropiada para perfiles conservadores.
- **Diversificación:** Analice las correlaciones para identificar oportunidades de mejor diversificación.

---

*Este reporte fue generado automáticamente el {datetime.now().strftime("%Y-%m-%d a las %H:%M:%S")}*
"""
    
    # Guardar el archivo
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return filepath


def generate_complete_analysis(
    portfolio_returns: pd.Series,
    asset_returns: pd.DataFrame,
    portfolio_weights: Dict[str, float],
    benchmark_returns: pd.Series = None,
    risk_free_rate: float = 0.0,
    output_dir: str = "outputs",
    generate_api_response: bool = False,
    generate_html: bool = False
) -> Dict[str, str]:
    """
    Función principal que ejecuta todo el análisis completo y genera reportes.

    Args:
        portfolio_returns (pd.Series): Retornos del portafolio.
        asset_returns (pd.DataFrame): Retornos de los activos.
        portfolio_weights (Dict[str, float]): Pesos del portafolio.
        benchmark_returns (pd.Series, optional): Retornos del benchmark.
        risk_free_rate (float): Tasa libre de riesgo.
        output_dir (str): Directorio de salida.
        generate_api_response (bool): Si True, genera también respuesta JSON para API.
        generate_html (bool): Si True, genera también archivos HTML interactivos.

    Returns:
        Dict[str, str]: Diccionario con las rutas de todos los archivos generados.
    """
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Generar timestamp para archivos únicos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Generar métricas de rendimiento
    performance_summary = generate_performance_summary(portfolio_returns, risk_free_rate)
    
    # 2. Encontrar portafolios óptimos
    optimal_portfolios = find_optimal_portfolios(asset_returns, risk_free_rate)
    
    # 3. Generar y guardar gráficos
    output_files = {}
    
    # Generar gráficos tradicionales usando matplotlib
    try:
        from .interactive_charts import generate_all_charts_and_save
        saved_charts = generate_all_charts_and_save(
            portfolio_returns=portfolio_returns, 
            asset_returns=asset_returns, 
            benchmark_returns=benchmark_returns,
            output_dir=output_dir,
            portfolio_weights=portfolio_weights
        )
        output_files.update(saved_charts)
    except ImportError:
        # Fallback: generar gráficos individuales
        print("⚠️ Generando gráficos individuales...")
        
        # Generar gráficos PNG básicos si las funciones están disponibles
        try:
            # Gráfico de rendimiento acumulado
            output_files['cumulative_return'] = plot_cumulative_returns(
                portfolio_returns, 
                asset_returns, 
                output_path=os.path.join(output_dir, f"rendimiento_acumulado_{timestamp}.png")
            )
        except Exception as e:
            print(f"No se pudo generar gráfico de rendimiento: {e}")
        
        try:
            # Gráfico de correlación
            output_files['correlation_matrix'] = plot_correlation_matrix(
                asset_returns, 
                output_path=os.path.join(output_dir, f"matriz_correlacion_{timestamp}.png")
            )
        except Exception as e:
            print(f"No se pudo generar matriz de correlación: {e}")
            
        try:
            # Gráfico donut
            output_files['donut_chart'] = plot_donut_chart(
                list(portfolio_weights.values()), 
                list(portfolio_weights.keys()), 
                output_path=os.path.join(output_dir, f"donut_chart_{timestamp}.png")
            )
        except Exception as e:
            print(f"No se pudo generar gráfico donut: {e}")
            
        try:
            # Gráfico breakdown
            output_files['breakdown_chart'] = plot_breakdown_chart(
                list(portfolio_weights.values()), 
                list(portfolio_weights.keys()), 
                output_path=os.path.join(output_dir, f"breakdown_chart_{timestamp}.png")
            )
        except Exception as e:
            print(f"No se pudo generar gráfico breakdown: {e}")
            
        try:
            # Gráfico drawdown underwater
            output_files['drawdown_underwater'] = plot_drawdown_underwater(
                portfolio_returns, 
                output_path=os.path.join(output_dir, f"drawdown_underwater_{timestamp}.png")
            )
        except Exception as e:
            print(f"No se pudo generar gráfico drawdown: {e}")

    # 4. Generar gráficos HTML interactivos
    try:
        # Gráficos HTML Interactivos
        output_files['interactive_cumulative_return'] = plot_cumulative_returns(
            portfolio_returns, 
            asset_returns, 
            output_path=os.path.join(output_dir, f"rendimiento_acumulado_interactivo_{timestamp}.html")
        )
        output_files['interactive_donut_chart'] = plot_donut_chart(
            list(portfolio_weights.values()), 
            list(portfolio_weights.keys()), 
            output_path=os.path.join(output_dir, f"donut_chart_interactivo_{timestamp}.html")
        )
        output_files['interactive_breakdown_chart'] = plot_breakdown_chart(
            list(portfolio_weights.values()), 
            list(portfolio_weights.keys()), 
            output_path=os.path.join(output_dir, f"breakdown_chart_interactivo_{timestamp}.html")
        )
        output_files['interactive_correlation_matrix'] = plot_correlation_matrix(
            asset_returns, 
            output_path=os.path.join(output_dir, f"matriz_correlacion_interactiva_{timestamp}.html")
        )
        output_files['interactive_drawdown_underwater'] = plot_drawdown_underwater(
            portfolio_returns, 
            output_path=os.path.join(output_dir, f"drawdown_underwater_interactivo_{timestamp}.html")
        )
    except Exception as e:
        print(f"⚠️ No se pudieron generar gráficos interactivos: {e}")

    # 5. Generar reporte en Markdown
    try:
        markdown_path = generate_markdown_report(
            portfolio_returns, asset_returns, portfolio_weights,
            performance_summary, optimal_portfolios, output_files, output_dir
        )
        output_files["markdown_report"] = markdown_path
    except Exception as e:
        print(f"⚠️ No se pudo generar el reporte Markdown: {e}")
    
    # 6. Generar respuesta JSON para API si se solicita
    if generate_api_response:
        try:
            # Generar respuesta JSON usando format_for_fastapi
            api_response_data = format_for_fastapi(
                portfolio_returns=portfolio_returns,
                asset_returns=asset_returns,
                portfolio_weights=portfolio_weights,
                metrics=performance_summary,
                optimized_portfolios=optimal_portfolios,
                output_dir=output_dir
            )
            
            # El archivo JSON ya se guarda automáticamente en format_for_fastapi
            # Solo necesitamos agregar la ruta al diccionario de archivos generados
            json_filename = f"api_response_{timestamp}.json"
            json_path = os.path.join(output_dir, json_filename)
            output_files["api_response"] = json_path
            
            print(f"   ✅ Respuesta JSON para API generada: {json_filename}")
            
        except Exception as e:
            print(f"⚠️ No se pudo generar la respuesta API: {e}")
            import traceback
            traceback.print_exc()
    
    return output_files