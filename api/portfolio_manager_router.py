"""Endpoints modernos para exponer el Portfolio Manager dentro del backend."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from config import settings
from services.portfolio_manager_service import portfolio_runtime

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
    period: Optional[str] = Query(None, description="Periodo histórico a analizar"),
    refresh: bool = Query(False, description="Forzar regeneración del reporte"),
):
    """Devuelve el reporte completo del portafolio con caché y refresco opcional."""
    data = await portfolio_runtime.get_report(period=period, force_refresh=refresh)
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
async def get_portfolio_summary():
    """Resumen rápido del portafolio."""
    summary_data = await portfolio_runtime.get_summary()
    if summary_data.get("enabled") is False:
        return JSONResponse(status_code=200, content=summary_data)

    if not summary_data.get("summary"):
        raise HTTPException(status_code=503, detail="No se pudo obtener el resumen del portafolio")

    # Asegurarse de que 'generated_at' esté en la respuesta si es posible
    if "generated_at" not in summary_data:
        full_report = await portfolio_runtime.get_report(force_refresh=False)
        if full_report.get("data", {}).get("generated_at"):
            summary_data["generated_at"] = full_report["data"]["generated_at"]

    return summary_data


@router.get("/market")
async def get_market_overview():
    """Información de mercado basada en la watchlist configurada."""
    market = await portfolio_runtime.get_market()
    if market.get("enabled") is False:
        return JSONResponse(status_code=200, content=market)

    if not market:
        raise HTTPException(status_code=503, detail="No se pudo obtener la información de mercado")
    return market


@router.get("/charts/{chart_name}", response_class=HTMLResponse)
async def get_chart(chart_name: str):
    """Entrega el HTML del gráfico solicitado (portfolio, allocation o símbolo concreto)."""
    html = await portfolio_runtime.get_chart(chart_name)
    if not html:
        raise HTTPException(status_code=404, detail=f"No se encontró el gráfico '{chart_name}'")
    return HTMLResponse(content=html)


@router.get("/watch")
async def poll_portfolio_updates(
    since: Optional[str] = Query(None, description="Marca de tiempo (ISO 8601) del último JSON recibido"),
    include_report: bool = Query(False, description="Incluir el reporte completo en la respuesta"),
    include_summary: bool = Query(True, description="Incluir el resumen del portafolio"),
    include_market: bool = Query(True, description="Incluir la sección de mercado"),
):
    """Permite al frontend consultar periódicamente si existe un JSON más reciente sin forzar regeneraciones."""
    payload = await portfolio_runtime.poll_portfolio(
        since=since,
        include_report=include_report,
        include_summary=include_summary,
        include_market=include_market,
    )
    return payload


@router.post("/assets")
async def add_asset(asset: AssetModel):
    """Agrega un nuevo activo al portafolio y regenera el reporte."""
    result = await portfolio_runtime.add_asset(asset.symbol, asset.units)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "No se pudo agregar el activo"))
    return result


@router.put("/assets")
async def update_portfolio(request: PortfolioUpdateRequest):
    """Sobrescribe la composición completa del portafolio."""
    assets_payload = [asset.model_dump() for asset in request.assets]
    result = await portfolio_runtime.update_portfolio(assets_payload)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "No se pudo actualizar el portafolio"))
    return result
