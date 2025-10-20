"""Endpoints modernos para exponer el Portfolio Manager dentro del backend."""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from config import settings
from services.portfolio_manager_service import get_portfolio_manager_client
from auth.dependencies import get_current_user, get_current_user_from_header_or_query
from db_models.models import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/portfolio-manager",
    tags=["Portfolio Manager"],
)


class AssetModel(BaseModel):
    symbol: str = Field(..., description="Ticker del activo")
    units: int = Field(..., gt=0, description="Cantidad de unidades")
    name: Optional[str] = Field(None, description="Nombre descriptivo opcional")


class PortfolioUpdateRequest(BaseModel):
    assets: List[AssetModel]


@router.get("/report")
async def get_portfolio_report(
    current_user: User = Depends(get_current_user),
    period: Optional[str] = Query(None, description="Periodo histÃ³rico a analizar"),
    refresh: bool = Query(False, description="Forzar regeneraciÃ³n del reporte"),
):
    """Devuelve el reporte completo del portafolio del usuario autenticado con cachÃ© y refresco opcional."""
    user_id = str(current_user.user_id)
    logger.info("Solicitando reporte de portfolio para user_id=%s, period=%s, refresh=%s", user_id, period, refresh)
    
    client = get_portfolio_manager_client(user_id)
    data = await client.get_report(period=period, force_refresh=refresh)
    if not data.get("enabled", True):
        return JSONResponse(status_code=200, content=data)

    if data.get("status") == "skipped":
        return data

    if not data.get("data"):
        return JSONResponse(
            status_code=200,
            content={
                **data,
                "status": data.get("status", "unavailable"),
                "message": data.get(
                    "message",
                    "No hay datos disponibles del portafolio en este momento",
                ),
            },
        )

    return data


@router.get("/summary")
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
):
    """Resumen rÃ¡pido del portafolio del usuario autenticado."""
    user_id = str(current_user.user_id)
    logger.info("Solicitando resumen de portfolio para user_id=%s", user_id)
    
    client = get_portfolio_manager_client(user_id)
    summary_data = await client.get_summary()
    if summary_data.get("enabled") is False:
        return JSONResponse(status_code=200, content=summary_data)

    if not summary_data.get("summary"):
        raise HTTPException(status_code=503, detail="No se pudo obtener el resumen del portafolio")

    # Asegurarse de que 'generated_at' estÃ© en la respuesta si es posible
    if "generated_at" not in summary_data:
        full_report = await client.get_report(force_refresh=False)
        if full_report.get("data", {}).get("generated_at"):
            summary_data["generated_at"] = full_report["data"]["generated_at"]

    return summary_data


@router.get("/market")
async def get_market_overview(
    current_user: User = Depends(get_current_user),
):
    """InformaciÃ³n de mercado basada en la watchlist configurada del usuario autenticado."""
    user_id = str(current_user.user_id)
    logger.info("Solicitando watchlist de mercado para user_id=%s", user_id)
    
    client = get_portfolio_manager_client(user_id)
    market = await client.get_market()
    if market.get("enabled") is False:
        return JSONResponse(status_code=200, content=market)

    if not market:
        raise HTTPException(status_code=503, detail="No se pudo obtener la informaciÃ³n de mercado")
    return market


@router.get("/charts/{chart_name}", response_class=HTMLResponse)
async def get_chart(
    chart_name: str,
    current_user: User = Depends(get_current_user_from_header_or_query),
):
    """Entrega el HTML del grÃ¡fico solicitado del usuario autenticado (portfolio, allocation o sÃ­mbolo concreto)."""
    user_id = str(current_user.user_id)
    logger.info("Solicitando grÃ¡fico '%s' para user_id=%s", chart_name, user_id)
    
    client = get_portfolio_manager_client(user_id)
    html = await client.get_chart(chart_name)
    if not html:
        raise HTTPException(status_code=404, detail=f"No se encontrÃ³ el grÃ¡fico '{chart_name}'")
    return HTMLResponse(content=html)


@router.get("/watch")
async def poll_portfolio_updates(
    current_user: User = Depends(get_current_user),
    since: Optional[str] = Query(None, description="Marca de tiempo (ISO 8601) del Ãºltimo JSON recibido"),
    include_report: bool = Query(False, description="Incluir el reporte completo en la respuesta"),
    include_summary: bool = Query(True, description="Incluir el resumen del portafolio"),
    include_market: bool = Query(True, description="Incluir la secciÃ³n de mercado"),
):
    """Permite al frontend consultar periÃ³dicamente si existe un JSON mÃ¡s reciente del usuario sin forzar regeneraciones."""
    user_id = str(current_user.user_id)
    
    client = get_portfolio_manager_client(user_id)
    payload = await client.poll_portfolio(
        since=since,
        include_report=include_report,
        include_summary=include_summary,
        include_market=include_market,
    )
    return payload


@router.post("/assets")
async def add_asset(
    asset: AssetModel,
    current_user: User = Depends(get_current_user),
):
    """Agrega un nuevo activo al portafolio del usuario autenticado y regenera el reporte."""
    user_id = str(current_user.user_id)
    logger.info("Agregando activo '%s' para user_id=%s", asset.symbol, user_id)
    
    client = get_portfolio_manager_client(user_id)
    result = await client.add_asset(asset.symbol, asset.units)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "No se pudo agregar el activo"))
    return result


@router.put("/assets")
async def update_portfolio(
    request: PortfolioUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Sobrescribe la composiciÃ³n completa del portafolio del usuario autenticado."""
    user_id = str(current_user.user_id)
    logger.info("Actualizando portfolio completo para user_id=%s", user_id)
    
    client = get_portfolio_manager_client(user_id)
    assets_payload = [asset.model_dump() for asset in request.assets]
    result = await client.update_portfolio(assets_payload)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "No se pudo actualizar el portafolio"))
    return result

