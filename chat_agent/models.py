# -*- coding: utf-8 -*-
"""
Modelos Pydantic para el agente de chat financiero
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class ModelType(str, Enum):
    """Tipos de modelo disponibles"""
    FLASH = "gemini-2.5-flash"
    PRO = "gemini-2.5-pro"


class ChatRequest(BaseModel):
    """Modelo de solicitud para el chat"""
    message: str = Field(..., description="Mensaje del usuario", min_length=1)
    file_content: Optional[str] = Field(None, description="Contenido del archivo para análisis")
    file_type: Optional[str] = Field(None, description="Tipo MIME del archivo")
    url: Optional[HttpUrl] = Field(None, description="URL para análisis")
    use_model: Optional[ModelType] = Field(None, description="Modelo específico a usar")
    session_id: Optional[str] = Field(None, description="ID de sesión para contexto")
    
    class Config:
        # Permitir URLs como strings también
        arbitrary_types_allowed = True


class ChatResponse(BaseModel):
    """Modelo de respuesta del chat"""
    response: str = Field(..., description="Respuesta del agente")
    model_used: str = Field(..., description="Modelo utilizado")
    tools_used: List[str] = Field(default_factory=list, description="Herramientas utilizadas")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")
    urls_processed: List[str] = Field(default_factory=list, description="URLs procesadas")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Información de tokens")
    session_id: Optional[str] = Field(None, description="ID de sesión")


class AgentConfig(BaseModel):
    """Configuración del agente"""
    api_key: str = Field(..., description="API Key de Google Gemini")
    model_flash: str = Field(default="gemini-2.5-flash", description="Modelo Flash")
    model_pro: str = Field(default="gemini-2.5-pro", description="Modelo Pro")
    enable_web_search: bool = Field(default=True, description="Habilitar búsqueda web")
    enable_url_context: bool = Field(default=True, description="Habilitar contexto de URL")
    max_tokens: Optional[int] = Field(None, description="Máximo de tokens")


class ErrorResponse(BaseModel):
    """Modelo de respuesta de error"""
    error: str = Field(..., description="Mensaje de error")
    detail: Optional[str] = Field(None, description="Detalle del error")
    code: Optional[int] = Field(None, description="Código de error")


class SessionInfo(BaseModel):
    """Información de sesión"""
    session_id: str = Field(..., description="ID de sesión")
    created_at: str = Field(..., description="Timestamp de creación")
    last_activity: str = Field(..., description="Última actividad")
    message_count: int = Field(default=0, description="Número de mensajes")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contexto de la sesión")
