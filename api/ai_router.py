# -*- coding: utf-8 -*-
"""
AI Router - Endpoints para el agente financiero Horizon v3.0
"""

import os
import tempfile
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import settings
from models.schemas import APIResponse
from services.remote_agent_client import remote_agent_client
from auth.dependencies import get_current_user  # ✅ Importar dependencia de autenticación
from db_models.models import User  # ✅ Importar modelo de Usuario

router = APIRouter()

# Modelos para requests/responses
class ChatRequest(BaseModel):
    message: str
    file_path: Optional[str] = None
    url: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    model_used: str = "unknown"
    tools_used: List[str] = []
    metadata: dict = {}
    urls_processed: List[str] = []
    token_usage: dict = {}
    session_id: str = "unknown"

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),  # ✅ Requerir autenticación
    authorization: Optional[str] = Header(None)  # ✅ Obtener header Authorization
):
    """
    Endpoint principal para chat con el agente financiero
    Requiere autenticación - el agente accederá solo a los archivos del usuario
    """
    try:
        user_id = str(current_user.user_id)  # ✅ Obtener user_id del usuario autenticado
        
        # Extraer token JWT del header Authorization
        auth_token = None
        if authorization and authorization.startswith("Bearer "):
            auth_token = authorization.split(" ", 1)[1]
        
        # Usar servicio remoto
        response_data = await remote_agent_client.process_message(
            message=request.message,
            user_id=user_id,  # ✅ Pasar user_id al agente
            file_path=request.file_path,
            url=request.url,
            auth_token=auth_token  # ✅ Pasar token JWT al agente
        )
        
        # Normalizar la respuesta para garantizar compatibilidad
        normalized_response = {
            "response": response_data.get("response", "Sin respuesta"),
            "model_used": response_data.get("model_used", "unknown"),
            "tools_used": response_data.get("tools_used", []),
            "metadata": response_data.get("metadata", {}),
            "urls_processed": response_data.get("urls_processed", []),
            "token_usage": response_data.get("token_usage", {}),
            "session_id": response_data.get("session_id", "unknown")
        }
        
        return ChatResponse(**normalized_response)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando chat: {str(e)}"
        )

@router.post("/chat/upload")
async def chat_with_file(
    message: str = Form(..., description="Mensaje del usuario"),
    file: UploadFile = File(..., description="Archivo para análisis"),
    current_user: User = Depends(get_current_user),  # ✅ Requerir autenticación
    authorization: Optional[str] = Header(None)  # ✅ Obtener header Authorization
):
    """
    Endpoint para chat con archivo adjunto
    Requiere autenticación - el agente accederá solo a los archivos del usuario
    """
    try:
        user_id = str(current_user.user_id)  # ✅ Obtener user_id del usuario autenticado
        
        # Extraer token JWT del header Authorization
        auth_token = None
        if authorization and authorization.startswith("Bearer "):
            auth_token = authorization.split(" ", 1)[1]
        
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Usar servicio remoto
            response_data = await remote_agent_client.process_message(
                message=message,
                user_id=user_id,  # ✅ Pasar user_id al agente
                file_path=temp_file_path,
                auth_token=auth_token  # ✅ Pasar token JWT al agente
            )
            
            # Normalizar la respuesta
            normalized_response = {
                "response": response_data.get("response", "Sin respuesta"),
                "model_used": response_data.get("model_used", "unknown"),
                "tools_used": response_data.get("tools_used", []),
                "metadata": response_data.get("metadata", {}),
                "urls_processed": response_data.get("urls_processed", []),
                "token_usage": response_data.get("token_usage", {}),
                "session_id": response_data.get("session_id", "unknown")
            }
            
            return ChatResponse(**normalized_response)
        finally:
            # Limpiar archivo temporal
            import os
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando archivo: {str(e)}"
        )

