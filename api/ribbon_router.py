import json
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

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


router = APIRouter(prefix="/api/ribbon", tags=["Ribbon Actions"])
logger = logging.getLogger(__name__)


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


@router.get("/forecast")
async def get_forecast():
    return {
        "title": "Proyecciones Futuras",
        "message": "Proyección básica generada como prueba desde el backend."
    }


@router.get("/alerts")
async def get_alerts():
    return {
        "title": "Alertas y Oportunidades",
        "message": "Alerta de ejemplo: oportunidad detectada (mensaje de prueba)."
    }


@router.post("/custom-report")
async def trigger_portfolio_report(
    background_tasks: BackgroundTasks,
    payload: Optional[Dict[str, Any]] = None
):
    """Solicita al agente remoto la generación de un informe de portafolio."""

    normalized_payload = payload or {}

    try:
        report_response = await remote_agent_client.generate_portfolio_report(
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
                    prefix_name = getattr(settings, "SUPABASE_BASE_PREFIX_2", None) or getattr(settings, "SUPABASE_BASE_PREFIX", None)
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
                storage_result = guardar_json_en_supabase(clean_report_payload, config_obj)
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

