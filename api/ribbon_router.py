from fastapi import APIRouter


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


@router.get("/custom-report")
async def get_custom_report_preview():
    return {
        "title": "Reporte Personalizado",
        "message": "Tu reporte personalizado ha sido generado (demo) y se mostrará aquí como texto desde el backend.",
        "report_id": "demo-123"
    }


