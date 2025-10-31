import json
import logging
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Request

try:
    from config import settings  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    settings = None  # type: ignore[assignment]

from services.pdf_generation import trigger_pdf_generation_task
from services.remote_agent_client import remote_agent_client
from services.supabase_storage import guardar_json_en_supabase
from services.report_normalizer import (
    normalize_report_for_schema,
    ensure_image_sources,
    ReportValidationError,
)
from auth.dependencies import get_current_user  # ✅ Importar dependencia de autenticación
from db_models.models import User  # ✅ Importar modelo de Usuario


router = APIRouter(prefix="/api/ribbon", tags=["Ribbon Actions"])
logger = logging.getLogger(__name__)

# Almacenamiento en memoria para estados de reportes
# Con 1 worker, todos los requests comparten la misma memoria
report_statuses: Dict[str, Dict[str, Any]] = {}


@router.get("/summary")
async def get_summary():
    return {
        "title": "Resumen Diario/Semanal",
        "message": "Este es un mensaje de prueba desde el backend para el resumen."
    }


@router.get("/performance")
async def get_performance():
    return {
        "title": "Análisis de Rendimiento",
        "message": "Mensaje de prueba de rendimiento enviado por el backend."
    }


@router.post("/projections/start")
async def start_projections_analysis(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Inicia el análisis asíncrono de proyecciones futuras.
    Retorna inmediatamente con un task_id para hacer polling.
    """
    user_id = str(current_user.user_id)
    
    # Obtener token del header Authorization
    auth_token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        auth_token = auth_header.split(" ", 1)[1]
    
    try:
        # Llamar al agente remoto
        result = await remote_agent_client.start_future_projections(
            user_id=user_id,
            auth_token=auth_token,
            model_preference="flash"
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Error iniciando proyecciones: {result.get('error')}"
            )
        
        task_id = result.get("task_id")
        if not task_id:
            raise HTTPException(
                status_code=500,
                detail="No se recibió task_id del servicio de agente"
            )
        
        logger.info(f"✅ Proyecciones futuras iniciadas para user={user_id}, task_id={task_id}")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Análisis de proyecciones iniciado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error iniciando proyecciones: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/projections/status/{task_id}")
async def get_projections_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Consulta el estado del análisis de proyecciones futuras.
    """
    try:
        result = await remote_agent_client.get_future_projections_status(task_id)
        
        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error consultando estado de proyecciones: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/forecast")
async def get_forecast():
    return {
        "title": "Proyecciones Futuras",
        "message": "Proyección básica generada como prueba desde el backend."
    }


@router.post("/alerts/start")
async def start_alerts_analysis(
    request: Request,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Inicia el análisis asíncrono de alertas y oportunidades.
    Retorna inmediatamente con un report_id para hacer polling.
    """
    user_id = str(current_user.user_id)
    
    # Obtener token del header Authorization
    auth_token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        auth_token = auth_header.split(" ", 1)[1]
    
    # Generar ID único para el reporte
    report_id = str(uuid.uuid4())
    
    # Crear estado inicial
    report_statuses[report_id] = {
        "report_id": report_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    
    # Iniciar procesamiento en background (llamada al agente)
    background_tasks.add_task(
        process_alerts_analysis,
        report_id,
        user_id,
        auth_token
    )
    
    return {
        "report_id": report_id,
        "status": "pending",
        "message": "Análisis de alertas iniciado. Use el endpoint /api/ribbon/alerts/status/{report_id} para verificar el progreso.",
        "poll_url": f"/api/ribbon/alerts/status/{report_id}",
        "created_at": report_statuses[report_id]["created_at"]
    }


async def process_alerts_analysis(
    report_id: str,
    user_id: str,
    auth_token: Optional[str] = None
):
    """
    Función auxiliar que procesa el análisis de alertas en background.
    Actualiza el estado en report_statuses.
    """
    try:
        # Actualizar estado a "processing"
        report_statuses[report_id]["status"] = "processing"
        report_statuses[report_id]["updated_at"] = datetime.now().isoformat()
        
        # Iniciar análisis con el agente remoto
        start_response = await remote_agent_client.start_alerts_analysis(
            user_id=user_id,
            auth_token=auth_token,
            model_preference="pro",  # Usar modelo Pro para análisis profundo
        )
        
        task_id = start_response.get("task_id")
        if not task_id:
            raise Exception("No se recibió task_id del chat agent")
        
        # Hacer polling hasta que complete
        max_attempts = 60  # 60 intentos * 3 segundos = 3 minutos máximo
        for attempt in range(max_attempts):
            await asyncio.sleep(3)  # Esperar 3 segundos entre polls
            
            try:
                status_response = await remote_agent_client.get_alerts_analysis_status(task_id)
                
                status = status_response.get("status")
                
                if status == "completed":
                    # Análisis completado exitosamente
                    result = status_response.get("result", {})
                    report_statuses[report_id]["status"] = "completed"
                    report_statuses[report_id]["result"] = result
                    report_statuses[report_id]["updated_at"] = datetime.now().isoformat()
                    report_statuses[report_id]["completed_at"] = datetime.now().isoformat()
                    return
                
                elif status == "error":
                    # Error en el análisis
                    error_msg = status_response.get("error", "Error desconocido")
                    report_statuses[report_id]["status"] = "error"
                    report_statuses[report_id]["error"] = error_msg
                    report_statuses[report_id]["updated_at"] = datetime.now().isoformat()
                    return
                
                # Si está en "pending" o "processing", continuar polling
                
            except Exception as e:
                # Si falla el polling, continuar intentando
                if attempt == max_attempts - 1:
                    report_statuses[report_id]["status"] = "error"
                    report_statuses[report_id]["error"] = f"Timeout esperando resultado: {str(e)}"
                    report_statuses[report_id]["updated_at"] = datetime.now().isoformat()
                    return
        
        # Timeout después de todos los intentos
        report_statuses[report_id]["status"] = "error"
        report_statuses[report_id]["error"] = "Timeout: el análisis no se completó en el tiempo esperado"
        report_statuses[report_id]["updated_at"] = datetime.now().isoformat()
    
    except Exception as e:
        # Error inesperado
        report_statuses[report_id]["status"] = "error"
        report_statuses[report_id]["error"] = str(e)
        report_statuses[report_id]["updated_at"] = datetime.now().isoformat()


@router.get("/alerts/status/{report_id}")
async def get_alerts_analysis_status(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el estado actual de un análisis de alertas.
    Estados posibles: pending, processing, completed, error
    """
    if report_id not in report_statuses:
        raise HTTPException(
            status_code=404,
            detail=f"Análisis con ID {report_id} no encontrado"
        )
    
    status_info = report_statuses[report_id]
    
    # Respuesta básica para todos los estados
    response = {
        "report_id": status_info["report_id"],
        "status": status_info["status"],
        "created_at": status_info["created_at"],
        "updated_at": status_info["updated_at"],
    }
    
    # Agregar información específica según el estado
    if status_info["status"] == "completed":
        result = status_info.get("result", {})
        response["analysis"] = result.get("analysis", "")
        response["model_used"] = result.get("model_used", "")
        response["completed_at"] = status_info.get("completed_at")
    elif status_info["status"] == "error":
        response["error"] = status_info.get("error")
    elif status_info["status"] in ["pending", "processing"]:
        response["message"] = "Análisis en proceso. Vuelva a consultar en unos segundos."
    
    return response


@router.get("/alerts")
async def get_alerts():
    """
    Endpoint legacy - ahora se usa /alerts/start para iniciar el análisis
    """
    return {
        "title": "Alertas y Oportunidades",
        "message": "Use el endpoint POST /api/ribbon/alerts/start para iniciar el análisis."
    }


async def process_report_generation(
    report_id: str,
    user_id: str,  # ✅ NUEVO: Requerido para multiusuario
    model_preference: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
):
    """
    Función auxiliar que procesa la generación del reporte en background.
    Actualiza el estado en report_statuses (memoria compartida con 1 worker).
    """
    try:
        # Actualizar estado a "processing"
        report_statuses[report_id]["status"] = "processing"
        report_statuses[report_id]["updated_at"] = datetime.now().isoformat()
        
        # Generar reporte con el agente remoto
        # Ahora usa procesamiento asíncrono, puede usar Gemini Pro sin timeout
        report_response = await remote_agent_client.generate_portfolio_report(
            user_id=user_id,  # ✅ Pasar user_id al agente
            model_preference=model_preference,  # Usará Gemini Pro si no se especifica
            context=context,
            session_id=session_id,
        )

        storage_result: Dict[str, Any]
        clean_report_payload: Optional[Dict[str, Any]] = None

        if isinstance(report_response, dict):
            raw_report = report_response.get("report")
            if isinstance(raw_report, dict):
                try:
                    normalized_report = normalize_report_for_schema(raw_report)
                    bucket_name = getattr(settings, "SUPABASE_BUCKET_NAME", None) if settings else None
                    prefix_name = getattr(settings, "SUPABASE_BASE_PREFIX", None) if settings else None
                    normalized_report = ensure_image_sources(
                        normalized_report,
                        bucket=bucket_name,
                        prefix=prefix_name,
                        transform_width=800,
                    )
                    clean_report_payload = json.loads(json.dumps(normalized_report, ensure_ascii=False))
                except ReportValidationError as exc:
                    logger.error("El informe del agente no cumple el esquema esperado: %s", exc)
                    clean_report_payload = None
                except (TypeError, ValueError):
                    logger.exception("No se pudo serializar el informe normalizado para generación de PDF")
                    clean_report_payload = None
            else:
                logger.error("La respuesta del agente no contiene un objeto 'report' válido")
        else:
            logger.error("Respuesta inesperada del agente remoto: tipo %s", type(report_response))

        enable_upload = bool(getattr(settings, "ENABLE_SUPABASE_UPLOAD", False))

        if enable_upload:
            config_obj = settings if settings is not None else None
            if clean_report_payload is not None:
                storage_result = guardar_json_en_supabase(user_id, clean_report_payload, config_obj)  # ✅ MULTIUSUARIO
            else:
                storage_result = {
                    "status": "error",
                    "message": "No se pudo extraer el informe para guardarlo en Supabase.",
                }

            if storage_result.get("status") == "success":
                logger.info(
                    "Informe estratégico almacenado en Supabase: %s",
                    storage_result.get("path"),
                )

                # Generar PDF en background (no bloquear)
                if clean_report_payload is not None:
                    try:
                        trigger_pdf_generation_task(
                            clean_report_payload,
                            storage_result.get("path"),
                            config=settings if settings is not None else None,
                            user_id=user_id  # ✅ MULTIUSUARIO: Pasar user_id al generador de PDF
                        )
                    except Exception as pdf_error:
                        logger.error(f"Error generando PDF: {pdf_error}")
            else:
                logger.error(
                    "Error al almacenar informe en Supabase: %s",
                    storage_result.get("message"),
                )
        else:
            storage_result = {
                "status": "skipped",
                "message": "Carga a Supabase deshabilitada por configuración",
            }

        # Preparar respuesta final
        if isinstance(report_response, dict):
            response_copy = json.loads(json.dumps(report_response, ensure_ascii=False))
            if clean_report_payload is not None:
                response_copy["report"] = clean_report_payload
            response_copy["storage_result"] = storage_result
            final_response = response_copy
        else:
            final_response = {
                "report": report_response,
                "storage_result": storage_result,
            }

        # Actualizar estado a "completed"
        report_statuses[report_id]["status"] = "completed"
        report_statuses[report_id]["result"] = final_response
        report_statuses[report_id]["updated_at"] = datetime.now().isoformat()
        report_statuses[report_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Reporte {report_id} generado exitosamente")

    except Exception as exc:
        # Actualizar estado a "error"
        report_statuses[report_id]["status"] = "error"
        report_statuses[report_id]["error"] = str(exc)
        report_statuses[report_id]["updated_at"] = datetime.now().isoformat()
        logger.error(f"Error generando reporte {report_id}: {exc}")


@router.post("/custom-report/start")
async def start_portfolio_report(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),  # ✅ Requerir autenticación
    payload: Optional[Dict[str, Any]] = None
):
    """
    Inicia la generación asíncrona de un informe de portafolio.
    Retorna inmediatamente con un report_id para hacer polling.
    Requiere autenticación - el agente accederá solo a los archivos del usuario.
    """
    user_id = str(current_user.user_id)  # ✅ Obtener user_id del usuario autenticado
    normalized_payload = payload or {}
    
    # Generar ID único para el reporte
    report_id = str(uuid.uuid4())
    
    # Crear estado inicial
    report_statuses[report_id] = {
        "report_id": report_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "model_preference": normalized_payload.get("model_preference"),
    }
    
    # Iniciar procesamiento en background
    background_tasks.add_task(
        process_report_generation,
        report_id,
        user_id,  # ✅ Pasar user_id a la función de background
        normalized_payload.get("model_preference"),
        normalized_payload.get("context"),
        normalized_payload.get("session_id")
    )
    
    logger.info(f"Reporte {report_id} iniciado")
    
    return {
        "report_id": report_id,
        "status": "pending",
        "message": "Generación de reporte iniciada. Use el endpoint /api/ribbon/custom-report/status/{report_id} para verificar el progreso.",
        "poll_url": f"/api/ribbon/custom-report/status/{report_id}",
        "created_at": report_statuses[report_id]["created_at"]
    }


@router.get("/custom-report/status/{report_id}")
async def get_report_status(report_id: str):
    """
    Obtiene el estado actual de un reporte en generación.
    Estados posibles: pending, processing, completed, error
    """
    if report_id not in report_statuses:
        raise HTTPException(
            status_code=404,
            detail=f"Reporte con ID {report_id} no encontrado"
        )
    
    status_info = report_statuses[report_id]
    
    # Respuesta básica para todos los estados
    response = {
        "report_id": status_info["report_id"],
        "status": status_info["status"],
        "created_at": status_info["created_at"],
        "updated_at": status_info["updated_at"],
    }
    
    # Agregar información específica según el estado
    if status_info["status"] == "completed":
        response["result"] = status_info.get("result")
        response["completed_at"] = status_info.get("completed_at")
    elif status_info["status"] == "error":
        response["error"] = status_info.get("error")
    elif status_info["status"] in ["pending", "processing"]:
        response["message"] = "Reporte en proceso de generación. Vuelva a consultar en unos segundos."
    
    return response


@router.post("/custom-report")
async def trigger_portfolio_report(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),  # ✅ Requerir autenticación
    payload: Optional[Dict[str, Any]] = None
):
    """
    Solicita al agente remoto la generación de un informe de portafolio.
    Requiere autenticación - el agente accederá solo a los archivos del usuario.
    """
    user_id = str(current_user.user_id)  # ✅ Obtener user_id del usuario autenticado
    normalized_payload = payload or {}

    try:
        report_response = await remote_agent_client.generate_portfolio_report(
            user_id=user_id,  # ✅ Pasar user_id al agente
            model_preference=normalized_payload.get("model_preference"),
            context=normalized_payload.get("context"),
            session_id=normalized_payload.get("session_id"),
        )

        storage_result: Dict[str, Any]
        clean_report_payload: Optional[Dict[str, Any]] = None

        if isinstance(report_response, dict):
            raw_report = report_response.get("report")
            if isinstance(raw_report, dict):
                try:
                    normalized_report = normalize_report_for_schema(raw_report)
                    bucket_name = getattr(settings, "SUPABASE_BUCKET_NAME", None) if settings else None
                    prefix_name = getattr(settings, "SUPABASE_BASE_PREFIX", None) if settings else None
                    normalized_report = ensure_image_sources(
                        normalized_report,
                        bucket=bucket_name,
                        prefix=prefix_name,
                        transform_width=800,
                    )
                    clean_report_payload = json.loads(json.dumps(normalized_report, ensure_ascii=False))
                except ReportValidationError as exc:
                    logger.error("El informe del agente no cumple el esquema esperado: %s", exc)
                    clean_report_payload = None
                except (TypeError, ValueError):
                    logger.exception("No se pudo serializar el informe normalizado para generación de PDF")
                    clean_report_payload = None
            else:
                logger.error("La respuesta del agente no contiene un objeto 'report' válido")
        else:
            logger.error("Respuesta inesperada del agente remoto: tipo %s", type(report_response))

        enable_upload = bool(getattr(settings, "ENABLE_SUPABASE_UPLOAD", False))

        if enable_upload:
            config_obj = settings if settings is not None else None
            if clean_report_payload is not None:
                storage_result = guardar_json_en_supabase(user_id, clean_report_payload, config_obj)  # ✅ MULTIUSUARIO
            else:
                storage_result = {
                    "status": "error",
                    "message": "No se pudo extraer el informe para guardarlo en Supabase.",
                }

            if storage_result.get("status") == "success":
                logger.info(
                    "Informe estratégico almacenado en Supabase: %s",
                    storage_result.get("path"),
                )

                if clean_report_payload is not None:
                    background_tasks.add_task(
                        trigger_pdf_generation_task,
                        clean_report_payload,
                        storage_result.get("path"),
                        config=settings if settings is not None else None,
                        user_id=user_id  # ✅ MULTIUSUARIO: Pasar user_id al generador de PDF
                    )
            else:
                logger.error(
                    "Error al almacenar informe en Supabase: %s",
                    storage_result.get("message"),
                )
        else:
            storage_result = {
                "status": "skipped",
                "message": "Carga a Supabase deshabilitada por configuración",
            }

        if isinstance(report_response, dict):
            response_copy = json.loads(json.dumps(report_response, ensure_ascii=False))
            if clean_report_payload is not None:
                response_copy["report"] = clean_report_payload
            response_copy["storage_result"] = storage_result
            return response_copy

        return {
            "report": report_response,
            "storage_result": storage_result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error solicitando informe al agente remoto: {exc}"
        ) from exc


@router.post("/regenerate-pdf")
async def regenerate_pdf_from_existing_json(
    current_user: User = Depends(get_current_user),
):
    """
    Regenera el PDF directamente desde el estructura_informe.json existente en Supabase.
    NO llama al agente de IA, solo toma el JSON ya guardado y genera el PDF.
    Útil cuando ya existe un informe y solo se necesita regenerar el PDF.
    """
    user_id = str(current_user.user_id)
    
    try:
        # Verificar que Supabase esté habilitado
        enable_upload = bool(getattr(settings, "ENABLE_SUPABASE_UPLOAD", False))
        if not enable_upload:
            raise HTTPException(
                status_code=503,
                detail="Supabase no está configurado. No se puede regenerar el PDF."
            )
        
        # Construir la ruta esperada del JSON en Supabase
        bucket_name = getattr(settings, "SUPABASE_BUCKET_NAME", "portfolio-files")
        json_path = f"{user_id}/estructura_informe.json"
        
        logger.info(f"Intentando regenerar PDF desde {json_path} para usuario {user_id}")
        
        # El PDF Generator descargará el JSON directamente desde Supabase
        # Solo necesitamos invocar el servicio con user_id
        pdf_result = trigger_pdf_generation_task(
            report_payload={},  # Payload vacío, el generador descargará desde Supabase
            storage_path=json_path,
            config=settings if settings is not None else None,
            user_id=user_id
        )
        
        logger.info(f"PDF regenerado exitosamente para usuario {user_id}: {pdf_result}")
        
        return {
            "status": "success",
            "message": "PDF regenerado exitosamente desde el JSON existente",
            "user_id": user_id,
            "json_path": json_path,
            "pdf_result": pdf_result
        }
        
    except Exception as exc:
        logger.error(f"Error regenerando PDF para usuario {user_id}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerando PDF: {str(exc)}"
        ) from exc

