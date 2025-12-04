import logging

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from services.home_data_service import get_home_dashboard_data
from services.heroku_service import heroku_service
from auth.dependencies import get_current_user
from db_models.models import User

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
    except FileNotFoundError:
        logger.info("Datos de inicio no encontrados para usuario %s. Iniciando setup bajo demanda.", user_id)
        
        # Disparar la generación de datos en background (o await si queremos asegurar el trigger)
        # Usamos await aquí para asegurar que el trigger se envíe antes de responder, 
        # aunque la ejecución en Heroku es asíncrona por naturaleza.
        # Si preferimos que sea totalmente background para no bloquear la respuesta HTTP:
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
                ]
            }
        )
    except Exception as exc:  # pragma: no cover - errores inesperados
        logger.exception("Error al obtener datos para la sección de inicio del usuario %s", user_id)
        raise HTTPException(status_code=500, detail="Error al obtener datos de inicio") from exc

