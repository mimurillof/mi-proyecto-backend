import logging

from fastapi import APIRouter, HTTPException

from services.home_data_service import get_home_dashboard_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/home", tags=["Home"])


@router.get("/dashboard")
async def get_home_dashboard():
    try:
        return get_home_dashboard_data()
    except FileNotFoundError as exc:
        logger.error("No se encontró el archivo de noticias del portafolio: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - errores inesperados
        logger.exception("Error al obtener datos para la sección de inicio")
        raise HTTPException(status_code=500, detail="Error al obtener datos de inicio") from exc
