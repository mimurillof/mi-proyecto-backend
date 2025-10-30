"""
Router para el dashboard de alertas y oportunidades
Procesa los JSONs de análisis desde Supabase y genera tarjetas de alerta para el frontend
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends

from auth.dependencies import get_current_user
from db_models.models import User
from services.alert_mapper import process_alert_to_card

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# Importar servicio de Supabase Storage
try:
    from services.supabase_storage import get_supabase_storage
    from config import settings
    
    supabase_storage = get_supabase_storage(settings)
    SUPABASE_ENABLED = supabase_storage is not None
    
    if SUPABASE_ENABLED:
        logger.info("Servicio de Supabase Storage habilitado para dashboard")
    else:
        logger.warning("Servicio de Supabase Storage no se pudo inicializar para dashboard")
        
except Exception as e:
    SUPABASE_ENABLED = False
    logger.warning(f"Servicio de Supabase Storage deshabilitado para dashboard: {e}")
    supabase_storage = None


async def load_analysis_json(user_id: str, filename: str) -> Optional[Dict[str, Any]]:
    """
    Carga un archivo JSON de análisis desde Supabase Storage.
    
    Args:
        user_id: ID del usuario
        filename: Nombre del archivo JSON
        
    Returns:
        Dict con los datos del JSON o None si no existe
    """
    if not SUPABASE_ENABLED or not supabase_storage:
        logger.warning(f"Supabase no disponible, no se puede cargar {filename}")
        return None
    
    try:
        # Usar read_report_json para leer archivos JSON del usuario
        data = supabase_storage.read_report_json(user_id, filename)
        logger.info(f"Archivo {filename} cargado exitosamente para usuario {user_id}")
        return data
    except Exception as e:
        logger.warning(f"No se pudo cargar {filename} desde Supabase para usuario {user_id}: {e}")
        return None


def process_portfolio_alerts(portfolio_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Procesa las alertas del JSON de portfolio_analisis.
    
    Args:
        portfolio_data: Dict con los datos del portfolio_analisis.json
        
    Returns:
        Lista de tarjetas de alerta procesadas
    """
    cards = []
    
    if not portfolio_data or "portfolio" not in portfolio_data:
        return cards
    
    assets = portfolio_data.get("portfolio", {}).get("assets", {})
    
    for ticker, data in assets.items():
        if "signals" in data and "alerts" in data["signals"]:
            for alert in data["signals"]["alerts"]:
                alert_type = alert.get("type")
                
                # Ignorar alertas sin señal
                if alert_type == "SIN_SEÑALES":
                    continue
                
                description = alert.get("description", "")
                priority = alert.get("priority", "LOW")
                
                card = process_alert_to_card(
                    alert_type=alert_type,
                    description=description,
                    ticker=ticker,
                    priority=priority
                )
                cards.append(card)
    
    return cards


def process_market_alerts(market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Procesa las alertas del JSON de mercado_analisis.
    
    Args:
        market_data: Dict con los datos del mercado_analisis.json
        
    Returns:
        Lista de tarjetas de alerta procesadas
    """
    cards = []
    
    if not market_data or "market" not in market_data:
        return cards
    
    assets = market_data.get("market", {}).get("assets", {})
    
    for ticker, data in assets.items():
        if "signals" in data and "alerts" in data["signals"]:
            for alert in data["signals"]["alerts"]:
                alert_type = alert.get("type")
                
                # Ignorar alertas sin señal
                if alert_type == "SIN_SEÑALES":
                    continue
                
                description = alert.get("description", "")
                priority = alert.get("priority", "LOW")
                
                card = process_alert_to_card(
                    alert_type=alert_type,
                    description=description,
                    ticker=ticker,
                    priority=priority
                )
                cards.append(card)
    
    return cards


@router.get("/alerts")
async def get_dashboard_alerts(current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    Obtiene todas las alertas y oportunidades del dashboard procesadas desde Supabase.
    
    Lee los archivos portfolio_analisis.json y mercado_analisis.json desde Supabase Storage,
    procesa las alertas usando el mapeador y devuelve una lista de tarjetas listas para
    renderizar en el frontend.
    
    Requiere autenticación mediante token JWT.
    
    Returns:
        Lista de tarjetas de alerta con estructura:
        [
            {
                "id": "NVDA-SOBRECOMPRA",
                "title": "Alerta: Sobrecompra",
                "description": "**NVDA:** El activo ha entrado en zona de sobrecompra...",
                "color_theme": "warning",
                "icon": "⬆️",
                "priority": "MEDIUM"
            },
            ...
        ]
    """
    user_id = str(current_user.user_id)
    
    try:
        # 1. Cargar los JSONs desde Supabase
        portfolio_data = await load_analysis_json(user_id, "portfolio_analisis.json")
        market_data = await load_analysis_json(user_id, "mercado_analisis.json")
        
        all_cards = []
        
        # 2. Procesar alertas del portfolio
        if portfolio_data:
            portfolio_cards = process_portfolio_alerts(portfolio_data)
            all_cards.extend(portfolio_cards)
            logger.info(f"Procesadas {len(portfolio_cards)} alertas del portfolio para usuario {user_id}")
        
        # 3. Procesar alertas del mercado
        if market_data:
            market_cards = process_market_alerts(market_data)
            all_cards.extend(market_cards)
            logger.info(f"Procesadas {len(market_cards)} alertas del mercado para usuario {user_id}")
        
        # 4. Eliminar duplicados por ID (puede haber activos en ambos JSONs)
        unique_cards = {}
        for card in all_cards:
            card_id = card["id"]
            # Si ya existe, mantener el de mayor prioridad
            if card_id not in unique_cards:
                unique_cards[card_id] = card
            else:
                priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
                current_priority = priority_order.get(card["priority"], 3)
                existing_priority = priority_order.get(unique_cards[card_id]["priority"], 3)
                if current_priority < existing_priority:
                    unique_cards[card_id] = card
        
        # 5. Ordenar por prioridad (HIGH -> MEDIUM -> LOW)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_cards = sorted(
            unique_cards.values(),
            key=lambda x: priority_order.get(x["priority"], 3)
        )
        
        logger.info(f"Devolviendo {len(sorted_cards)} alertas únicas para usuario {user_id}")
        return sorted_cards
        
    except Exception as e:
        logger.error(f"Error al procesar alertas del dashboard para usuario {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener alertas del dashboard: {str(e)}"
        )

