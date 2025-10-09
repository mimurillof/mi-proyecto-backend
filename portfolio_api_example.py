"""
Ejemplo de integración con FastAPI Backend
Este archivo muestra cómo integrar el Portfolio Manager con FastAPI
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import sys
from pathlib import Path

# Agregar el directorio Portfolio manager al path
portfolio_manager_dir = Path(__file__).parent.parent / "Portfolio manager"
sys.path.insert(0, str(portfolio_manager_dir))

# Importar funciones del Portfolio Manager
from api_integration import (
    get_portfolio_data_for_api,
    get_portfolio_summary_for_api,
    get_market_data_for_api,
    get_chart_html_for_api,
    add_asset_for_api,
    update_portfolio_for_api
)

# Crear app FastAPI
app = FastAPI(
    title="Portfolio Manager API",
    description="API para gestión de portafolio de inversiones",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# ENDPOINTS DE PORTAFOLIO
# ========================================

@app.get("/api/portfolio")
async def get_portfolio(
    period: str = Query("6mo", description="Periodo de tiempo (1d, 1w, 1mo, 6mo, 1y)"),
    refresh: bool = Query(False, description="Forzar actualización de datos")
):
    """
    Obtiene datos completos del portafolio
    
    - **period**: Periodo de tiempo para análisis histórico
    - **refresh**: Si es True, fuerza la actualización de datos
    """
    try:
        data = get_portfolio_data_for_api(period=period, refresh=refresh)
        
        if not data:
            raise HTTPException(status_code=404, detail="No se pudieron obtener datos del portafolio")
        
        return data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """
    Obtiene un resumen rápido del portafolio sin generar gráficos
    
    Retorna:
    - Valor total
    - Cambio porcentual
    - Cambio absoluto
    - Lista de activos con precios actuales
    """
    try:
        summary = get_portfolio_summary_for_api()
        
        if not summary:
            raise HTTPException(status_code=404, detail="No se pudo obtener el resumen")
        
        return summary
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/assets")
async def get_portfolio_assets():
    """
    Obtiene solo la lista de activos del portafolio
    """
    try:
        summary = get_portfolio_summary_for_api()
        
        if not summary or "assets" not in summary:
            raise HTTPException(status_code=404, detail="No se pudieron obtener los activos")
        
        return {"assets": summary["assets"]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/asset")
async def add_asset(symbol: str, units: int):
    """
    Agrega un nuevo activo al portafolio
    
    - **symbol**: Símbolo del ticker (ej: AAPL, TSLA)
    - **units**: Número de unidades/acciones
    """
    try:
        result = add_asset_for_api(symbol, units)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/portfolio")
async def update_portfolio(assets: List[dict]):
    """
    Actualiza todo el portafolio
    
    Body ejemplo:
    ```json
    [
        {"symbol": "AAPL", "units": 10, "name": "Apple"},
        {"symbol": "TSLA", "units": 20, "name": "Tesla"}
    ]
    ```
    """
    try:
        result = update_portfolio_for_api(assets)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# ENDPOINTS DE MERCADO
# ========================================

@app.get("/api/market")
async def get_market_data():
    """
    Obtiene datos de mercado general (watchlist)
    
    Retorna:
    - Todos los activos de la watchlist
    - Top 5 ganadores
    - Top 5 perdedores
    - 4 más vistos
    """
    try:
        market_data = get_market_data_for_api()
        
        if not market_data:
            raise HTTPException(status_code=404, detail="No se pudieron obtener datos de mercado")
        
        return market_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/gainers")
async def get_market_gainers():
    """
    Obtiene los mayores ganadores del mercado
    """
    try:
        market_data = get_market_data_for_api()
        
        if not market_data or "gainers" not in market_data:
            raise HTTPException(status_code=404, detail="No se pudieron obtener ganadores")
        
        return {"gainers": market_data["gainers"]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/losers")
async def get_market_losers():
    """
    Obtiene los mayores perdedores del mercado
    """
    try:
        market_data = get_market_data_for_api()
        
        if not market_data or "losers" not in market_data:
            raise HTTPException(status_code=404, detail="No se pudieron obtener perdedores")
        
        return {"losers": market_data["losers"]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# ENDPOINTS DE GRÁFICOS
# ========================================

@app.get("/api/chart/portfolio", response_class=HTMLResponse)
async def get_portfolio_chart():
    """
    Obtiene el gráfico de rendimiento del portafolio en formato HTML
    """
    try:
        html = get_chart_html_for_api("portfolio")
        
        if not html:
            raise HTTPException(status_code=404, detail="Gráfico no encontrado")
        
        return HTMLResponse(content=html)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chart/allocation", response_class=HTMLResponse)
async def get_allocation_chart():
    """
    Obtiene el gráfico de distribución del portafolio en formato HTML
    """
    try:
        html = get_chart_html_for_api("allocation")
        
        if not html:
            raise HTTPException(status_code=404, detail="Gráfico no encontrado")
        
        return HTMLResponse(content=html)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chart/{symbol}", response_class=HTMLResponse)
async def get_asset_chart(symbol: str):
    """
    Obtiene el gráfico de un activo específico en formato HTML
    
    - **symbol**: Símbolo del ticker (ej: AAPL, TSLA)
    """
    try:
        html = get_chart_html_for_api(symbol.upper())
        
        if not html:
            raise HTTPException(
                status_code=404, 
                detail=f"Gráfico no encontrado para {symbol}"
            )
        
        return HTMLResponse(content=html)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# ENDPOINTS DE UTILIDAD
# ========================================

@app.get("/")
async def root():
    """
    Endpoint raíz con información de la API
    """
    return {
        "name": "Portfolio Manager API",
        "version": "1.0.0",
        "description": "API para gestión de portafolio de inversiones",
        "endpoints": {
            "portfolio": "/api/portfolio",
            "market": "/api/market",
            "charts": "/api/chart/{type}",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/health")
async def health_check():
    """
    Endpoint de health check
    """
    return {"status": "healthy"}


# ========================================
# EJECUTAR APLICACIÓN
# ========================================

if __name__ == "__main__":
    import uvicorn
    
    print("="*60)
    print("INICIANDO PORTFOLIO MANAGER API")
    print("="*60)
    print("\nEndpoints disponibles:")
    print("  - Documentación: http://localhost:8000/docs")
    print("  - Portafolio: http://localhost:8000/api/portfolio")
    print("  - Mercado: http://localhost:8000/api/market")
    print("  - Gráficos: http://localhost:8000/api/chart/portfolio")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
