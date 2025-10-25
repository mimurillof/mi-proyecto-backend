"""
Cliente HTTP para comunicación con el servicio remoto del agente de chat
"""

import httpx
import asyncio
from typing import Optional, Dict, Any, List
from config import settings

class RemoteChatAgentClient:
    """Cliente para comunicarse con el servicio remoto del agente de chat"""
    
    def __init__(self):
        # Usa get_chat_agent_url() para obtener la URL correcta según el entorno
        self.base_url = settings.get_chat_agent_url().rstrip('/')
        self.timeout = settings.CHAT_AGENT_TIMEOUT
        self.retries = settings.CHAT_AGENT_RETRIES
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Hacer request HTTP con reintentos"""
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=f"{self.base_url}{endpoint}",
                        **kwargs
                    )
                    response.raise_for_status()
                    return response.json()
            
            except httpx.TimeoutException:
                if attempt == self.retries:
                    raise Exception(f"Timeout después de {self.retries + 1} intentos")
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial
            
            except httpx.HTTPStatusError as e:
                if attempt == self.retries:
                    raise Exception(f"Error HTTP {e.response.status_code}: {e.response.text}")
                await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                if attempt == self.retries:
                    raise Exception(f"Error de conexión: {str(e)}")
                await asyncio.sleep(2 ** attempt)
        
        raise Exception("Error inesperado en _make_request")
    
    async def health_check(self) -> Dict[str, Any]:
        """Verificar el estado del servicio remoto"""
        return await self._make_request("GET", "/health")
    
    async def process_message(
        self,
        message: str,
        user_id: str,  # ✅ NUEVO: Requerido para multiusuario
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        session_id: Optional[str] = None,
        auth_token: Optional[str] = None  # ✅ NUEVO: Token JWT para acceso a Supabase
    ) -> Dict[str, Any]:
        """Procesar un mensaje con el agente remoto"""
        payload = {
            "message": message,
            "user_id": user_id,  # ✅ Incluir user_id en el payload
            "auth_token": auth_token  # ✅ Incluir auth_token para acceso a archivos del usuario
        }
        
        if file_path:
            payload["file_path"] = file_path
        if url:
            payload["url"] = url
        if session_id:
            payload["session_id"] = session_id
        
        return await self._make_request("POST", "/chat", json=payload)
    
    async def upload_file_chat(
        self,
        message: str,
        user_id: str,  # ✅ NUEVO: Requerido para multiusuario
        file_content: bytes,
        filename: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Chat con archivo adjunto"""
        files = {"file": (filename, file_content)}
        data = {
            "message": message,
            "user_id": user_id  # ✅ Incluir user_id en el payload
        }
        
        if session_id:
            data["session_id"] = session_id
        
        return await self._make_request("POST", "/chat/upload", files=files, data=data)
    
    async def generate_portfolio_report(
        self,
        user_id: str,  # ✅ NUEVO: Requerido para multiusuario
        model_preference: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Solicitar la generación de un informe de portafolio al agente remoto.
        Usa procesamiento asíncrono con polling para evitar timeouts.
        """
        payload: Dict[str, Any] = {
            "user_id": user_id,  # ✅ Incluir user_id en el payload
            "context": context or {},
        }

        if model_preference:
            payload["model_preference"] = model_preference
        if session_id:
            payload["session_id"] = session_id

        # 1. Iniciar generación (responde inmediatamente)
        start_response = await self._make_request(
            "POST",
            "/acciones/generar_informe_portafolio/start",
            json=payload,
            timeout=10.0,  # Solo para iniciar
        )
        
        task_id = start_response.get("task_id")
        if not task_id:
            raise Exception("No se recibió task_id del chat agent")
        
        # 2. Hacer polling hasta que complete
        max_attempts = 60  # 60 intentos * 3 segundos = 3 minutos máximo
        for attempt in range(max_attempts):
            await asyncio.sleep(3)  # Esperar 3 segundos entre polls
            
            try:
                status_response = await self._make_request(
                    "GET",
                    f"/acciones/generar_informe_portafolio/status/{task_id}",
                    timeout=10.0,
                )
                
                status = status_response.get("status")
                
                if status == "completed":
                    # Tarea completada exitosamente
                    return status_response.get("result")
                
                elif status == "error":
                    # Error en la generación
                    error_msg = status_response.get("error", "Error desconocido")
                    raise Exception(f"Error en chat agent: {error_msg}")
                
                # Si está en "pending" o "processing", continuar polling
                
            except Exception as e:
                # Si falla el polling, continuar intentando
                if attempt == max_attempts - 1:
                    raise Exception(f"Timeout esperando resultado del chat agent: {str(e)}")
        
        raise Exception("Timeout: el chat agent no completó la generación en el tiempo esperado")

    async def get_status(self) -> Dict[str, Any]:
        """Obtener estado del agente"""
        return await self._make_request("GET", "/status")
    
    async def create_session(self) -> Dict[str, Any]:
        """Crear nueva sesión"""
        return await self._make_request("POST", "/session")
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Obtener información de sesión"""
        return await self._make_request("GET", f"/session/{session_id}")
    
    async def list_sessions(self) -> Dict[str, Any]:
        """Listar todas las sesiones"""
        return await self._make_request("GET", "/sessions")
    
    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Eliminar una sesión"""
        return await self._make_request("DELETE", f"/session/{session_id}")
    
    async def clear_all_sessions(self) -> Dict[str, Any]:
        """Limpiar todas las sesiones"""
        return await self._make_request("DELETE", "/sessions")

# Instancia global del cliente
remote_agent_client = RemoteChatAgentClient()