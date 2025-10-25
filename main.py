import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import user_router, auth_router, ai_router
from api.ribbon_router import router as ribbon_router
from api.analizer_router import router as analizer_router
from api.portfolio_router import router as portfolio_router
from api.storage_router import router as storage_router
from api.portfolio_manager_router import router as portfolio_manager_router
from api.home_router import router as home_router
from api.supabase_auth_router import router as supabase_auth_router
from config import settings
from services.portfolio_manager_service import (
    shutdown_portfolio_manager,
    startup_portfolio_manager,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend para la aplicación de finanzas con IA - FastAPI Migration",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configuración de CORS
# Obtener orígenes CORS desde settings
origins = settings.get_cors_origins()
# Agregar CLIENT_ORIGIN si no está en la lista
if settings.CLIENT_ORIGIN not in origins:
    origins.append(settings.CLIENT_ORIGIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup() -> None:
    await startup_portfolio_manager()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await shutdown_portfolio_manager()

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Mi Proyecto API - FastAPI Backend",
        "status": "ok",
        "version": "1.0.0"
    }

@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }

# Include routers
app.include_router(
    auth_router, 
    tags=["Authentication"], 
    prefix=f"{settings.API_V1_STR}/auth"
)
app.include_router(
    supabase_auth_router,
    tags=["Supabase Auth Integration"],
)
app.include_router(
    user_router, 
    tags=["Users"], 
    prefix=f"{settings.API_V1_STR}/users"
)
app.include_router(
    ai_router, 
    tags=["AI"], 
    prefix=f"{settings.API_V1_STR}/ai"
)
app.include_router(
    portfolio_router, 
    tags=["Portfolio"], 
    prefix=""  # Ya incluye el prefijo /api/portfolio en el router
)

app.include_router(
    storage_router,
)

app.include_router(
    home_router,
)

app.include_router(
    portfolio_manager_router,
)

# Portfolio Analizer v2 (script integration)
app.include_router(
    analizer_router,
    tags=["Portfolio Analizer v2"],
)

# Ribbon actions (summary/performance/forecast/alerts/custom report)
app.include_router(
    ribbon_router,
    tags=["Ribbon Actions"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 