"""
Portfolio Analyzer - Módulo principal.

Este paquete contiene todas las funcionalidades para el análisis avanzado
de portafolios de inversión, incluyendo:

Módulos disponibles:
- data_manager: Gestión y descarga de datos financieros
- portfolio_metrics: Métricas y análisis de rendimiento
- interactive_charts: Visualizaciones interactivas
- api_responses: Respuestas estructuradas para API
- asset_classifier: Clasificación automática de activos

Autor: Portfolio Analyzer Team
Fecha: Julio 2025
Versión: 2.0.0
"""

from . import data_manager
from . import portfolio_metrics
from . import interactive_charts

__version__ = "2.0.0"
__author__ = "Portfolio Analyzer Team"

# Funciones principales disponibles al importar el paquete
from .data_manager import fetch_portfolio_data, calculate_returns
from .portfolio_metrics import generate_complete_analysis, calculate_portfolio_returns
from .interactive_charts import plot_cumulative_returns, plot_drawdown_underwater

__all__ = [
    'data_manager',
    'portfolio_metrics', 
    'interactive_charts',
    'fetch_portfolio_data',
    'calculate_returns',
    'generate_complete_analysis',
    'calculate_portfolio_returns',
    'plot_cumulative_returns',
    'plot_drawdown_underwater'
] 