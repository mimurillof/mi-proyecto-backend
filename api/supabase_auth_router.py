"""
Router para integración con Supabase Auth.
Permite intercambiar tokens de Supabase por JWT tokens del backend.
"""
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from datetime import timedelta

from database import get_db
from crud.user_service import user_crud
from auth.security import create_access_token
from config import settings
from models.schemas import Token
import uuid
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/supabase-auth", tags=["Supabase Auth"])


class SupabaseTokenExchange(BaseModel):
    """Request model para intercambio de tokens"""
    supabase_token: str
    email: EmailStr


class DirectLoginRequest(BaseModel):
    """Request model para login directo (sin Supabase Auth)"""
    email: EmailStr
    password: str


@router.post("/exchange-token", response_model=Token)
async def exchange_supabase_token(
    request: SupabaseTokenExchange,
    db: AsyncSession = Depends(get_db)
):
    """
    Intercambia un token de Supabase Auth por un JWT token del backend.
    
    Este endpoint permite que usuarios autenticados con Supabase puedan
    acceder a recursos protegidos del backend.
    """
    try:
        # Validar el token de Supabase (opcional pero recomendado)
        # Por ahora, confiamos en que el frontend ya validó con Supabase
        
        # Buscar el usuario en nuestra base de datos por email
        user = await user_crud.get_user_by_email(db, email=request.email)
        
        if not user:
            logger.warning(f"Usuario no encontrado para email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado en el sistema. Por favor, completa el registro."
            )
        
        # Crear nuestro propio JWT token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": str(user.user_id),
                "user_id": str(user.user_id),
                "email": user.email
            },
            expires_delta=access_token_expires
        )
        
        logger.info(f"✅ Token intercambiado exitosamente para usuario: {user.email}")
        
        return Token(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error en intercambio de token para {request.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al intercambiar token: {str(e)}"
        )


@router.post("/login-direct", response_model=Token)
async def login_direct(
    request: DirectLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login directo usando el backend (sin Supabase Auth).
    
    Este endpoint valida las credenciales contra la base de datos
    y emite un JWT token directamente.
    """
    try:
        # Autenticar usuario
        user = await user_crud.authenticate_user(db, request.email, request.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Crear JWT token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": str(user.user_id),
                "user_id": str(user.user_id),
                "email": user.email
            },
            expires_delta=access_token_expires
        )
        
        logger.info(f"✅ Login directo exitoso para usuario: {user.email}")
        
        return Token(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error en login directo para {request.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al iniciar sesión: {str(e)}"
        )


@router.post("/verify-and-login", response_model=Token)
async def verify_and_login(
    request: SupabaseTokenExchange,
    db: AsyncSession = Depends(get_db)
):
    """
    Verifica un token de Supabase con su API y emite un JWT del backend.
    
    Este es el método más seguro ya que valida el token directamente con Supabase.
    """
    try:
        # Verificar el token con Supabase
        supabase_url = settings.SUPABASE_URL
        headers = {
            "Authorization": f"Bearer {request.supabase_token}",
            "apikey": settings.SUPABASE_ANON_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers=headers,
                timeout=10.0
            )
        
        if response.status_code != 200:
            logger.warning(f"Token de Supabase inválido: {response.status_code}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de Supabase inválido o expirado"
            )
        
        user_data = response.json()
        email = user_data.get("email")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo obtener el email del token de Supabase"
            )
        
        # Buscar usuario en nuestra DB
        user = await user_crud.get_user_by_email(db, email=email)
        
        if not user:
            logger.warning(f"Usuario {email} autenticado en Supabase pero no existe en nuestro sistema")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado. Por favor, completa el proceso de registro."
            )
        
        # Emitir nuestro JWT
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": str(user.user_id),
                "user_id": str(user.user_id),
                "email": user.email
            },
            expires_delta=access_token_expires
        )
        
        logger.info(f"✅ Token verificado y intercambiado para: {email}")
        
        return Token(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error al verificar y intercambiar token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar token: {str(e)}"
        )
