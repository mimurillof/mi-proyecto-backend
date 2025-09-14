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

# Importar servicio de Supabase Storage
try:
    from services.supabase_storage import get_supabase_storage
    from config import settings
    
    # Inicializar servicio de Supabase con configuración
    supabase_storage = get_supabase_storage(settings)
    SUPABASE_ENABLED = supabase_storage is not None
    
    if SUPABASE_ENABLED:
        logger.info("Servicio de Supabase Storage habilitado")
    else:
        logger.warning("Servicio de Supabase Storage no se pudo inicializar")
        
except Exception as e:
    SUPABASE_ENABLED = False
    logger.warning(f"Servicio de Supabase Storage deshabilitado: {e}")
    supabase_storage = None


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
    Endpoint para obtener las métricas en vivo del portfolio desde Supabase Storage
    Retorna performance_metrics y risk_analysis del archivo JSON en Supabase
    """
    try:
        # Verificar si Supabase está habilitado
        if not SUPABASE_ENABLED or not supabase_storage:
            # Fallback al método local si Supabase no está disponible
            return await get_live_metrics_local()
        
        # Leer métricas desde Supabase Storage
        data = await supabase_storage.read_metrics_json("api_response_B.json")
        
        # Extraer las secciones requeridas
        response_data = {
            "timestamp": data.get("timestamp"),
            "analysis_period": data.get("analysis_period"),
            "portfolio_composition": data.get("portfolio_composition"),
            "performance_metrics": data.get("performance_metrics", {}),
            "risk_analysis": data.get("risk_analysis", {}),
            "correlations": data.get("correlations", {}),
            "source": "supabase_storage"
        }
        
        logger.info("Métricas en vivo servidas exitosamente desde Supabase Storage")
        return response_data
        
    except Exception as e:
        logger.error(f"Error al obtener métricas desde Supabase: {str(e)}")
        # Intentar fallback al método local
        try:
            logger.info("Intentando fallback a archivos locales...")
            return await get_live_metrics_local()
        except Exception as fallback_error:
            logger.error(f"Error en fallback: {str(fallback_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error al obtener métricas: Supabase: {str(e)}, Local: {str(fallback_error)}"
            )

async def get_live_metrics_local():
    """
    Método de fallback para obtener métricas desde archivos locales
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
        
        # Extraer las secciones requeridas
        response_data = {
            "timestamp": data.get("timestamp"),
            "analysis_period": data.get("analysis_period"),
            "portfolio_composition": data.get("portfolio_composition"),
            "performance_metrics": data.get("performance_metrics", {}),
            "risk_analysis": data.get("risk_analysis", {}),
            "correlations": data.get("correlations", {}),
            "source": "local_files"
        }
        
        logger.info("Métricas en vivo servidas exitosamente desde archivos locales")
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
        logger.error(f"Error al obtener métricas en vivo locales: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/api/portfolio/charts/{chart_name}")
async def get_portfolio_chart(chart_name: str):
    """
    Endpoint para servir los gráficos HTML desde Supabase Storage
    
    Args:
        chart_name: Nombre del gráfico ('cumulative_returns', 'composition_donut', etc.)
    """
    try:
        # Verificar si Supabase está habilitado
        if not SUPABASE_ENABLED or not supabase_storage:
            # Fallback al método local si Supabase no está disponible
            return await get_portfolio_chart_local(chart_name)
        
        # Leer gráfico HTML desde Supabase Storage
        html_content = await supabase_storage.read_html_chart(chart_name)
        
        logger.info(f"Sirviendo gráfico: {chart_name} desde Supabase Storage")
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error al servir gráfico desde Supabase: {str(e)}")
        # Intentar fallback al método local
        try:
            logger.info(f"Intentando fallback a archivos locales para gráfico: {chart_name}")
            return await get_portfolio_chart_local(chart_name)
        except Exception as fallback_error:
            logger.error(f"Error en fallback para gráfico: {str(fallback_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error al servir gráfico: Supabase: {str(e)}, Local: {str(fallback_error)}"
            )

