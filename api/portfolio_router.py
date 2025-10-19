"""
Router para la integraciÃ³n con Portfolio Analyzer
Proporciona endpoints para:
- Ejecutar anÃ¡lisis usando el proveedor de datos unificado (`client_data_provider`)
- Servir mÃ©tricas y grÃ¡ficos generados por el analizador
"""

import os
import sys
import json
import glob
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, HTMLResponse
import logging
from pydantic import BaseModel

from auth.dependencies import get_current_user
from db_models.models import User

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# ConfiguraciÃ³n del directorio de outputs del Portfolio Analyzer
PORTFOLIO_OUTPUTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    "Portfolio_analizer", 
    "outputs"
)

# Asegurar que los mÃ³dulos de Portfolio_analizer/src sean importables desde este router
PORTFOLIO_ANALYZER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "Portfolio_analizer"
)
if PORTFOLIO_ANALYZER_DIR not in sys.path:
    sys.path.append(PORTFOLIO_ANALYZER_DIR)

# Importar funciones de anÃ¡lisis y formateo desde Portfolio_analizer/src
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
        f"No se pudieron importar mÃ³dulos de Portfolio_analizer/src: {e}"
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
    
    # Inicializar servicio de Supabase con configuraciÃ³n
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
    Encuentra el archivo JSON mÃ¡s reciente en el directorio de outputs
    """
    try:
        json_pattern = os.path.join(PORTFOLIO_OUTPUTS_DIR, "api_response_*.json")
        json_files = glob.glob(json_pattern)
        
        if not json_files:
            logger.warning(f"No se encontraron archivos JSON en {PORTFOLIO_OUTPUTS_DIR}")
            return None
            
        # Ordenar por fecha de modificaciÃ³n (mÃ¡s reciente primero)
        latest_file = max(json_files, key=os.path.getmtime)
        logger.info(f"Archivo JSON mÃ¡s reciente: {latest_file}")
        return latest_file
        
    except Exception as e:
        logger.error(f"Error al buscar archivos JSON: {str(e)}")
        return None

def get_latest_html_file(chart_type: str) -> Optional[str]:
    """
    Encuentra el archivo HTML mÃ¡s reciente para un tipo de grÃ¡fico especÃ­fico
    
    Args:
        chart_type: Tipo de grÃ¡fico ('cumulative_returns', 'composition_donut', etc.)
    """
    try:
        # Mapeo de nombres de grÃ¡ficos a patrones de archivo
        chart_patterns = {
            'cumulative_returns': 'rendimiento_acumulado_interactivo_*.html',
            'composition_donut': 'donut_chart_interactivo_*.html',
            'correlation_matrix': 'matriz_correlacion_interactiva_*.html',
            'drawdown_underwater': 'drawdown_underwater_interactivo_*.html',
            'breakdown_chart': 'breakdown_chart_interactivo_*.html'
        }
        
        if chart_type not in chart_patterns:
            logger.warning(f"Tipo de grÃ¡fico no reconocido: {chart_type}")
            return None
            
        html_pattern = os.path.join(PORTFOLIO_OUTPUTS_DIR, chart_patterns[chart_type])
        html_files = glob.glob(html_pattern)
        
        if not html_files:
            logger.warning(f"No se encontraron archivos HTML para {chart_type}")
            return None
            
        # Ordenar por fecha de modificaciÃ³n (mÃ¡s reciente primero)
        latest_file = max(html_files, key=os.path.getmtime)
        logger.info(f"Archivo HTML mÃ¡s reciente para {chart_type}: {latest_file}")
        return latest_file
        
    except Exception as e:
        logger.error(f"Error al buscar archivos HTML para {chart_type}: {str(e)}")
        return None


@router.get("/api/portfolio/config")
async def get_portfolio_config() -> Dict[str, Any]:
    """
    Obtiene la configuraciÃ³n del portafolio por defecto desde el proveedor unificado.
    """
    try:
        cfg = get_client_portfolio(client_id=None)  # placeholder a BD
        return {
            "status": "success",
            "config": cfg,
            "description": "ConfiguraciÃ³n del portafolio por defecto (proveedor central)",
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

        # Generar anÃ¡lisis completo en el directorio de outputs del analizador
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
            "message": "AnÃ¡lisis completado exitosamente",
            "data": api_response,
            "generated_files": list(output_files.keys()),
            "analysis_timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).error(f"Error en anÃ¡lisis por defecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/portfolio/analyze/custom")
async def analyze_custom_portfolio(request: PortfolioAnalysisRequest) -> Dict[str, Any]:
    """
    Analiza un portafolio personalizado con parÃ¡metros especÃ­ficos del usuario, usando el proveedor central.
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

        # Fechas por defecto: Ãºltimos ~2 aÃ±os si no se especifica
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
            "message": "AnÃ¡lisis personalizado completado",
            "request_parameters": request.dict(),
            "data": api_response,
            "generated_files": list(output_files.keys()),
            "analysis_timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).error(f"Error en anÃ¡lisis personalizado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/live-metrics")
