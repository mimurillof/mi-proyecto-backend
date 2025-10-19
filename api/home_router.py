import logging

from fastapi import APIRouter, HTTPException, Depends

from services.home_data_service import get_home_dashboard_data
from auth.dependencies import get_current_user
from db_models.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/home", tags=["Home"])


@router.get("/dashboard")
async def get_home_dashboard(current_user: User = Depends(get_current_user)):
    """
    Obtiene los datos del dashboard de inicio para el usuario autenticado.
    
    Requiere autenticación mediante token JWT.
    """
    try:
        # Usar el ID del usuario autenticado para obtener sus datos personalizados
        user_id = str(current_user.id)
        return get_home_dashboard_data(user_id)
    except FileNotFoundError as exc:
        logger.error("No se encontró el archivo de noticias del portafolio para usuario %s: %s", current_user.id, exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - errores inesperados
        logger.exception("Error al obtener datos para la sección de inicio del usuario %s", current_user.id)
        raise HTTPException(status_code=500, detail="Error al obtener datos de inicio") from exc