async def get_portfolio_chart_local(chart_name: str):
    """
    Método de fallback para servir gráficos desde archivos locales
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
        
        logger.info(f"Sirviendo gráfico: {chart_name} desde archivos locales: {latest_html}")
        
        # Leer el contenido HTML y servirlo directamente
        with open(latest_html, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al servir gráfico local {chart_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al servir gráfico local: {str(e)}"
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

# ===== NUEVOS ENDPOINTS PARA SUPABASE STORAGE =====

@router.get("/api/portfolio/signed-url/{filename}")
async def get_signed_url(filename: str, expires_in: int = 3600):
    """
    Genera una URL firmada para acceso directo a un archivo de métricas en Supabase Storage
    
    Args:
        filename: Nombre del archivo (ej: api_response_B.json)
        expires_in: Tiempo de expiración en segundos (por defecto: 1 hora)
    
    Returns:
        Dict con la URL firmada
    """
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no está disponible"
            )
        
        signed_url = supabase_storage.create_signed_url(filename, expires_in)
        
        return {
            "status": "success",
            "signed_url": signed_url,
            "filename": filename,
            "expires_in": expires_in,
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al generar URL firmada: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/supabase/metrics")
async def get_supabase_metrics(filename: str = "api_response_B.json"):
    """
    Obtiene métricas directamente desde Supabase Storage
    
    Args:
        filename: Nombre del archivo JSON (por defecto: api_response_B.json)
    """
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no está disponible"
            )
        
        data = await supabase_storage.read_metrics_json(filename)
        
        return {
            "status": "success",
            "source": "supabase_storage",
            "filename": filename,
            "data": data,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al obtener métricas desde Supabase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/supabase/files")
async def list_supabase_files():
    """
    Lista todos los archivos de métricas disponibles en Supabase Storage
    """
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no está disponible"
            )
        
        files = supabase_storage.list_metrics_files()
        
        return {
            "status": "success",
            "source": "supabase_storage",
            "files": files,
            "total_files": len(files),
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al listar archivos en Supabase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/supabase/health")
async def supabase_health_check():
    """
    Verifica el estado de la conexión con Supabase Storage
    """
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            return {
                "status": "disabled",
                "message": "Servicio de Supabase Storage no está habilitado",
                "timestamp": datetime.now().isoformat()
            }
        
        health_status = supabase_storage.health_check()
        return health_status
        
    except Exception as e:
        logger.error(f"Error en health check de Supabase: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ===== ENDPOINTS ESPECÍFICOS PARA GRÁFICOS EN SUPABASE =====

@router.get("/api/portfolio/charts/supabase/{chart_name}")
async def get_supabase_chart_direct(chart_name: str):
    """
    Obtiene un gráfico HTML directamente desde Supabase Storage (sin fallback)
    
    Args:
        chart_name: Nombre del gráfico ('cumulative_returns', etc.)
    """
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no está disponible"
            )
        
        html_content = await supabase_storage.read_html_chart(chart_name)
        
        logger.info(f"Gráfico {chart_name} servido directamente desde Supabase Storage")
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error al obtener gráfico desde Supabase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/charts/signed-url/{chart_name}")
async def get_chart_signed_url(chart_name: str, expires_in: int = 3600):
    """
    Genera una URL firmada para acceso directo a un gráfico HTML en Supabase Storage
    
    Args:
        chart_name: Nombre del gráfico
        expires_in: Tiempo de expiración en segundos
    """
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no está disponible"
            )
        
        signed_url = supabase_storage.create_chart_signed_url(chart_name, expires_in)
        
        return {
            "status": "success",
            "signed_url": signed_url,
            "chart_name": chart_name,
            "expires_in": expires_in,
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al generar URL firmada para gráfico: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/charts/list")
async def list_available_charts():
    """
    Lista todos los gráficos HTML disponibles en Supabase Storage
    """
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no está disponible"
            )
        
        charts = supabase_storage.list_chart_files()
        
        return {
            "status": "success",
            "source": "supabase_storage",
            "charts": charts,
            "total_charts": len(charts),
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al listar gráficos en Supabase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
