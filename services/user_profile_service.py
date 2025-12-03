"""
Servicio para manejar el perfil de usuario y la imagen de perfil desde Supabase Storage.

Este servicio proporciona:
- Generación de URLs firmadas para la imagen de perfil
- Avatares por defecto según el género
- Upload de imagen de perfil a Supabase Storage
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple
from urllib.parse import quote
import uuid
import httpx

from config import settings

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = Any

logger = logging.getLogger(__name__)

# Usar el mismo bucket de portfolio-files para imágenes de perfil
# La estructura es: portfolio-files/{user_id}/profile.{ext}
PROFILE_BUCKET_NAME = "portfolio-files"

# URLs de avatares por defecto según género
DEFAULT_AVATARS = {
    "male": "https://api.dicebear.com/7.x/avataaars/svg?seed=male&backgroundColor=b6e3f4",
    "female": "https://api.dicebear.com/7.x/avataaars/svg?seed=female&backgroundColor=ffdfbf",
    "other": "https://api.dicebear.com/7.x/avataaars/svg?seed=neutral&backgroundColor=d1d4f9",
    "prefer_not_to_say": "https://api.dicebear.com/7.x/avataaars/svg?seed=default&backgroundColor=c0aede",
    "default": "https://api.dicebear.com/7.x/initials/svg?seed=U&backgroundColor=94a3b8"
}

# Extensiones de imagen permitidas
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_IMAGE_SIZE_MB = 5
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


class UserProfileService:
    """
    Servicio para manejar perfiles de usuario e imágenes de perfil.
    """
    
    def __init__(self, config=None):
        """
        Inicializa el servicio de perfil de usuario.
        
        Args:
            config: Configuración opcional (usa settings por defecto)
        """
        self.config = config or settings
        self.supabase_url = self.config.SUPABASE_URL
        self.supabase_service_role = self.config.SUPABASE_SERVICE_ROLE
        self.bucket_name = PROFILE_BUCKET_NAME
        
        self.client: Optional[Client] = None
        
        if self.supabase_url and self.supabase_service_role:
            if create_client:
                try:
                    self.client = create_client(self.supabase_url, self.supabase_service_role)
                    logger.info(f"UserProfileService inicializado - Bucket: {self.bucket_name}")
                except Exception as e:
                    logger.warning(f"No se pudo inicializar cliente Supabase: {e}")
        else:
            logger.warning("Credenciales de Supabase no configuradas para UserProfileService")
    
    def get_user_profile_image_path(self, user_id: str) -> str:
        """
        Construye el path de la imagen de perfil de un usuario en Storage.
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            str: Path en el bucket (ej: "user_123/profile.jpg")
        """
        return f"{user_id}/profile"
    
    def get_default_avatar_url(self, gender: Optional[str] = None, first_name: Optional[str] = None) -> str:
        """
        Obtiene la URL del avatar por defecto según el género del usuario.
        
        Args:
            gender: Género del usuario (male, female, other, prefer_not_to_say)
            first_name: Nombre del usuario para generar avatar con iniciales
            
        Returns:
            str: URL del avatar por defecto
        """
        if first_name:
            # Avatar con iniciales del nombre
            initial = first_name[0].upper() if first_name else "U"
            return f"https://api.dicebear.com/7.x/initials/svg?seed={initial}&backgroundColor=94a3b8"
        
        if gender and gender in DEFAULT_AVATARS:
            return DEFAULT_AVATARS[gender]
        
        return DEFAULT_AVATARS["default"]
    
    async def get_profile_image_url(
        self, 
        user_id: str, 
        profile_image_path: Optional[str] = None,
        gender: Optional[str] = None,
        first_name: Optional[str] = None,
        expires_in: int = 3600
    ) -> Tuple[str, bool]:
        """
        Obtiene la URL de la imagen de perfil del usuario.
        
        Si el usuario tiene imagen en Storage, retorna una URL firmada.
        Si no tiene imagen, retorna un avatar por defecto.
        
        Args:
            user_id: UUID del usuario
            profile_image_path: Path de la imagen en Storage (si existe)
            gender: Género del usuario para avatar por defecto
            first_name: Nombre para generar avatar con iniciales
            expires_in: Tiempo de expiración de la URL firmada (segundos)
            
        Returns:
            Tuple[str, bool]: (URL de la imagen, es_default)
        """
        # Si hay una imagen de perfil almacenada, intentar obtener URL firmada
        if profile_image_path and self.client:
            try:
                signed_url = await self._create_signed_url(profile_image_path, expires_in)
                if signed_url:
                    return signed_url, False
            except Exception as e:
                logger.warning(f"Error al obtener URL firmada para {profile_image_path}: {e}")
        
        # Retornar avatar por defecto
        default_url = self.get_default_avatar_url(gender, first_name)
        return default_url, True
    
    async def _create_signed_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Crea una URL firmada para acceder a un archivo en Supabase Storage.
        
        Args:
            file_path: Path del archivo en el bucket
            expires_in: Tiempo de expiración en segundos
            
        Returns:
            str: URL firmada o None si hay error
        """
        if not self.client:
            return None
        
        try:
            response = self.client.storage.from_(self.bucket_name).create_signed_url(
                file_path, 
                expires_in
            )
            return response.get("signedURL") or response.get("signed_url")
        except Exception as e:
            logger.error(f"Error creando URL firmada: {e}")
            return None
    
    async def upload_profile_image(
        self, 
        user_id: str, 
        file_content: bytes, 
        content_type: str,
        filename: str
    ) -> Dict[str, Any]:
        """
        Sube una imagen de perfil a Supabase Storage.
        
        Args:
            user_id: UUID del usuario
            file_content: Contenido del archivo en bytes
            content_type: Tipo MIME del archivo
            filename: Nombre original del archivo
            
        Returns:
            Dict con el resultado de la operación
        """
        if not self.client:
            return {
                "success": False,
                "message": "Servicio de almacenamiento no disponible"
            }
        
        # Validar extensión
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return {
                "success": False,
                "message": f"Extensión no permitida. Usa: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            }
        
        # Validar tamaño
        if len(file_content) > MAX_IMAGE_SIZE_BYTES:
            return {
                "success": False,
                "message": f"Imagen demasiado grande. Máximo: {MAX_IMAGE_SIZE_MB}MB"
            }
        
        try:
            # Construir path del archivo
            storage_path = f"{user_id}/profile{ext}"
            
            # Eliminar imagen anterior si existe
            await self._delete_existing_profile_images(user_id)
            
            # Subir nueva imagen usando REST API
            base_url = (self.supabase_url or "").rstrip("/")
            object_path = quote(storage_path, safe="")
            upload_url = f"{base_url}/storage/v1/object/{self.bucket_name}/{object_path}"
            
            headers = {
                "Authorization": f"Bearer {self.supabase_service_role}",
                "apikey": self.supabase_service_role,
                "Content-Type": content_type,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    upload_url, 
                    content=file_content, 
                    headers=headers, 
                    timeout=30.0
                )
            
            if response.status_code not in (200, 201):
                logger.error(f"Error subiendo imagen: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"Error al subir imagen: {response.status_code}"
                }
            
            logger.info(f"Imagen de perfil subida exitosamente: {storage_path}")
            return {
                "success": True,
                "message": "Imagen de perfil actualizada correctamente",
                "path": storage_path
            }
            
        except Exception as e:
            logger.error(f"Error subiendo imagen de perfil: {e}")
            return {
                "success": False,
                "message": f"Error al subir imagen: {str(e)}"
            }
    
    async def _delete_existing_profile_images(self, user_id: str) -> None:
        """
        Elimina imágenes de perfil existentes del usuario.
        
        Args:
            user_id: UUID del usuario
        """
        if not self.client:
            return
        
        try:
            # Listar archivos en la carpeta del usuario
            files = self.client.storage.from_(self.bucket_name).list(user_id)
            
            # Eliminar archivos que empiecen con "profile"
            for file_info in files or []:
                filename = file_info.get("name", "")
                if filename.startswith("profile"):
                    file_path = f"{user_id}/{filename}"
                    self.client.storage.from_(self.bucket_name).remove([file_path])
                    logger.info(f"Imagen anterior eliminada: {file_path}")
                    
        except Exception as e:
            logger.warning(f"Error al limpiar imágenes anteriores: {e}")
    
    async def delete_profile_image(self, user_id: str) -> Dict[str, Any]:
        """
        Elimina la imagen de perfil del usuario.
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            Dict con el resultado de la operación
        """
        if not self.client:
            return {
                "success": False,
                "message": "Servicio de almacenamiento no disponible"
            }
        
        try:
            await self._delete_existing_profile_images(user_id)
            return {
                "success": True,
                "message": "Imagen de perfil eliminada correctamente"
            }
        except Exception as e:
            logger.error(f"Error eliminando imagen de perfil: {e}")
            return {
                "success": False,
                "message": f"Error al eliminar imagen: {str(e)}"
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica el estado del servicio.
        
        Returns:
            Dict con información de estado
        """
        return {
            "service": "UserProfileService",
            "status": "healthy" if self.client else "degraded",
            "bucket": self.bucket_name,
            "supabase_configured": bool(self.supabase_url and self.supabase_service_role),
            "client_initialized": bool(self.client)
        }


# Singleton del servicio
_user_profile_service: Optional[UserProfileService] = None


def get_user_profile_service() -> UserProfileService:
    """
    Obtiene la instancia singleton del servicio de perfil de usuario.
    
    Returns:
        UserProfileService: Instancia del servicio
    """
    global _user_profile_service
    if _user_profile_service is None:
        _user_profile_service = UserProfileService()
    return _user_profile_service
