"""
Router para la integración con Portfolio Analyzer
Proporciona endpoints para:
- Ejecutar análisis usando el proveedor de datos unificado (`client_data_provider`)
- Servir métricas y gráficos generados por el analizador
"""

import os
import sys
import json
import glob
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
import logging
from pydantic import BaseModel

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Configuración del directorio de outputs del Portfolio Analyzer
PORTFOLIO_OUTPUTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    "Portfolio_analizer", 
    "outputs"
)

# Asegurar que los módulos de Portfolio_analizer/src sean importables desde este router
PORTFOLIO_ANALYZER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "Portfolio_analizer"
)
if PORTFOLIO_ANALYZER_DIR not in sys.path:
    sys.path.append(PORTFOLIO_ANALYZER_DIR)

# Importar funciones de análisis y formateo desde Portfolio_analizer/src
try:
    from src.portfolio_metrics import (
        generate_complete_analysis,
        calculate_portfolio_returns,
        generate_performance_summary,
        find_optimal_portfolios,
    )
    from src.api_responses import format_for_fastapi
except Exception as e:
    logging.getLogger(__name__).warning(
        f"No se pudieron importar módulos de Portfolio_analizer/src: {e}"
    )

# Importar proveedor de datos unificado
try:
    from client_data_provider import (
        get_client_portfolio,
        fetch_portfolio_market_data,
    )
except Exception as e:
    logging.getLogger(__name__).warning(
        f"No se pudo importar client_data_provider: {e}"
    )


# ===== Modelos Pydantic =====
class PortfolioAnalysisRequest(BaseModel):
    tickers: List[str]
    weights: Dict[str, float]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    risk_free_rate: Optional[float] = 0.02
    generate_charts: Optional[bool] = True

def get_latest_json_file() -> Optional[str]:
    """
    Encuentra el archivo JSON más reciente en el directorio de outputs
    """
    try:
        json_pattern = os.path.join(PORTFOLIO_OUTPUTS_DIR, "api_response_*.json")
        json_files = glob.glob(json_pattern)
        
        if not json_files:
            logger.warning(f"No se encontraron archivos JSON en {PORTFOLIO_OUTPUTS_DIR}")
            return None
            
        # Ordenar por fecha de modificación (más reciente primero)
        latest_file = max(json_files, key=os.path.getmtime)
        logger.info(f"Archivo JSON más reciente: {latest_file}")
        return latest_file
        
    except Exception as e:
        logger.error(f"Error al buscar archivos JSON: {str(e)}")
        return None

def get_latest_html_file(chart_type: str) -> Optional[str]:
    """
    Encuentra el archivo HTML más reciente para un tipo de gráfico específico
    
    Args:
        chart_type: Tipo de gráfico ('cumulative_returns', 'composition_donut', etc.)
    """
    try:
        # Mapeo de nombres de gráficos a patrones de archivo
        chart_patterns = {
            'cumulative_returns': 'rendimiento_acumulado_interactivo_*.html',
            'composition_donut': 'donut_chart_interactivo_*.html',
            'correlation_matrix': 'matriz_correlacion_interactiva_*.html',
            'drawdown_underwater': 'drawdown_underwater_interactivo_*.html',
            'breakdown_chart': 'breakdown_chart_interactivo_*.html'
        }
        
        if chart_type not in chart_patterns:
            logger.warning(f"Tipo de gráfico no reconocido: {chart_type}")
            return None
            
        html_pattern = os.path.join(PORTFOLIO_OUTPUTS_DIR, chart_patterns[chart_type])
        html_files = glob.glob(html_pattern)
        
        if not html_files:
            logger.warning(f"No se encontraron archivos HTML para {chart_type}")
            return None
            
        # Ordenar por fecha de modificación (más reciente primero)
        latest_file = max(html_files, key=os.path.getmtime)
        logger.info(f"Archivo HTML más reciente para {chart_type}: {latest_file}")
        return latest_file
        
    except Exception as e:
        logger.error(f"Error al buscar archivos HTML para {chart_type}: {str(e)}")
        return None


