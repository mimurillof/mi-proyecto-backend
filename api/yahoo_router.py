"""Endpoints para búsqueda de activos usando Yahoo Finance API."""
from __future__ import annotations

import logging
from typing import Optional, List
import httpx
from fastapi import APIRouter, HTTPException, Query, Depends

from config import settings
from auth.dependencies import get_current_user
from db_models.models import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/yahoo",
    tags=["Yahoo Finance"],
)


# Constantes para la API de Yahoo Finance
YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


async def search_yahoo_finance(query: str, limit: int = 10) -> List[dict]:
    """Busca activos en Yahoo Finance."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                YAHOO_SEARCH_URL,
                params={"q": query},
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            # Formatear resultados
            quotes = data.get("quotes", [])[:limit]
            formatted_results = []
            
            for quote in quotes:
                formatted_results.append({
                    "symbol": quote.get("symbol", ""),
                    "name": quote.get("longname") or quote.get("shortname") or quote.get("symbol", ""),
                    "exchange": quote.get("exchange", "Unknown"),
                    "exchangeShortName": quote.get("exchDisp", quote.get("exchange", "Unknown")),
                    "type": quote.get("quoteType", "equity"),
                    "typeDisp": quote.get("typeDisp", ""),
                })
            
            return formatted_results
    except httpx.HTTPError as e:
        logger.error(f"Error buscando en Yahoo Finance: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado en búsqueda Yahoo Finance: {e}")
        return []


async def get_yahoo_asset_profile(symbol: str) -> Optional[dict]:
    """Obtiene el perfil detallado de un activo desde Yahoo Finance."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{YAHOO_CHART_URL}/{symbol}",
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            result = data.get("chart", {}).get("result", [])
            if not result:
                return None

            meta = result[0].get("meta", {})
            current_price = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
            previous_close = meta.get("previousClose", 0)
            change = current_price - previous_close if previous_close else 0
            change_percent = (change / previous_close * 100) if previous_close > 0 else 0

            return {
                "symbol": meta.get("symbol", symbol),
                "companyName": meta.get("longName") or meta.get("shortName") or symbol,
                "price": current_price,
                "previousClose": previous_close,
                "changes": round(change, 4),
                "changesPercentage": round(change_percent, 4),
                "exchange": meta.get("fullExchangeName") or meta.get("exchangeName", "Unknown"),
                "exchangeShortName": meta.get("exchangeName", "Unknown"),
                "currency": meta.get("currency", "USD"),
                "marketCap": meta.get("marketCap", 0),
                "regularMarketVolume": meta.get("regularMarketVolume", 0),
                "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh", 0),
                "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow", 0),
                "instrumentType": meta.get("instrumentType", "EQUITY"),
                "timezone": meta.get("timezone", ""),
            }
    except httpx.HTTPError as e:
        logger.error(f"Error obteniendo perfil de {symbol}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado obteniendo perfil de {symbol}: {e}")
        return None


@router.get("/search")
async def search_assets(
    query: str = Query(..., min_length=1, description="Término de búsqueda (símbolo o nombre)"),
    limit: int = Query(10, ge=1, le=20, description="Número máximo de resultados"),
    current_user: User = Depends(get_current_user),
):
    """
    Busca activos financieros por símbolo o nombre usando Yahoo Finance.
    
    - **query**: Texto de búsqueda (mínimo 1 carácter)
    - **limit**: Número máximo de resultados (1-20, default: 10)
    
    Retorna una lista de activos coincidentes con símbolo, nombre e información del exchange.
    """
    logger.info(f"🔍 [YAHOO-SEARCH] Buscando '{query}' para user_id={current_user.user_id}")
    
    results = await search_yahoo_finance(query.strip(), limit)
    
    logger.info(f"✅ [YAHOO-SEARCH] Encontrados {len(results)} resultados para '{query}'")
    
    return {
        "success": True,
        "data": results,
        "count": len(results),
        "query": query,
    }


@router.get("/profile/{symbol}")
async def get_asset_profile(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene el perfil detallado de un activo financiero.
    
    - **symbol**: Símbolo del activo (ej: AAPL, MSFT, BTC-USD)
    
    Retorna información detallada incluyendo precio actual, cambios, volumen, etc.
    """
    logger.info(f"📊 [YAHOO-PROFILE] Obteniendo perfil de '{symbol}' para user_id={current_user.user_id}")
    
    profile = await get_yahoo_asset_profile(symbol.upper())
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró información para el símbolo '{symbol}'. Verifica que sea correcto."
        )
    
    logger.info(f"✅ [YAHOO-PROFILE] Perfil obtenido para '{symbol}'")
    
    return {
        "success": True,
        "data": profile,
    }