@router.get("/status")
async def get_agent_status():
    """
    Obtiene el estado del agente
    """
    try:
        # Verificar estado del servicio remoto
        status = await remote_agent_client.get_status()
        return status
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estado: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    Health check del agente
    """
    try:
        # Verificar servicio remoto
        remote_status = await remote_agent_client.health_check()
        
        return APIResponse(
            success=remote_status.get("status") == "healthy",
            message="Servicio de agente remoto",
            data={
                "status": remote_status.get("status", "unknown"),
                "service_url": settings.get_chat_agent_url(),
                "remote_service": True,
                "version": remote_status.get("version", "unknown"),
                "models": remote_status.get("models_available", [])
            }
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": f"Error en agente: {str(e)}",
                "data": None
            }
        )

@router.post("/search-news")
async def search_financial_news(
    query: str = Form(...),
    current_user: User = Depends(get_current_user)  # ✅ Requerir autenticación
):
    """
    Buscar noticias financieras
    Requiere autenticación
    """
    try:
        user_id = str(current_user.user_id)  # ✅ Obtener user_id del usuario autenticado
        
        # Usar servicio remoto
        response_data = await remote_agent_client.process_message(
            message=query,
            user_id=user_id  # ✅ Pasar user_id al agente
        )
        
        # Normalizar la respuesta
        normalized_response = {
            "response": response_data.get("response", "Sin respuesta"),
            "model_used": response_data.get("model_used", "unknown"),
            "tools_used": response_data.get("tools_used", []),
            "metadata": response_data.get("metadata", {}),
            "urls_processed": response_data.get("urls_processed", []),
            "token_usage": response_data.get("token_usage", {}),
            "session_id": response_data.get("session_id", "unknown")
        }
        
        return ChatResponse(**normalized_response)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error buscando noticias: {str(e)}"
        )

@router.post("/analyze-url")
async def analyze_url(
    url: str = Form(...),
    query: str = Form("Analiza esta página web"),
    current_user: User = Depends(get_current_user)  # ✅ Requerir autenticación
):
    """
    Analizar una URL específica
    Requiere autenticación
    """
    try:
        user_id = str(current_user.user_id)  # ✅ Obtener user_id del usuario autenticado
        
        # Usar servicio remoto
        response_data = await remote_agent_client.process_message(
            message=query,
            user_id=user_id,  # ✅ Pasar user_id al agente
            url=url
        )
        
        # Normalizar la respuesta
        normalized_response = {
            "response": response_data.get("response", "Sin respuesta"),
            "model_used": response_data.get("model_used", "unknown"),
            "tools_used": response_data.get("tools_used", []),
            "metadata": response_data.get("metadata", {}),
            "urls_processed": response_data.get("urls_processed", []),
            "token_usage": response_data.get("token_usage", {}),
            "session_id": response_data.get("session_id", "unknown")
        }
        
        return ChatResponse(**normalized_response)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analizando URL: {str(e)}"
        )

@router.post("/predict")
async def predict_trend(
    symbol: str = Query(..., description="Símbolo financiero"),
    period: str = Query("1month", description="Período de análisis"),
    include_news: bool = Query(True, description="Incluir análisis de noticias"),
    current_user: User = Depends(get_current_user)  # ✅ Requerir autenticación
):
    """
    Predice tendencias financieras usando el agente
    Requiere autenticación
    """
    try:
        user_id = str(current_user.user_id)  # ✅ Obtener user_id del usuario autenticado
        
        # Crear consulta para predicción
        query = f"Analiza la tendencia de {symbol} para los próximos {period}"
        if include_news:
            query += ". Incluye análisis de noticias recientes y sentimiento del mercado."
        
        # Usar servicio remoto
        response_data = await remote_agent_client.process_message(
            message=query,
            user_id=user_id  # ✅ Pasar user_id al agente
        )
        
        return {
            "symbol": symbol,
            "period": period,
            "prediction": response_data["response"],
            "model_used": response_data["model_used"],
            "confidence": "Analysis completed",
            "sources": response_data["urls_processed"],
            "session_id": response_data["session_id"]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en predicción: {str(e)}"
        ) 