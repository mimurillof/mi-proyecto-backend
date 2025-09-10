# -*- coding: utf-8 -*-
"""
Horizon Agent Service - Agente financiero integrado con FastAPI
Basado en Horizon v3.0 original
"""
import os
import sys
import uuid
import mimetypes
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import traceback

# Cargar variables de entorno
load_dotenv()

try:
    from google import genai
    from google.genai import types
    
    # Configurar API key
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY o GOOGLE_API_KEY no configurada")
    
    if not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = api_key
    
    client = genai.Client()
    
except Exception as e:
    print(f"❌ Error configurando Gemini: {e}")
    client = None

# Configuración de modelos
MODEL_FLASH = 'gemini-2.5-flash'
MODEL_PRO = 'gemini-2.5-pro'

# Prompts del sistema
FLASH_SYSTEM_PROMPT = """
Eres un asistente financiero rápido y eficiente especializado en:
- Consultas generales del mercado y definiciones financieras
- Búsquedas web de información actualizada 
- Análisis de contenido de URLs
- Resúmenes concisos y respuestas directas

Utiliza las herramientas disponibles cuando sea necesario y proporciona respuestas precisas y útiles.
"""

PRO_SYSTEM_PROMPT = """
Eres un analista financiero experto especializado en análisis profundo de documentos.
- Analiza documentos financieros con detalle crítico
- Identifica riesgos, oportunidades y patrones
- Proporciona insights accionables y fundamentados
- Mantén una perspectiva crítica y objetiva

Enfócate en la calidad del análisis sobre la velocidad.
"""

class HorizonAgent:
    """Agente financiero Horizon v3.0 para FastAPI"""
    
    def __init__(self):
        self.client = client
        self.sessions: Dict[str, Dict] = {}
        self.active_sessions = 0
        
        if not self.client:
            raise Exception("Cliente Gemini no disponible")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del agente"""
        return {
            "status": "active",
            "models_available": [MODEL_FLASH, MODEL_PRO],
            "active_sessions": self.active_sessions,
            "version": "3.0",
            "capabilities": [
                "financial_analysis",
                "web_search", 
                "url_analysis",
                "document_analysis",
                "real_time_data"
            ]
        }
    
    def _choose_model_and_tools(self, query: str, file_path: Optional[str] = None, url: Optional[str] = None) -> tuple:
        """Elegir modelo y herramientas basado en el tipo de consulta"""
        
        # Si hay archivo local, usar Pro para análisis profundo
        if file_path:
            return MODEL_PRO, []
        
        # Si hay URL o necesita búsqueda web, usar Flash con herramientas
        if url or self._needs_web_search(query):
            tools = []
            if self._has_google_search():
                tools.append("Google Search")
            # URL Context no está disponible en la versión actual
            # if url:
            #     tools.append("URL Context")
            return MODEL_FLASH, tools
        
        # Para consultas generales, usar Flash
        return MODEL_FLASH, ["Google Search"] if self._has_google_search() else []
    
    def _needs_web_search(self, query: str) -> bool:
        """Determinar si la consulta necesita búsqueda web"""
        web_indicators = [
            "precio", "cotización", "noticias", "últimas", "actual", "hoy",
            "mercado", "tendencia", "análisis", "previsión", "tesla", "apple",
            "bitcoin", "criptomonedas", "bolsa", "dow jones", "nasdaq", "sp500"
        ]
        return any(indicator in query.lower() for indicator in web_indicators)
    
    def _has_google_search(self) -> bool:
        """Verificar si Google Search está disponible"""
        # Esta función verificaría si las herramientas de búsqueda están disponibles
        return True  # Por simplicidad, asumimos que están disponibles
    
    def _read_file_content(self, file_path: str) -> str:
        """Leer contenido de archivo"""
        try:
            # Detectar tipo de archivo
            mime_type, _ = mimetypes.guess_type(file_path)
            
            if mime_type and mime_type.startswith('text/'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif mime_type and mime_type.startswith('image/'):
                return f"[IMAGEN: {os.path.basename(file_path)}]"
            else:
                return f"[ARCHIVO: {os.path.basename(file_path)}]"
                
        except Exception as e:
            return f"[ERROR LEYENDO ARCHIVO: {str(e)}]"
    
    def _make_gemini_request(self, model: str, prompt: str, system_prompt: str, tools: List[str]) -> Dict[str, Any]:
        """Hacer petición a Gemini"""
        try:
            # Configurar herramientas si están disponibles
            request_tools = []
            if "Google Search" in tools:
                request_tools.append(types.Tool(google_search=types.GoogleSearch()))
            # Nota: URLContext no está disponible en la versión actual de la API
            # Se omite por ahora hasta que esté disponible
            
            # Hacer la petición
            if request_tools:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        tools=request_tools
                    )
                )
            else:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt
                    )
                )
            
            return {
                "response": response.text,
                "model_used": model,
                "tools_used": [tool for tool in tools if tool != "URL Context"],  # Filtrar URL Context
                "success": True
            }
            
        except Exception as e:
            return {
                "response": f"Error en la petición: {str(e)}",
                "model_used": model,
                "tools_used": tools,
                "success": False,
                "error": str(e)
            }
    
    def process_query(self, message: str, file_path: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        """Procesar consulta del usuario"""
        try:
            # Generar ID de sesión
            session_id = str(uuid.uuid4())
            
            # Elegir modelo y herramientas
            model, tools = self._choose_model_and_tools(message, file_path, url)
            
            # Preparar prompt
            prompt = message
            
            # Agregar contenido de archivo si existe
            if file_path:
                file_content = self._read_file_content(file_path)
                prompt = f"{message}\n\nContenido del archivo:\n{file_content}"
                print(f"🧠 [Pro]: Análisis profundo")
            else:
                print(f"⚡ [Flash]: Procesando consulta")
            
            # Agregar URL si existe
            if url:
                prompt = f"{message}\n\nURL a analizar: {url}"
            
            # Seleccionar prompt del sistema
            system_prompt = PRO_SYSTEM_PROMPT if model == MODEL_PRO else FLASH_SYSTEM_PROMPT
            
            # Hacer petición a Gemini
            result = self._make_gemini_request(model, prompt, system_prompt, tools)
            
            # Preparar respuesta
            response = {
                "response": result["response"],
                "model_used": result["model_used"],
                "tools_used": result["tools_used"],
                "metadata": {
                    "processing_type": "pro_deep_analysis" if model == MODEL_PRO else "flash_rapid_analysis"
                },
                "urls_processed": [url] if url else [],
                "token_usage": {
                    "input_tokens": len(prompt.split()) * 1.3,  # Estimación
                    "output_tokens": len(result["response"].split()) * 1.3,  # Estimación
                    "total_tokens": len(prompt.split()) * 1.3 + len(result["response"].split()) * 1.3
                },
                "session_id": session_id
            }
            
            # Guardar sesión
            self.sessions[session_id] = {
                "query": message,
                "response": result["response"],
                "model": model,
                "tools": tools
            }
            
            return response
            
        except Exception as e:
            traceback.print_exc()
            return {
                "response": f"Error procesando consulta: {str(e)}",
                "model_used": "error",
                "tools_used": [],
                "metadata": {"error": str(e)},
                "urls_processed": [],
                "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "session_id": str(uuid.uuid4())
            }
