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

from chat_agent import HorizonAgent
from models.schemas import APIResponse

router = APIRouter()

# Modelos para requests/responses
class ChatRequest(BaseModel):
    message: str
    file_path: Optional[str] = None
    url: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    model_used: str
    tools_used: List[str]
    metadata: dict
    urls_processed: List[str]
    token_usage: dict
    session_id: str

# Instancia global del agente
agent: Optional[HorizonAgent] = None

def get_agent() -> HorizonAgent:
    """Obtiene o crea la instancia del agente"""
    global agent
    if agent is None:
        try:
            agent = HorizonAgent()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error inicializando agente: {str(e)}"
            )
    return agent

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Endpoint principal para chat con el agente financiero
    """
    try:
        horizon_agent = get_agent()
        response_data = horizon_agent.process_query(
            request.message, 
            request.file_path, 
            request.url
        )
        return ChatResponse(**response_data)
    
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
        horizon_agent = get_agent()
        
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Procesar con el archivo
            response_data = horizon_agent.process_query(message, temp_file_path)
            return ChatResponse(**response_data)
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
        horizon_agent = get_agent()
        status = horizon_agent.get_status()
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
        # Verificar variables de entorno
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="API Key no configurada"
            )
        
        # Intentar obtener agente
        horizon_agent = get_agent()
        
        return APIResponse(
            success=True,
            message="Agente operativo",
            data={
                "status": "healthy",
                "agent_active": True,
                "version": "3.0",
                "models": ["gemini-2.5-flash", "gemini-2.5-pro"]
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
        horizon_agent = get_agent()
        response_data = horizon_agent.process_query(query)
        return ChatResponse(**response_data)
    
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
        horizon_agent = get_agent()
        response_data = horizon_agent.process_query(query, None, url)
        return ChatResponse(**response_data)
    
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
        horizon_agent = get_agent()
        
        # Crear consulta para predicción
        query = f"Analiza la tendencia de {symbol} para los próximos {period}"
        if include_news:
            query += ". Incluye análisis de noticias recientes y sentimiento del mercado."
        
        response_data = horizon_agent.process_query(query)
        
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