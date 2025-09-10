# src/api_responses.py
"""
Módulo para generar respuestas JSON optimizadas para FastAPI.

Este módulo proporciona clases y funciones para convertir los resultados del
análisis de portafolios en respuestas JSON estructuradas y optimizadas para
endpoints de API REST.

Clases principales:
- PortfolioAPIResponse: Clase para generar respuestas JSON estructuradas

Funciones principales:
- format_for_fastapi: Función de utilidad para formateo rápido

Autor: Portfolio Analyzer Team
Fecha: Julio 2025
Versión: 2.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path
from .daily_generation_control import DailyGenerationController

class PortfolioAPIResponse:
    """
    Clase para generar respuestas JSON estructuradas para API endpoints
    """
    
    def __init__(self, portfolio_returns: pd.Series, asset_returns: pd.DataFrame, 
                 portfolio_weights: Dict[str, float], output_dir: str = "outputs"):
        self.portfolio_returns = portfolio_returns
        self.asset_returns = asset_returns
        self.portfolio_weights = portfolio_weights
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Inicializar el controlador de generaciones diarias
        self.daily_controller = DailyGenerationController(output_dir)
        
    def generate_api_response(self, metrics: Dict[str, Any], 
                            optimized_portfolios: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera una respuesta JSON completa para endpoints de FastAPI
        
        Returns:
            Dict: Respuesta estructurada con todos los datos del análisis
        """
        
        response = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "analysis_period": {
                "start_date": self.portfolio_returns.index[0].strftime("%Y-%m-%d"),
                "end_date": self.portfolio_returns.index[-1].strftime("%Y-%m-%d"),
                "total_days": len(self.portfolio_returns)
            },
            "portfolio_composition": self.portfolio_weights,
            "performance_metrics": self._format_metrics(metrics),
            "optimization_results": self._format_optimization(optimized_portfolios),
            "risk_analysis": self._generate_risk_analysis(),
            "correlations": self._generate_correlation_matrix(),
            "charts": self._generate_chart_paths(),
            "time_series_data": self._generate_time_series_data(),
            "recommendations": self._generate_recommendations(metrics, optimized_portfolios),
            "current_market_info": self._generate_current_market_info()
        }
        
        # Guardar respuesta JSON con sistema de control diario
        json_path = self.daily_controller.prepare_daily_file("api_response", "json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(response, f, indent=2, ensure_ascii=False, default=str)
            
        return response
    
    def _format_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea las métricas para la API"""
        return {
            "annualized_return": round(metrics.get("Rendimiento Anualizado (%)", 0), 2),
            "annualized_volatility": round(metrics.get("Volatilidad Anualizada (%)", 0), 2),
            "sharpe_ratio": round(metrics.get("Ratio de Sharpe", 0), 2),
            "sortino_ratio": round(metrics.get("Ratio de Sortino", 0), 2),
            "calmar_ratio": round(metrics.get("Ratio de Calmar", 0), 2),
            "max_drawdown": round(metrics.get("Máximo Drawdown (%)", 0), 2),
            "var_daily": round(metrics.get("Valor en Riesgo (VaR) Diario (%)", 0), 2),
            "skewness": round(metrics.get("Skewness (Asimetría)", 0), 2),
            "kurtosis": round(metrics.get("Kurtosis (Curtosis)", 0), 2)
        }
    
    def _format_optimization(self, optimized_portfolios: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea los resultados de optimización para la API"""
        optimization_results = {}
        
        for opt_type, data in optimized_portfolios.items():
            if isinstance(data, dict) and 'weights' in data:
                optimization_results[opt_type] = {
                    "weights": {asset: round(weight * 100, 2) for asset, weight in data['weights'].items()},
                    "expected_return": round(data.get("expected_return", 0) * 100, 2),
                    "volatility": round(data.get("volatility", 0) * 100, 2),
                    "sharpe_ratio": round(data.get("sharpe_ratio", 0), 2)
                }
        
        return optimization_results
    
    def _generate_risk_analysis(self) -> Dict[str, Any]:
        """Genera análisis de riesgo detallado"""
        returns = self.portfolio_returns
        
        # Calcular percentiles de riesgo
        percentiles = [1, 5, 10, 25, 75, 90, 95, 99]
        risk_percentiles = {f"percentile_{p}": round(np.percentile(returns, p) * 100, 2) 
                           for p in percentiles}
        
        # Análisis de drawdown
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        
        return {
            "risk_percentiles": risk_percentiles,
            "drawdown_analysis": {
                "current_drawdown": round(drawdown.iloc[-1] * 100, 2),
                "max_drawdown": round(drawdown.min() * 100, 2),
                "drawdown_duration_days": int((drawdown < -0.05).sum()),
                "recovery_periods": self._calculate_recovery_periods(drawdown)
            },
            "volatility_analysis": {
                "daily_vol": round(returns.std() * 100, 2),
                "weekly_vol": round(returns.std() * np.sqrt(5) * 100, 2),
                "monthly_vol": round(returns.std() * np.sqrt(21) * 100, 2),
                "annual_vol": round(returns.std() * np.sqrt(252) * 100, 2)
            }
        }
    
    def _generate_correlation_matrix(self) -> Dict[str, Any]:
        """Genera matriz de correlación en formato API"""
        corr_matrix = self.asset_returns.corr()
        
        # Convertir a formato de lista de listas para fácil consumo en frontend
        correlation_data = []
        assets = list(corr_matrix.columns)
        
        for i, asset1 in enumerate(assets):
            row_data = []
            for j, asset2 in enumerate(assets):
                row_data.append({
                    "asset1": asset1,
                    "asset2": asset2,
                    "correlation": round(corr_matrix.iloc[i, j], 3)
                })
            correlation_data.append(row_data)
        
        return {
            "assets": assets,
            "matrix": correlation_data,
            "summary": {
                "avg_correlation": round(corr_matrix.values[np.triu_indices_from(corr_matrix.values, 1)].mean(), 3),
                "max_correlation": round(corr_matrix.values[np.triu_indices_from(corr_matrix.values, 1)].max(), 3),
                "min_correlation": round(corr_matrix.values[np.triu_indices_from(corr_matrix.values, 1)].min(), 3)
            }
        }
    
    def _generate_chart_paths(self) -> Dict[str, str]:
        """Genera las rutas de los gráficos generados"""
        return {
            "cumulative_returns": f"rendimiento_acumulado_{self.timestamp}.png",
            "drawdown_chart": f"drawdown_underwater_{self.timestamp}.png",
            "correlation_heatmap": f"matriz_correlacion_{self.timestamp}.png"
        }
    
    def _generate_time_series_data(self, max_points: int = 500) -> Dict[str, List]:
        """
        Genera datos de series temporales para gráficos en frontend
        Limita los puntos para evitar sobrecarga en la API
        """
        
        # Resamplear si hay demasiados puntos
        if len(self.portfolio_returns) > max_points:
            # Calcular el paso para obtener aproximadamente max_points
            step = len(self.portfolio_returns) // max_points
            sampled_returns = self.portfolio_returns.iloc[::step]
        else:
            sampled_returns = self.portfolio_returns
        
        # Calcular retornos acumulados
        cumulative_returns = (1 + sampled_returns).cumprod()
        
        # Calcular drawdown
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        
        return {
            "dates": [date.strftime("%Y-%m-%d") for date in sampled_returns.index],
            "portfolio_returns": [round(ret * 100, 4) for ret in sampled_returns.values],
            "cumulative_returns": [round((cum_ret - 1) * 100, 2) for cum_ret in cumulative_returns.values],
            "drawdown": [round(dd * 100, 2) for dd in drawdown.values],
            "individual_assets": {
                asset: [round(ret * 100, 4) for ret in self.asset_returns[asset].reindex(sampled_returns.index).values]
                for asset in self.asset_returns.columns
            }
        }
    
    def _generate_recommendations(self, metrics: Dict[str, Any], 
                                optimized_portfolios: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Genera recomendaciones basadas en el análisis"""
        recommendations = []
        
        # Análisis del Sharpe Ratio
        sharpe = metrics.get("Ratio de Sharpe", 0)
        if sharpe < 0.5:
            recommendations.append({
                "type": "risk_adjustment",
                "priority": "high",
                "title": "Ratio de Sharpe Bajo",
                "description": "El portafolio tiene un ratio de Sharpe por debajo de 0.5, considerado subóptimo.",
                "action": "Considere rebalancear según la optimización de máximo Sharpe."
            })
        elif sharpe > 1.0:
            recommendations.append({
                "type": "performance",
                "priority": "low",
                "title": "Excelente Ratio de Sharpe",
                "description": "El portafolio muestra un rendimiento ajustado por riesgo excepcional.",
                "action": "Mantenga la estrategia actual y monitoree regularmente."
            })
        
        # Análisis de Drawdown
        max_dd = abs(metrics.get("Máximo Drawdown (%)", 0))
        if max_dd > 20:
            recommendations.append({
                "type": "risk_management",
                "priority": "high",
                "title": "Alto Drawdown",
                "description": f"El máximo drawdown de {max_dd:.1f}% indica alto riesgo de pérdidas.",
                "action": "Considere la composición de mínima volatilidad para reducir riesgo."
            })
        
        # Análisis de diversificación
        corr_matrix = self.asset_returns.corr()
        avg_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, 1)].mean()
        
        if avg_corr > 0.7:
            recommendations.append({
                "type": "diversification",
                "priority": "medium",
                "title": "Baja Diversificación",
                "description": f"La correlación promedio de {avg_corr:.2f} indica concentración de riesgo.",
                "action": "Considere agregar activos de diferentes sectores o clases."
            })
        
        return recommendations
    
    def _generate_current_market_info(self) -> Dict[str, Any]:
        """Genera información actual de mercado para cada activo del portafolio"""
        try:
            from .data_manager import get_current_asset_info
        except ImportError:
            # Fallback si no se puede importar
            return {asset: {"error": "No se pudo obtener información actual"} for asset in self.portfolio_weights.keys()}
        
        current_info = {}
        for asset in self.portfolio_weights.keys():
            asset_info = get_current_asset_info(asset)
            if "error" not in asset_info:
                current_info[asset] = {
                    "company_name": asset_info.get('company_name'),
                    "current_price": asset_info.get('current_price'),
                    "price_change": asset_info.get('price_change'),
                    "percent_change": asset_info.get('percent_change'),
                    "market_cap": asset_info.get('market_cap'),
                    "volume": asset_info.get('volume'),
                    "pe_ratio": asset_info.get('pe_ratio'),
                    "dividend_yield": asset_info.get('dividend_yield'),
                    "sector": asset_info.get('sector'),
                    "industry": asset_info.get('industry'),
                    "fifty_two_week_high": asset_info.get('fifty_two_week_high'),
                    "fifty_two_week_low": asset_info.get('fifty_two_week_low')
                }
            else:
                current_info[asset] = {"error": asset_info["error"]}
        
        return current_info
    
    def _calculate_recovery_periods(self, drawdown: pd.Series) -> List[Dict[str, Any]]:
        """Calcula períodos de recuperación de drawdowns"""
        recovery_periods = []
        
        # Identificar períodos de drawdown significativos (>5%)
        significant_dd = drawdown < -0.05
        
        if significant_dd.any():
            # Encontrar inicios y finales de períodos de drawdown
            dd_starts = significant_dd & ~significant_dd.shift(1, fill_value=False)
            dd_ends = ~significant_dd & significant_dd.shift(1, fill_value=False)
            
            start_dates = drawdown.index[dd_starts]
            end_dates = drawdown.index[dd_ends]
            
            # Emparejar inicios y finales
            for i, start_date in enumerate(start_dates):
                # Buscar el primer final después del inicio
                end_candidates = end_dates[end_dates > start_date]
                if len(end_candidates) > 0:
                    end_date = end_candidates[0]
                    duration = (end_date - start_date).days
                    max_dd_in_period = drawdown.loc[start_date:end_date].min()
                    
                    recovery_periods.append({
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "duration_days": duration,
                        "max_drawdown": round(max_dd_in_period * 100, 2)
                    })
        
        return recovery_periods[:5]  # Limitar a los 5 más recientes


# TODO: Conectar con base de datos para configuración dinámica
# class DatabaseConfig:
#     """
#     Clase para manejar configuración desde base de datos
#     """
#     
#     def __init__(self, db_connection):
#         self.db = db_connection
#     
#     def get_portfolio_config(self, user_id: int, portfolio_id: int) -> Dict[str, Any]:
#         """
#         Obtiene configuración de portafolio desde la base de datos
#         
#         Args:
#             user_id: ID del usuario
#             portfolio_id: ID del portafolio
#             
#         Returns:
#             Dict con configuración: tickers, weights, start_date, end_date
#         """
#         # query = """
#         # SELECT tickers, weights, start_date, end_date, risk_free_rate
#         # FROM portfolios 
#         # WHERE user_id = %s AND portfolio_id = %s AND active = true
#         # """
#         # result = self.db.execute(query, (user_id, portfolio_id))
#         # return result.fetchone()
#         pass
#     
#     def save_analysis_results(self, user_id: int, portfolio_id: int, 
#                              results: Dict[str, Any]) -> bool:
#         """
#         Guarda resultados del análisis en la base de datos
#         
#         Args:
#             user_id: ID del usuario
#             portfolio_id: ID del portafolio
#             results: Resultados del análisis
#             
#         Returns:
#             bool: True si se guardó exitosamente
#         """
#         # insert_query = """
#         # INSERT INTO analysis_results 
#         # (user_id, portfolio_id, analysis_date, metrics, optimization_results)
#         # VALUES (%s, %s, %s, %s, %s)
#         # """
#         # self.db.execute(insert_query, (user_id, portfolio_id, datetime.now(), 
#         #                               json.dumps(results['performance_metrics']),
#         #                               json.dumps(results['optimization_results'])))
#         pass


def format_for_fastapi(portfolio_returns: pd.Series, asset_returns: pd.DataFrame,
                      portfolio_weights: Dict[str, float], metrics: Dict[str, Any],
                      optimized_portfolios: Dict[str, Any], output_dir: str = "outputs") -> Dict[str, Any]:
    """
    Función de conveniencia para generar respuesta API completa
    
    Args:
        portfolio_returns: Serie de retornos del portafolio
        asset_returns: DataFrame de retornos de activos individuales
        portfolio_weights: Diccionario con pesos del portafolio
        metrics: Métricas de rendimiento calculadas
        optimized_portfolios: Resultados de optimización
        output_dir: Directorio de salida
        
    Returns:
        Dict: Respuesta JSON completa para FastAPI
    """
    
    api_response = PortfolioAPIResponse(
        portfolio_returns=portfolio_returns,
        asset_returns=asset_returns,
        portfolio_weights=portfolio_weights,
        output_dir=output_dir
    )
    
    return api_response.generate_api_response(metrics, optimized_portfolios)