@router.get("/api/portfolio/config")
async def get_portfolio_config() -> Dict[str, Any]:
    """
    Obtiene la configuración del portafolio por defecto desde el proveedor unificado.
    """
    try:
        cfg = get_client_portfolio(client_id=None)  # placeholder a BD
        return {
            "status": "success",
            "config": cfg,
            "description": "Configuración del portafolio por defecto (proveedor central)",
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/analyze")
async def analyze_default_portfolio() -> Dict[str, Any]:
    """
    Analiza el portafolio por defecto usando el proveedor central y genera salidas en `Portfolio_analizer/outputs`.
    """
    try:
        cfg = get_client_portfolio(client_id=None)
        tickers = cfg["tickers"]
        weights = cfg["weights"]

        prices_df, asset_returns = fetch_portfolio_market_data(tickers, period="5y")
        if prices_df is None or prices_df.empty:
            raise HTTPException(status_code=500, detail="No se pudieron descargar datos del portafolio por defecto")

        weights_array = [weights.get(t, 0.0) for t in tickers]
        portfolio_returns = calculate_portfolio_returns(asset_returns, weights_array)

        # Generar análisis completo en el directorio de outputs del analizador
        os.makedirs(PORTFOLIO_OUTPUTS_DIR, exist_ok=True)
        output_files = generate_complete_analysis(
            portfolio_returns=portfolio_returns,
            asset_returns=asset_returns,
            portfolio_weights=weights,
            risk_free_rate=0.02,
            output_dir=PORTFOLIO_OUTPUTS_DIR,
            generate_api_response=True,
        )

        performance_metrics = generate_performance_summary(portfolio_returns, 0.02)
        optimal_portfolios = find_optimal_portfolios(asset_returns, 0.02)

        api_response = format_for_fastapi(
            portfolio_returns=portfolio_returns,
            asset_returns=asset_returns,
            portfolio_weights=weights,
            metrics=performance_metrics,
            optimized_portfolios=optimal_portfolios,
            output_dir=PORTFOLIO_OUTPUTS_DIR,
        )

        return {
            "status": "success",
            "message": "Análisis completado exitosamente",
            "data": api_response,
            "generated_files": list(output_files.keys()),
            "analysis_timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).error(f"Error en análisis por defecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/portfolio/analyze/custom")
async def analyze_custom_portfolio(request: PortfolioAnalysisRequest) -> Dict[str, Any]:
    """
    Analiza un portafolio personalizado con parámetros específicos del usuario, usando el proveedor central.
    """
    try:
        total_weight = sum(request.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Los pesos deben sumar 1.0, suma actual: {total_weight:.4f}",
            )

        missing_weights = set(request.tickers) - set(request.weights.keys())
        if missing_weights:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan pesos para los siguientes tickers: {list(missing_weights)}",
            )

        # Fechas por defecto: últimos ~2 años si no se especifica
        end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
        start_date = request.start_date or (datetime.now().replace(year=datetime.now().year - 2).strftime("%Y-%m-%d"))

        prices_df, asset_returns = fetch_portfolio_market_data(
            request.tickers, start_date=start_date, end_date=end_date
        )
        if prices_df is None or prices_df.empty or asset_returns is None or asset_returns.empty:
            raise HTTPException(
                status_code=404,
                detail="No se pudieron obtener datos para los tickers especificados",
            )

        weights_array = [request.weights[t] for t in request.tickers]
        portfolio_returns = calculate_portfolio_returns(asset_returns, weights_array)

        os.makedirs(PORTFOLIO_OUTPUTS_DIR, exist_ok=True)
        output_files = generate_complete_analysis(
            portfolio_returns=portfolio_returns,
            asset_returns=asset_returns,
            portfolio_weights=request.weights,
            risk_free_rate=request.risk_free_rate,
            output_dir=PORTFOLIO_OUTPUTS_DIR,
            generate_api_response=True,
        )

        performance_metrics = generate_performance_summary(portfolio_returns, request.risk_free_rate)
        optimal_portfolios = find_optimal_portfolios(asset_returns, request.risk_free_rate)

        api_response = format_for_fastapi(
            portfolio_returns=portfolio_returns,
            asset_returns=asset_returns,
            portfolio_weights=request.weights,
            metrics=performance_metrics,
            optimized_portfolios=optimal_portfolios,
            output_dir=PORTFOLIO_OUTPUTS_DIR,
        )

        return {
            "status": "success",
            "message": "Análisis personalizado completado",
            "request_parameters": request.dict(),
            "data": api_response,
            "generated_files": list(output_files.keys()),
            "analysis_timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).error(f"Error en análisis personalizado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/live-metrics")
async def get_live_metrics():
    """
    Endpoint para obtener las métricas en vivo del portfolio
    Retorna performance_metrics y risk_analysis del archivo JSON más reciente
    """
    try:
        latest_json = get_latest_json_file()
        
        if not latest_json:
            raise HTTPException(
                status_code=404, 
                detail="No se encontraron archivos de análisis de portfolio"
            )
        
        with open(latest_json, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Extraer las secciones requeridas según el mapeo del TODO.md
        response_data = {
            "timestamp": data.get("timestamp"),
            "analysis_period": data.get("analysis_period"),
            "portfolio_composition": data.get("portfolio_composition"),
            "performance_metrics": data.get("performance_metrics", {}),
            "risk_analysis": data.get("risk_analysis", {}),
            "correlations": data.get("correlations", {})
        }
        
        logger.info("Métricas en vivo servidas exitosamente")
        return response_data
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Archivo de métricas no encontrado"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Error al decodificar el archivo de métricas"
        )
    except Exception as e:
        logger.error(f"Error al obtener métricas en vivo: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/api/portfolio/charts/{chart_name}")
async def get_portfolio_chart(chart_name: str):
    """
    Endpoint para servir los gráficos HTML generados por el Portfolio Analyzer
    
    Args:
        chart_name: Nombre del gráfico ('cumulative_returns', 'composition_donut', etc.)
    """
    try:
        latest_html = get_latest_html_file(chart_name)
        
        if not latest_html:
            raise HTTPException(
                status_code=404,
                detail=f"Gráfico '{chart_name}' no encontrado"
            )
        
        if not os.path.exists(latest_html):
            raise HTTPException(
                status_code=404,
                detail=f"Archivo de gráfico no existe: {latest_html}"
            )
        
        logger.info(f"Sirviendo gráfico: {chart_name} desde {latest_html}")
        
        # Leer el contenido HTML y servirlo directamente
        with open(latest_html, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error al servir gráfico {chart_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al servir gráfico: {str(e)}"
        )

@router.get("/api/portfolio/latest-analysis-timestamp")
async def get_latest_analysis_timestamp():
    """
    Endpoint de control para obtener el timestamp del último análisis
    Utilizado por el frontend para detectar actualizaciones automáticas
    """
    try:
        latest_json = get_latest_json_file()
        
        if not latest_json:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron archivos de análisis"
            )
        
        # Obtener la fecha de modificación del archivo
        modification_time = os.path.getmtime(latest_json)
        timestamp = datetime.fromtimestamp(modification_time)
        
        # Leer también el timestamp interno del JSON para mayor precisión
        with open(latest_json, 'r', encoding='utf-8') as file:
            data = json.load(file)
            internal_timestamp = data.get("timestamp")
        
        response_data = {
            "file_modification_time": timestamp.isoformat(),
            "internal_timestamp": internal_timestamp,
            "file_path": os.path.basename(latest_json)
        }
        
        logger.info(f"Timestamp del último análisis: {timestamp}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error al obtener timestamp: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener timestamp: {str(e)}"
        )

@router.get("/api/portfolio/health")
async def portfolio_health_check():
    """
    Endpoint de salud para verificar la disponibilidad del Portfolio Analyzer
    """
    try:
        outputs_dir_exists = os.path.exists(PORTFOLIO_OUTPUTS_DIR)
        latest_json = get_latest_json_file()
        has_recent_data = latest_json is not None
        
        if has_recent_data:
            file_age_seconds = datetime.now().timestamp() - os.path.getmtime(latest_json)
            file_age_hours = file_age_seconds / 3600
        else:
            file_age_hours = None
        
        return {
            "status": "healthy" if outputs_dir_exists and has_recent_data else "warning",
            "outputs_directory_exists": outputs_dir_exists,
            "outputs_directory_path": PORTFOLIO_OUTPUTS_DIR,
            "has_recent_analysis": has_recent_data,
            "latest_file_age_hours": file_age_hours,
            "available_charts": [
                'cumulative_returns',
                'composition_donut', 
                'correlation_matrix',
                'drawdown_underwater',
                'breakdown_chart'
            ]
        }
        
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
