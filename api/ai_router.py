# -*- coding: utf-8 -*-
"""
AI Router - Endpoints para el agente financiero Horizon v3.0
"""

import os
import tempfile
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import settings
from models.schemas import APIResponse
from services.remote_agent_client import remote_agent_client

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
async def chat_with_agent(request: ChatRequest):
    """
    Endpoint principal para chat con el agente financiero
    """
    try:
        # Usar servicio remoto
        response_data = await remote_agent_client.process_message(
            message=request.message,
            file_path=request.file_path,
            url=request.url
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
    file: UploadFile = File(..., description="Archivo para análisis")
):
    """
    Endpoint para chat con archivo adjunto
    """
    try:
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Usar servicio remoto
            response_data = await remote_agent_client.process_message(
                message=message,
                file_path=temp_file_path
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
                "service_url": settings.CHAT_AGENT_SERVICE_URL,
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
async def search_financial_news(query: str = Form(...)):
    """
    Buscar noticias financieras
    """
    try:
        # Usar servicio remoto
        response_data = await remote_agent_client.process_message(
            message=query
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
    query: str = Form("Analiza esta página web")
):
    """
    Analizar una URL específica
    """
    try:
        # Usar servicio remoto
        response_data = await remote_agent_client.process_message(
            message=query,
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
    include_news: bool = Query(True, description="Incluir análisis de noticias")
):
    """
    Predice tendencias financieras usando el agente
    """
    try:
        # Crear consulta para predicción
        query = f"Analiza la tendencia de {symbol} para los próximos {period}"
        if include_news:
            query += ". Incluye análisis de noticias recientes y sentimiento del mercado."
        
        # Usar servicio remoto
        response_data = await remote_agent_client.process_message(
            message=query
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