async def get_live_metrics(current_user: User = Depends(get_current_user)):
    """
    Endpoint para obtener las mÃ©tricas en vivo del portfolio desde Supabase Storage
    Retorna performance_metrics y risk_analysis del archivo JSON en Supabase
    
    Requiere autenticaciÃ³n mediante token JWT.
    """
    user_id = str(current_user.user_id)
    
    try:
        # Verificar si Supabase estÃ¡ habilitado
        if not SUPABASE_ENABLED or not supabase_storage:
            # Fallback al mÃ©todo local si Supabase no estÃ¡ disponible
            return await get_live_metrics_local()
        
        # Leer mÃ©tricas desde Supabase Storage para el usuario especÃ­fico
        data = await supabase_storage.read_metrics_json(user_id, "api_response_B.json")
        
        # Extraer las secciones requeridas
        response_data = {
            "timestamp": data.get("timestamp"),
            "analysis_period": data.get("analysis_period"),
            "portfolio_composition": data.get("portfolio_composition"),
            "performance_metrics": data.get("performance_metrics", {}),
            "risk_analysis": data.get("risk_analysis", {}),
            "correlations": data.get("correlations", {}),
            "source": "supabase_storage",
            "user_id": user_id
        }
        
        logger.info("MÃ©tricas en vivo servidas exitosamente desde Supabase Storage para usuario %s", user_id)
        return response_data
        
    except Exception as e:
        logger.error(f"Error al obtener mÃ©tricas desde Supabase para usuario {user_id}: {str(e)}")
        # Intentar fallback al mÃ©todo local
        try:
            logger.info("Intentando fallback a archivos locales...")
            return await get_live_metrics_local()
        except Exception as fallback_error:
            logger.error(f"Error en fallback: {str(fallback_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error al obtener mÃ©tricas: Supabase: {str(e)}, Local: {str(fallback_error)}"
            )

async def get_live_metrics_local():
    """
    MÃ©todo de fallback para obtener mÃ©tricas desde archivos locales
    """
    try:
        latest_json = get_latest_json_file()
        
        if not latest_json:
            raise HTTPException(
                status_code=404, 
                detail="No se encontraron archivos de anÃ¡lisis de portfolio"
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
        
        logger.info("MÃ©tricas en vivo servidas exitosamente desde archivos locales")
        return response_data
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Archivo de mÃ©tricas no encontrado"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Error al decodificar el archivo de mÃ©tricas"
        )
    except Exception as e:
        logger.error(f"Error al obtener mÃ©tricas en vivo locales: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/api/portfolio/charts/{chart_name}")
async def get_portfolio_chart(chart_name: str, current_user: User = Depends(get_current_user)):
    """
    Endpoint para servir los grÃ¡ficos HTML desde Supabase Storage
    
    Args:
        chart_name: Nombre del grÃ¡fico ('cumulative_returns', 'composition_donut', etc.)
        current_user: Usuario autenticado (inyectado)
        
    Requiere autenticaciÃ³n mediante token JWT.
    """
    user_id = str(current_user.user_id)
    
    try:
        # Verificar si Supabase estÃ¡ habilitado
        if not SUPABASE_ENABLED or not supabase_storage:
            # Fallback al mÃ©todo local si Supabase no estÃ¡ disponible
            return await get_portfolio_chart_local(chart_name)
        
        # Leer grÃ¡fico HTML desde Supabase Storage para el usuario
        html_content = await supabase_storage.read_html_chart(user_id, chart_name)
        
        logger.info(f"Sirviendo grÃ¡fico: {chart_name} desde Supabase Storage para usuario {user_id}")
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error al servir grÃ¡fico desde Supabase para usuario {user_id}: {str(e)}")
        # Intentar fallback al mÃ©todo local
        try:
            logger.info(f"Intentando fallback a archivos locales para grÃ¡fico: {chart_name}")
            return await get_portfolio_chart_local(chart_name)
        except Exception as fallback_error:
            logger.error(f"Error en fallback para grÃ¡fico: {str(fallback_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error al servir grÃ¡fico: Supabase: {str(e)}, Local: {str(fallback_error)}"
            )

