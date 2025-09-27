from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException

from services.remote_agent_client import remote_agent_client


router = APIRouter(prefix="/api/ribbon", tags=["Ribbon Actions"])


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

        return report_response
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error solicitando informe al agente remoto: {exc}"
        ) from exc

