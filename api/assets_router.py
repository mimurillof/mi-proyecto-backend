"""Endpoints para gestionar activos del portafolio en Supabase Database."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from config import settings
from auth.dependencies import get_current_user
from db_models.models import User

try:
    from supabase import create_client, Client  # type: ignore
except ImportError:
    create_client = None  # type: ignore
    Client = Any  # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/assets",
    tags=["Portfolio Assets"],
)

# Cliente de Supabase (inicializado de forma lazy)
_supabase_client: Optional[Any] = None


def get_supabase_client() -> Any:
    """Obtiene el cliente de Supabase con inicialización lazy."""
    global _supabase_client
    if _supabase_client is None:
        if create_client is None:
            raise HTTPException(status_code=500, detail="Librería Supabase no disponible")
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE:
            raise HTTPException(status_code=500, detail="Configuración de Supabase incompleta")
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE)
    return _supabase_client


# ============== Modelos Pydantic ==============

class AssetCreate(BaseModel):
    """Modelo para crear un nuevo activo en el portafolio."""
    asset_symbol: str = Field(..., min_length=1, max_length=20, description="Símbolo del activo (ej: AAPL, BTC-USD)")
    quantity: float = Field(..., gt=0, description="Cantidad de unidades")
    acquisition_price: float = Field(..., gt=0, description="Precio de adquisición por unidad")
    acquisition_date: Optional[date] = Field(None, description="Fecha de adquisición (YYYY-MM-DD)")


class AssetUpdate(BaseModel):
    """Modelo para actualizar un activo existente."""
    quantity: Optional[float] = Field(None, gt=0, description="Nueva cantidad de unidades")
    acquisition_price: Optional[float] = Field(None, gt=0, description="Nuevo precio de adquisición")
    acquisition_date: Optional[date] = Field(None, description="Nueva fecha de adquisición")


class AssetResponse(BaseModel):
    """Modelo de respuesta para un activo."""
    asset_id: int
    portfolio_id: int
    asset_symbol: str
    quantity: float
    acquisition_price: float
    acquisition_date: Optional[date]
    added_at: Optional[datetime]


class AssetListResponse(BaseModel):
    """Respuesta para listar activos."""
    success: bool
    data: List[AssetResponse]
    count: int


# ============== Helpers ==============

async def get_user_portfolio_id(user_id: Any) -> int:
    """
    Obtiene el portfolio_id del usuario.
    Si el usuario no tiene portafolio, crea uno.
    """
    client = get_supabase_client()
    user_id_str = str(user_id)
    
    # Buscar portafolio existente del usuario
    response = client.table("portfolios").select("portfolio_id").eq("user_id", user_id_str).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]["portfolio_id"]
    
    # Si no existe, crear uno nuevo
    new_portfolio = client.table("portfolios").insert({
        "user_id": user_id_str,
        "name": "Mi Portafolio",
        "description": "Portafolio principal"
    }).execute()
    
    if not new_portfolio.data:
        raise HTTPException(status_code=500, detail="No se pudo crear el portafolio")
    
    return new_portfolio.data[0]["portfolio_id"]


# ============== Endpoints ==============

@router.get("", response_model=AssetListResponse)
async def list_assets(
    current_user: User = Depends(get_current_user),
):
    """
    Lista todos los activos del portafolio del usuario autenticado.
    
    Retorna una lista de activos con su símbolo, cantidad, precio de adquisición y fecha.
    """
    try:
        portfolio_id = await get_user_portfolio_id(current_user.user_id)
        client = get_supabase_client()
        
        response = client.table("assets").select("*").eq("portfolio_id", portfolio_id).order("added_at", desc=True).execute()
        
        assets = []
        for row in response.data or []:
            assets.append(AssetResponse(
                asset_id=row["asset_id"],
                portfolio_id=row["portfolio_id"],
                asset_symbol=row["asset_symbol"],
                quantity=float(row["quantity"]) if row["quantity"] else 0,
                acquisition_price=float(row["acquisition_price"]) if row["acquisition_price"] else 0,
                acquisition_date=row.get("acquisition_date"),
                added_at=row.get("added_at"),
            ))
        
        logger.info(f"✅ [ASSETS] Listados {len(assets)} activos para user_id={current_user.user_id}")
        
        return AssetListResponse(
            success=True,
            data=assets,
            count=len(assets),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [ASSETS] Error listando activos: {e}")
        raise HTTPException(status_code=500, detail=f"Error al listar activos: {str(e)}")


@router.post("", status_code=201)
async def create_asset(
    asset: AssetCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Añade un nuevo activo al portafolio del usuario.
    
    - **asset_symbol**: Símbolo del activo (requerido)
    - **quantity**: Cantidad de unidades (requerido)
    - **acquisition_price**: Precio de adquisición por unidad (requerido)
    - **acquisition_date**: Fecha de adquisición (opcional, default: hoy)
    """
    try:
        portfolio_id = await get_user_portfolio_id(current_user.user_id)
        client = get_supabase_client()
        
        # Verificar si el activo ya existe en el portafolio
        existing = client.table("assets").select("asset_id").eq("portfolio_id", portfolio_id).eq("asset_symbol", asset.asset_symbol.upper()).execute()
        
        if existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"El activo {asset.asset_symbol.upper()} ya existe en tu portafolio. Usa PUT para actualizar."
            )
        
        # Crear el nuevo activo
        new_asset = {
            "portfolio_id": portfolio_id,
            "asset_symbol": asset.asset_symbol.upper().strip(),
            "quantity": asset.quantity,
            "acquisition_price": asset.acquisition_price,
            "acquisition_date": asset.acquisition_date.isoformat() if asset.acquisition_date else date.today().isoformat(),
        }
        
        response = client.table("assets").insert(new_asset).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="No se pudo crear el activo")
        
        created = response.data[0]
        logger.info(f"✅ [ASSETS] Creado activo {asset.asset_symbol.upper()} para user_id={current_user.user_id}")
        
        return {
            "success": True,
            "message": f"Activo {asset.asset_symbol.upper()} añadido exitosamente",
            "data": AssetResponse(
                asset_id=created["asset_id"],
                portfolio_id=created["portfolio_id"],
                asset_symbol=created["asset_symbol"],
                quantity=float(created["quantity"]) if created["quantity"] else 0,
                acquisition_price=float(created["acquisition_price"]) if created["acquisition_price"] else 0,
                acquisition_date=created.get("acquisition_date"),
                added_at=created.get("added_at"),
            ),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [ASSETS] Error creando activo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al crear activo: {str(e)}")


@router.put("/{symbol}")
async def update_asset(
    symbol: str,
    asset_update: AssetUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Actualiza un activo existente en el portafolio.
    
    - **symbol**: Símbolo del activo a actualizar
    - **quantity**: Nueva cantidad (opcional)
    - **acquisition_price**: Nuevo precio de adquisición (opcional)
    - **acquisition_date**: Nueva fecha de adquisición (opcional)
    """
    try:
        portfolio_id = await get_user_portfolio_id(current_user.user_id)
        client = get_supabase_client()
        symbol_upper = symbol.upper().strip()
        
        # Verificar que el activo existe
        existing = client.table("assets").select("*").eq("portfolio_id", portfolio_id).eq("asset_symbol", symbol_upper).execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail=f"Activo {symbol_upper} no encontrado en tu portafolio")
        
        # Construir objeto de actualización
        update_data = {}
        if asset_update.quantity is not None:
            update_data["quantity"] = asset_update.quantity
        if asset_update.acquisition_price is not None:
            update_data["acquisition_price"] = asset_update.acquisition_price
        if asset_update.acquisition_date is not None:
            update_data["acquisition_date"] = asset_update.acquisition_date.isoformat()
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")
        
        # Actualizar
        response = client.table("assets").update(update_data).eq("portfolio_id", portfolio_id).eq("asset_symbol", symbol_upper).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el activo")
        
        updated = response.data[0]
        logger.info(f"✅ [ASSETS] Actualizado activo {symbol_upper} para user_id={current_user.user_id}")
        
        return {
            "success": True,
            "message": f"Activo {symbol_upper} actualizado exitosamente",
            "data": AssetResponse(
                asset_id=updated["asset_id"],
                portfolio_id=updated["portfolio_id"],
                asset_symbol=updated["asset_symbol"],
                quantity=float(updated["quantity"]) if updated["quantity"] else 0,
                acquisition_price=float(updated["acquisition_price"]) if updated["acquisition_price"] else 0,
                acquisition_date=updated.get("acquisition_date"),
                added_at=updated.get("added_at"),
            ),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [ASSETS] Error actualizando activo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al actualizar activo: {str(e)}")


@router.delete("/{symbol}")
async def delete_asset(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    """
    Elimina un activo del portafolio.
    
    - **symbol**: Símbolo del activo a eliminar
    """
    try:
        portfolio_id = await get_user_portfolio_id(current_user.user_id)
        client = get_supabase_client()
        symbol_upper = symbol.upper().strip()
        
        # Verificar que el activo existe
        existing = client.table("assets").select("asset_id").eq("portfolio_id", portfolio_id).eq("asset_symbol", symbol_upper).execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail=f"Activo {symbol_upper} no encontrado en tu portafolio")
        
        # Eliminar
        response = client.table("assets").delete().eq("portfolio_id", portfolio_id).eq("asset_symbol", symbol_upper).execute()
        
        logger.info(f"✅ [ASSETS] Eliminado activo {symbol_upper} para user_id={current_user.user_id}")
        
        return {
            "success": True,
            "message": f"Activo {symbol_upper} eliminado exitosamente",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [ASSETS] Error eliminando activo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al eliminar activo: {str(e)}")


@router.get("/{symbol}")
async def get_asset(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene los detalles de un activo específico.
    
    - **symbol**: Símbolo del activo
    """
    try:
        portfolio_id = await get_user_portfolio_id(current_user.user_id)
        client = get_supabase_client()
        symbol_upper = symbol.upper().strip()
        
        response = client.table("assets").select("*").eq("portfolio_id", portfolio_id).eq("asset_symbol", symbol_upper).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail=f"Activo {symbol_upper} no encontrado en tu portafolio")
        
        row = response.data[0]
        
        return {
            "success": True,
            "data": AssetResponse(
                asset_id=row["asset_id"],
                portfolio_id=row["portfolio_id"],
                asset_symbol=row["asset_symbol"],
                quantity=float(row["quantity"]) if row["quantity"] else 0,
                acquisition_price=float(row["acquisition_price"]) if row["acquisition_price"] else 0,
                acquisition_date=row.get("acquisition_date"),
                added_at=row.get("added_at"),
            ),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [ASSETS] Error obteniendo activo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener activo: {str(e)}")