async def get_portfolio_chart_local(chart_name: str):
    """
    MÃ©todo de fallback para servir grÃ¡ficos desde archivos locales
    """
    try:
        latest_html = get_latest_html_file(chart_name)
        
        if not latest_html:
            raise HTTPException(
                status_code=404,
                detail=f"GrÃ¡fico '{chart_name}' no encontrado"
            )
        
        if not os.path.exists(latest_html):
            raise HTTPException(
                status_code=404,
                detail=f"Archivo de grÃ¡fico no existe: {latest_html}"
            )
        
        logger.info(f"Sirviendo grÃ¡fico: {chart_name} desde archivos locales: {latest_html}")
        
        # Leer el contenido HTML y servirlo directamente
        with open(latest_html, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al servir grÃ¡fico local {chart_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al servir grÃ¡fico local: {str(e)}"
        )

@router.get("/api/portfolio/latest-analysis-timestamp")
async def get_latest_analysis_timestamp():
    """
    Endpoint de control para obtener el timestamp del Ãºltimo anÃ¡lisis
    Utilizado por el frontend para detectar actualizaciones automÃ¡ticas
    """
    try:
        # 1) Preferir Supabase si estÃ¡ disponible
        if SUPABASE_ENABLED and supabase_storage:
            try:
                data = await supabase_storage.read_metrics_json("api_response_B.json")
                file_info = supabase_storage.get_file_info("api_response_B.json")
                return {
                    "file_modification_time": file_info.get("last_modified"),
                    "internal_timestamp": data.get("timestamp"),
                    "file_path": file_info.get("full_path"),
                    "source": "supabase_storage",
                }
            except Exception as e:
                logger.warning(f"Fallo al obtener timestamp desde Supabase, se intenta fallback local: {e}")
        
        # 2) Fallback a archivos locales si existen
        latest_json = get_latest_json_file()
        if latest_json and os.path.exists(latest_json):
            modification_time = os.path.getmtime(latest_json)
            timestamp = datetime.fromtimestamp(modification_time)
            with open(latest_json, 'r', encoding='utf-8') as file:
                data = json.load(file)
                internal_timestamp = data.get("timestamp")
            return {
                "file_modification_time": timestamp.isoformat(),
                "internal_timestamp": internal_timestamp,
                "file_path": os.path.basename(latest_json),
                "source": "local_files",
            }
        
        # 3) Si no hay datos locales y Supabase fallÃ³
        raise HTTPException(status_code=404, detail="No se encontraron anÃ¡lisis ni en Supabase ni localmente")
        
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
        # 1) Preferir estado de Supabase si estÃ¡ habilitado
        if SUPABASE_ENABLED and supabase_storage:
            status_info = supabase_storage.health_check()
            # Intentar tambiÃ©n verificar existencia del JSON y listado de grÃ¡ficos
            try:
                file_info = supabase_storage.get_file_info("api_response_B.json")
                has_recent_data = file_info is not None
            except Exception:
                has_recent_data = False
            try:
                charts = supabase_storage.list_chart_files()
            except Exception:
                charts = []
            return {
                "status": "healthy" if status_info.get("status") == "healthy" else status_info.get("status", "warning"),
                "outputs_directory_exists": os.path.exists(PORTFOLIO_OUTPUTS_DIR),
                "outputs_directory_path": PORTFOLIO_OUTPUTS_DIR,
                "has_recent_analysis": has_recent_data,
                "latest_file_age_hours": None,
                "available_charts": [c.get("chart_type") or c.get("name") for c in charts],
                "source": "supabase_storage",
            }

        # 2) Fallback al estado basado en archivos locales
        outputs_dir_exists = os.path.exists(PORTFOLIO_OUTPUTS_DIR)
        latest_json = get_latest_json_file()
        has_recent_data = latest_json is not None
        if has_recent_data and os.path.exists(latest_json):
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
                'breakdown_chart',
            ],
            "source": "local_files",
        }
        
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

# ===== NUEVOS ENDPOINTS PARA SUPABASE STORAGE =====

