import logging
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from services.home_data_service import get_home_dashboard_data
from services.heroku_service import heroku_service
from services.supabase_storage import get_supabase_storage
from auth.dependencies import get_current_user
from db_models.models import User
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/home", tags=["Home"])


@router.get("/dashboard")
async def get_home_dashboard(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene los datos del dashboard de inicio para el usuario autenticado.
    
    Si no existen datos (usuario nuevo), dispara la ejecución bajo demanda
    de los microservicios en Heroku y retorna un estado de 'building'.
    """
    user_id = str(current_user.user_id)
    try:
        # Usar el ID del usuario autenticado para obtener sus datos personalizados
        return get_home_dashboard_data(user_id)
    except FileNotFoundError as fnf:
        logger.info("Datos de inicio no encontrados para usuario %s (usuario nuevo). Detalle: %s", user_id, fnf)
        
        # Verificar si Heroku on-demand está habilitado y configurado
        if heroku_service.enabled and heroku_service.api_key:
            logger.info("Heroku on-demand habilitado. Disparando setup para usuario %s", user_id)
            background_tasks.add_task(heroku_service.trigger_on_demand_setup, user_id)
            
            return JSONResponse(
                status_code=202,
                content={
                    "status": "building",
                    "message": "Estamos preparando tu portafolio y analizando el mercado. Esto puede tomar unos minutos.",
                    "steps": [
                        "Generando análisis de mercado...",
                        "Construyendo portafolio inicial...",
                        "Finalizando configuración..."
                    ],
                    "user_id": user_id
                }
            )
        else:
            # Heroku no está configurado - crear datos de demo para el usuario
            logger.warning("Heroku on-demand NO está configurado. Creando datos de demo para usuario %s", user_id)
            
            try:
                # Crear datos de demo
                demo_data = create_demo_portfolio_news(user_id)
                
                # Guardar en Supabase
                storage = get_supabase_storage(settings)
                if storage:
                    storage.save_portfolio_report_json_custom(user_id, demo_data, "portfolio_news.json")
                    logger.info("Datos de demo creados para usuario %s", user_id)
                    
                    # Ahora intentar devolver los datos
                    return get_home_dashboard_data(user_id)
                else:
                    logger.error("No se pudo conectar a Supabase para guardar datos de demo")
            except Exception as demo_error:
                logger.error("Error creando datos de demo: %s", demo_error)
            
            # Si todo falla, devolver estado building de todas formas
            return JSONResponse(
                status_code=202,
                content={
                    "status": "building",
                    "message": "Tu portafolio está siendo configurado. Por favor, contacta al soporte si esto toma más de 5 minutos.",
                    "steps": [
                        "Configurando tu cuenta...",
                        "Esperando datos iniciales..."
                    ],
                    "user_id": user_id,
                    "needs_manual_setup": True
                }
            )
    except Exception as exc:  # pragma: no cover - errores inesperados
        error_msg = str(exc).lower()
        # Verificar si es un error que indica datos faltantes
        if "not found" in error_msg or "no existe" in error_msg or "vacío" in error_msg:
            logger.info("Posible usuario nuevo detectado por error: %s.", exc)
            
            if heroku_service.enabled and heroku_service.api_key:
                background_tasks.add_task(heroku_service.trigger_on_demand_setup, user_id)
            
            return JSONResponse(
                status_code=202,
                content={
                    "status": "building",
                    "message": "Estamos preparando tu portafolio y analizando el mercado. Esto puede tomar unos minutos.",
                    "steps": [
                        "Generando análisis de mercado...",
                        "Construyendo portafolio inicial...",
                        "Finalizando configuración..."
                    ],
                    "user_id": user_id
                }
            )
        logger.exception("Error al obtener datos para la sección de inicio del usuario %s", user_id)
        raise HTTPException(status_code=500, detail="Error al obtener datos de inicio") from exc


def create_demo_portfolio_news(user_id: str) -> dict:
    """Crea datos de demo para un usuario nuevo."""
    now = datetime.now(timezone.utc).isoformat()
    
    return {
        "generated_at": now,
        "user_id": user_id,
        "is_demo": True,
        "market_sentiment": {
            "value": 55,
            "description": "Neutral - Datos de demostración"
        },
        "portfolio_news": [
            {
                "uuid": "demo-1",
                "title": "Bienvenido a Horizon",
                "subtitle": "Tu portafolio financiero inteligente",
                "summary": "Este es un contenido de demostración. Tus datos personalizados se generarán pronto.",
                "source": "Horizon",
                "url": "#",
                "image": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=800&q=80",
                "published_at": now,
                "type": "welcome"
            },
            {
                "uuid": "demo-2", 
                "title": "Configurando tu portafolio",
                "subtitle": "Análisis en progreso",
                "summary": "Estamos analizando las tendencias del mercado para personalizar tu experiencia.",
                "source": "Horizon AI",
                "url": "#",
                "image": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=80",
                "published_at": now,
                "type": "info"
            }
        ],
        "tradingview_ideas": [
            {
                "id": "tv-demo-1",
                "title": "Análisis de Mercado - Demo",
                "author": "Horizon Analytics",
                "source": "TradingView",
                "ticker": "SPY",
                "category": "Análisis Técnico",
                "published_at": now,
                "image_url": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=800&q=80"
            }
        ]
    }

