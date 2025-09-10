# -*- coding: utf-8 -*-
"""
Horizon Agent v3.0 - Integración FastAPI
Agente financiero con distribución correcta de funcionalidades
"""

import os
import sys
import uuid
import mimetypes
from datetime import datetime
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

from .models import ChatRequest, ChatResponse, ModelType, SessionInfo

# Cargar variables de entorno
load_dotenv()


class HorizonAgent:
    """
    Agente financiero Horizon v3.0 con integración FastAPI
    """
    
    def __init__(self):
        """Inicializa el agente"""
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY o GOOGLE_API_KEY no configurada")
        
        # Configurar variable de entorno
        if not os.getenv("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = self.api_key
        
        # Importar y configurar cliente
        self._setup_client()
        
        # Configuración de modelos
        self.model_flash = ModelType.FLASH.value
        self.model_pro = ModelType.PRO.value
        
        # Cache de sesiones
        self.sessions: Dict[str, SessionInfo] = {}
        
        # Prompts del sistema
        self.flash_system_prompt = """
Eres un asistente financiero rápido y eficiente especializado en:
- Consultas generales del mercado y definiciones financieras
- Búsquedas web de información actualizada 
- Análisis de contenido de URLs
- Resúmenes concisos y respuestas directas
- Noticias financieras en tiempo real

Utiliza las herramientas de búsqueda web y análisis de URLs cuando necesites información actualizada.
Sé directo, preciso y proporciona fuentes cuando sea apropiado.
"""
        
        self.pro_system_prompt = """
Eres un analista financiero cuantitativo senior, escéptico y riguroso como 
los protagonistas de 'The Big Short'. Tu especialidad es el análisis profundo de:
- Documentos financieros y reportes anuales
- Estados financieros y métricas
- Gráficos, tablas y datos numéricos
- Archivos CSV, PDF, imágenes de documentos

No confías en opiniones populares; confías en los datos duros. Identifica patrones, 
riesgos, tendencias y métricas clave. Proporciona conclusiones fundamentadas y 
señala inconsistencias o riesgos ocultos en los documentos que analices.

IMPORTANTE: Solo trabajas con documentos locales. No tienes acceso a búsquedas web.
"""
    
    def _setup_client(self):
        """Configura el cliente de Google Gemini"""
        try:
            from google import genai
            from google.genai import types
            
            self.genai = genai
            self.types = types
            self.client = genai.Client()
            print("✅ Cliente Gemini configurado correctamente")
            
        except Exception as e:
            print(f"❌ Error configurando cliente: {e}")
            raise
    
    def create_session(self) -> str:
        """Crea una nueva sesión de chat"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = SessionInfo(
            session_id=session_id,
            created_at=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
            message_count=0,
            context={}
        )
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Obtiene información de una sesión"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str):
        """Actualiza la actividad de una sesión"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_activity = datetime.now().isoformat()
            session.message_count += 1
    
    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Procesa una solicitud de chat y retorna la respuesta
        """
        try:
            # Crear sesión si no existe
            if not request.session_id:
                request.session_id = self.create_session()
            elif request.session_id not in self.sessions:
                self.create_session()
            
            # Actualizar sesión
            self.update_session(request.session_id)
            
            # Determinar qué modelo usar
            model_to_use = self._determine_model(request)
            
            # Procesar según el modelo
            if model_to_use == self.model_pro:
                response_data = await self._process_with_pro(request)
            else:
                response_data = await self._process_with_flash(request)
            
            # Crear respuesta
            return ChatResponse(
                response=response_data["text"],
                model_used=response_data["model"],
                tools_used=response_data.get("tools", []),
                metadata=response_data.get("metadata", {}),
                urls_processed=response_data.get("urls", []),
                token_usage=response_data.get("token_usage"),
                session_id=request.session_id
            )
            
        except Exception as e:
            print(f"❌ Error procesando chat: {e}")
            raise
    
    def _determine_model(self, request: ChatRequest) -> str:
        """Determina qué modelo usar basado en la solicitud"""
        # Si se especifica un modelo, usarlo
        if request.use_model:
            return request.use_model.value
        
        # Si hay contenido de archivo, usar Pro
        if request.file_content:
            return self.model_pro
        
        # Si hay URL pero no archivo, usar Flash
        if request.url:
            return self.model_flash
        
        # Para consultas generales, determinar por palabras clave
        pro_keywords = ['analiza', 'reporte', 'informe', 'métricas', 'profundo', 
                       'análisis', 'evaluar', 'documento', 'detallado']
        
        if any(keyword in request.message.lower() for keyword in pro_keywords):
            return self.model_pro
        
        return self.model_flash
    
    async def _process_with_flash(self, request: ChatRequest) -> Dict[str, Any]:
        """Procesa solicitud con Gemini Flash"""
        print(f"⚡ [Flash]: Procesando consulta")
        
        # Preparar prompt
        prompt_completo = self.flash_system_prompt + "\\n\\nConsulta del usuario: " + request.message
        
        # Agregar URL si está presente
        if request.url:
            prompt_completo += f" {request.url}"
        
        tools_used = []
        urls_processed = []
        
        try:
            # Configurar herramientas
            tools = []
            tools.append(self.types.Tool(google_search=self.types.GoogleSearch()))
            tools_used.append("Google Search")
            
            if request.url:
                tools.append(self.types.Tool(url_context=self.types.UrlContext()))
                tools_used.append("URL Context")
            
            config = self.types.GenerateContentConfig(
                tools=tools,
                response_modalities=["TEXT"]
            )
            
            response = self.client.models.generate_content(
                model=self.model_flash,
                contents=prompt_completo,
                config=config
            )
            
        except Exception as tool_error:
            print(f"⚠️ Herramientas no disponibles: {tool_error}")
            # Fallback sin herramientas
            response = self.client.models.generate_content(
                model=self.model_flash,
                contents=prompt_completo
            )
            tools_used = []
        
        # Extraer URLs procesadas si hay URL Context
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'url_context_metadata') and candidate.url_context_metadata:
                for url_meta in candidate.url_context_metadata.url_metadata:
                    urls_processed.append(url_meta.retrieved_url)
        
        # Información de tokens
        token_usage = None
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            token_usage = {
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count,
                "total_tokens": usage.total_token_count if hasattr(usage, 'total_token_count') else None
            }
        
        return {
            "text": response.text,
            "model": self.model_flash,
            "tools": tools_used,
            "urls": urls_processed,
            "token_usage": token_usage,
            "metadata": {"processing_type": "flash_rapid_analysis"}
        }
    
    async def _process_with_pro(self, request: ChatRequest) -> Dict[str, Any]:
        """Procesa solicitud con Gemini Pro"""
        print(f"🧠 [Pro]: Análisis profundo")
        
        # Preparar prompt
        prompt_completo = self.pro_system_prompt + "\\n\\nConsulta del usuario: " + request.message
        
        # Agregar contenido del archivo si está presente
        if request.file_content:
            prompt_completo += f"\\n\\nContenido del documento para análisis:\\n{request.file_content}"
        
        # Ejecutar Pro sin herramientas web
        response = self.client.models.generate_content(
            model=self.model_pro,
            contents=prompt_completo
        )
        
        # Información de tokens
        token_usage = None
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            token_usage = {
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count,
                "total_tokens": usage.total_token_count if hasattr(usage, 'total_token_count') else None
            }
        
        return {
            "text": response.text,
            "model": self.model_pro,
            "tools": [],  # Pro no usa herramientas web
            "urls": [],
            "token_usage": token_usage,
            "metadata": {"processing_type": "pro_deep_analysis"}
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Retorna el estado del agente"""
        return {
            "status": "active",
            "models_available": [self.model_flash, self.model_pro],
            "active_sessions": len(self.sessions),
            "version": "3.0",
            "capabilities": [
                "financial_analysis",
                "web_search",
                "url_analysis", 
                "document_analysis",
                "real_time_data"
            ]
        }