@router.get("/api/portfolio/signed-url/{filename}")
async def get_signed_url(filename: str, expires_in: int = 3600, current_user: User = Depends(get_current_user)):
    """
    Genera una URL firmada para acceso directo a un archivo de mÃ©tricas en Supabase Storage
    
    Args:
        filename: Nombre del archivo (ej: api_response_B.json)
        expires_in: Tiempo de expiraciÃ³n en segundos (por defecto: 1 hora)
        current_user: Usuario autenticado (inyectado)
    
    Returns:
        Dict con la URL firmada
        
    Requiere autenticaciÃ³n mediante token JWT.
    """
    user_id = str(current_user.user_id)
    
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no estÃ¡ disponible"
            )
        
        signed_url = supabase_storage.create_signed_url(user_id, filename, expires_in)
        
        return {
            "status": "success",
            "signed_url": signed_url,
            "filename": filename,
            "expires_in": expires_in,
            "created_at": datetime.now().isoformat(),
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error al generar URL firmada para usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/supabase/metrics")
async def get_supabase_metrics(filename: str = "api_response_B.json"):
    """
    Obtiene mÃ©tricas directamente desde Supabase Storage
    
    Args:
        filename: Nombre del archivo JSON (por defecto: api_response_B.json)
    """
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no estÃ¡ disponible"
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
        logger.error(f"Error al obtener mÃ©tricas desde Supabase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/supabase/files")
async def list_supabase_files(current_user: User = Depends(get_current_user)):
    """
    Lista todos los archivos de mÃ©tricas disponibles en Supabase Storage para el usuario autenticado
    
    Requiere autenticaciÃ³n mediante token JWT.
    """
    user_id = str(current_user.user_id)
    
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no estÃ¡ disponible"
            )
        
        files = supabase_storage.list_metrics_files(user_id)
        
        return {
            "status": "success",
            "source": "supabase_storage",
            "files": files,
            "total_files": len(files),
            "user_id": user_id,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al listar archivos en Supabase para usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/supabase/health")
async def supabase_health_check():
    """
    Verifica el estado de la conexiÃ³n con Supabase Storage
    """
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            return {
                "status": "disabled",
                "message": "Servicio de Supabase Storage no estÃ¡ habilitado",
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

# ===== ENDPOINTS ESPECÃFICOS PARA GRÃFICOS EN SUPABASE =====

@router.get("/api/portfolio/charts/supabase/{chart_name}")
async def get_supabase_chart_direct(chart_name: str, current_user: User = Depends(get_current_user)):
    """
    Obtiene un grÃ¡fico HTML directamente desde Supabase Storage (sin fallback)
    
    Args:
        chart_name: Nombre del grÃ¡fico ('cumulative_returns', etc.)
        current_user: Usuario autenticado (inyectado)
        
    Requiere autenticaciÃ³n mediante token JWT.
    """
    user_id = str(current_user.user_id)
    
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no estÃ¡ disponible"
            )
        
        html_content = await supabase_storage.read_html_chart(user_id, chart_name)
        
        logger.info(f"GrÃ¡fico {chart_name} servido directamente desde Supabase Storage para usuario {user_id}")
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error al obtener grÃ¡fico desde Supabase para usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/charts/signed-url/{chart_name}")
async def get_chart_signed_url(chart_name: str, expires_in: int = 3600, current_user: User = Depends(get_current_user)):
    """
    Genera una URL firmada para acceso directo a un grÃ¡fico HTML en Supabase Storage
    
    Args:
        chart_name: Nombre del grÃ¡fico
        expires_in: Tiempo de expiraciÃ³n en segundos
        current_user: Usuario autenticado (inyectado)
        
    Requiere autenticaciÃ³n mediante token JWT.
    """
    user_id = str(current_user.user_id)
    
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no estÃ¡ disponible"
            )
        
        signed_url = supabase_storage.create_chart_signed_url(user_id, chart_name, expires_in)
        
        return {
            "status": "success",
            "signed_url": signed_url,
            "chart_name": chart_name,
            "expires_in": expires_in,
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al generar URL firmada para grÃ¡fico del usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/charts/list")
async def list_available_charts(current_user: User = Depends(get_current_user)):
    """
    Lista todos los grÃ¡ficos HTML disponibles en Supabase Storage para el usuario autenticado
    
    Requiere autenticaciÃ³n mediante token JWT.
    """
    user_id = str(current_user.user_id)
    
    try:
        if not SUPABASE_ENABLED or not supabase_storage:
            raise HTTPException(
                status_code=503,
                detail="Servicio de Supabase Storage no estÃ¡ disponible"
            )
        
        charts = supabase_storage.list_chart_files(user_id)
        
        return {
            "status": "success",
            "source": "supabase_storage",
            "charts": charts,
            "total_charts": len(charts),
            "user_id": user_id,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error al listar grÃ¡ficos en Supabase para usuario {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

