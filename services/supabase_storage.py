"""
Servicio para manejar la integración con Supabase Storage
Proporciona funciones para:
- Conectar con Supabase Storage
- Leer archivos JSON de métricas desde el Storage
- Generar Signed URLs para acceso directo a archivos
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from supabase import create_client, Client
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

class SupabaseStorageService:
    """
    Servicio para manejar operaciones con Supabase Storage
    """
    
    def __init__(self, config=None):
        """
        Inicializa el servicio de Supabase Storage con las credenciales del entorno o config
        """
        # Si se pasa un config, usarlo; sino, intentar cargar desde variables de entorno
        if config:
            self.supabase_url = config.SUPABASE_URL
            self.supabase_service_role = config.SUPABASE_SERVICE_ROLE
            self.bucket_name = config.SUPABASE_BUCKET_NAME or "portfolio-files"
            self.base_prefix = config.SUPABASE_BASE_PREFIX or "Graficos"
        else:
            # Fallback a variables de entorno
            self.supabase_url = os.getenv("SUPABASE_URL")
            self.supabase_service_role = os.getenv("SUPABASE_SERVICE_ROLE")
            self.bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "portfolio-files")
            self.base_prefix = os.getenv("SUPABASE_BASE_PREFIX", "Graficos")
        
        if not self.supabase_url or not self.supabase_service_role:
            raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_ROLE deben estar configurados en el .env o config")
        
        # Crear cliente de Supabase con service role key
        self.client: Client = create_client(self.supabase_url, self.supabase_service_role)
        
        logger.info(f"SupabaseStorageService inicializado - Bucket: {self.bucket_name}, Prefix: {self.base_prefix}")
    
    def get_metrics_file_path(self, filename: str = "api_response_B.json") -> str:
        """
        Construye el path completo del archivo en Supabase Storage
        
        Args:
            filename: Nombre del archivo (por defecto: api_response_B.json)
            
        Returns:
            str: Path completo en el bucket
        """
        return f"{self.base_prefix}/{filename}"
    
    async def read_metrics_json(self, filename: str = "api_response_B.json") -> Dict[str, Any]:
        """
        Lee un archivo JSON de métricas desde Supabase Storage
        
        Args:
            filename: Nombre del archivo JSON a leer
            
        Returns:
            Dict: Contenido del archivo JSON parseado
            
        Raises:
            Exception: Si el archivo no se puede leer o parsear
        """
        try:
            file_path = self.get_metrics_file_path(filename)
            
            # Descargar el archivo desde Supabase Storage
            response = self.client.storage.from_(self.bucket_name).download(file_path)
            
            if not response:
                raise Exception(f"No se pudo descargar el archivo {file_path}")
            
            # Decodificar bytes a string y parsear JSON
            json_content = response.decode('utf-8')
            data = json.loads(json_content)
            
            logger.info(f"Archivo {file_path} leído exitosamente desde Supabase Storage")
            return data
            
        except Exception as e:
            logger.error(f"Error al leer archivo JSON desde Supabase Storage: {str(e)}")
            raise Exception(f"Error al leer métricas desde Supabase: {str(e)}")
    
    def create_signed_url(self, filename: str = "api_response_B.json", expires_in: int = 3600) -> str:
        """
        Crea una URL firmada para acceso directo a un archivo en Supabase Storage
        
        Args:
            filename: Nombre del archivo
            expires_in: Tiempo de expiración en segundos (por defecto: 1 hora)
            
        Returns:
            str: URL firmada para acceso directo al archivo
            
        Raises:
            Exception: Si no se puede generar la URL firmada
        """
        try:
            file_path = self.get_metrics_file_path(filename)
            
            # Crear URL firmada
            response = self.client.storage.from_(self.bucket_name).create_signed_url(file_path, expires_in)
            
            # Extraer la URL firmada de la respuesta
            signed_url = response.get("signedURL") or response.get("signed_url")
            
            if not signed_url:
                raise Exception("No se retornó una URL firmada")
            
            logger.info(f"URL firmada creada para {file_path}, expira en {expires_in} segundos")
            return signed_url
            
        except Exception as e:
            logger.error(f"Error al crear URL firmada: {str(e)}")
            raise Exception(f"Error al crear URL firmada: {str(e)}")
    
    async def read_html_chart(self, chart_name: str) -> str:
        """
        Lee un archivo HTML de gráfico desde Supabase Storage
        
        Args:
            chart_name: Nombre del tipo de gráfico (cumulative_returns, etc.)
            
        Returns:
            str: Contenido HTML del gráfico
            
        Raises:
            Exception: Si el archivo no se puede leer
        """
        try:
            filename = self.get_chart_filename(chart_name)
            file_path = self.get_metrics_file_path(filename)
            
            # Descargar el archivo HTML desde Supabase Storage
            response = self.client.storage.from_(self.bucket_name).download(file_path)
            
            if not response:
                raise Exception(f"No se pudo descargar el archivo HTML {file_path}")
            
            # Decodificar bytes a string (contenido HTML)
            html_content = response.decode('utf-8')
            
            logger.info(f"Archivo HTML {file_path} leído exitosamente desde Supabase Storage")
            return html_content
            
        except Exception as e:
            logger.error(f"Error al leer archivo HTML desde Supabase Storage: {str(e)}")
            raise Exception(f"Error al leer gráfico desde Supabase: {str(e)}")
    
    def get_chart_filename(self, chart_name: str) -> str:
        """
        Mapea el nombre del gráfico a su archivo correspondiente en Supabase Storage
        
        Args:
            chart_name: Nombre del tipo de gráfico
            
        Returns:
            str: Nombre del archivo correspondiente
        """
        # Mapeo de nombres de gráficos a archivos en Supabase
        chart_mapping = {
            'cumulative_returns': 'rendimiento_acumulado_interactivo.html',
            'composition_donut': 'donut_chart_interactivo.html',
            'correlation_matrix': 'matriz_correlacion_interactiva.html',
            'drawdown_underwater': 'drawdown_underwater_interactivo.html',
            'breakdown_chart': 'breakdown_chart_interactivo.html',
            'efficient_frontier': 'efficient_frontier_interactive.html',
            'portfolio_growth': 'portfolio_growth_interactive.html',
            'monte_carlo_distribution': 'monte_carlo_distribution.html',
            'monte_carlo_trajectories': 'monte_carlo_trajectories.html'
        }
        
        filename = chart_mapping.get(chart_name)
        if not filename:
            raise ValueError(f"Tipo de gráfico no reconocido: {chart_name}")
        
        return filename
    
    def create_chart_signed_url(self, chart_name: str, expires_in: int = 3600) -> str:
        """
        Crea una URL firmada para acceso directo a un gráfico HTML
        
        Args:
            chart_name: Nombre del tipo de gráfico
            expires_in: Tiempo de expiración en segundos
            
        Returns:
            str: URL firmada para acceso directo al gráfico
        """
        try:
            filename = self.get_chart_filename(chart_name)
            return self.create_signed_url(filename, expires_in)
        except Exception as e:
            logger.error(f"Error al crear URL firmada para gráfico {chart_name}: {str(e)}")
            raise Exception(f"Error al crear URL firmada para gráfico: {str(e)}")
    
    def list_chart_files(self) -> list:
        """
        Lista todos los archivos HTML de gráficos disponibles en Supabase Storage
        
        Returns:
            list: Lista de archivos HTML de gráficos disponibles
        """
        try:
            response = self.client.storage.from_(self.bucket_name).list(self.base_prefix)
            
            # Filtrar solo archivos HTML de gráficos
            chart_files = []
            for file_data in response:
                filename = file_data.get("name", "")
                if filename.endswith(".html") and ("interactivo" in filename or "interactive" in filename):
                    chart_files.append({
                        "name": filename,
                        "size": file_data.get("metadata", {}).get("size") if isinstance(file_data.get("metadata"), dict) else None,
                        "last_modified": file_data.get("updated_at"),
                        "full_path": self.get_metrics_file_path(filename),
                        "chart_type": self.get_chart_type_from_filename(filename)
                    })
            
            logger.info(f"Encontrados {len(chart_files)} archivos de gráficos HTML en Supabase Storage")
            return chart_files
            
        except Exception as e:
            logger.error(f"Error al listar archivos de gráficos: {str(e)}")
            return []
    
    def get_chart_type_from_filename(self, filename: str) -> Optional[str]:
        """
        Determina el tipo de gráfico basado en el nombre del archivo
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            str: Tipo de gráfico o None si no se puede determinar
        """
        # Mapeo inverso de archivos a tipos de gráfico
        filename_to_chart = {
            'rendimiento_acumulado_interactivo.html': 'cumulative_returns',
            'donut_chart_interactivo.html': 'composition_donut',
            'matriz_correlacion_interactiva.html': 'correlation_matrix',
            'drawdown_underwater_interactivo.html': 'drawdown_underwater',
            'breakdown_chart_interactivo.html': 'breakdown_chart',
            'efficient_frontier_interactive.html': 'efficient_frontier',
            'portfolio_growth_interactive.html': 'portfolio_growth',
            'monte_carlo_distribution.html': 'monte_carlo_distribution',
            'monte_carlo_trajectories.html': 'monte_carlo_trajectories'
        }
        
        return filename_to_chart.get(filename)
    
    def get_file_info(self, filename: str = "api_response_B.json") -> Dict[str, Any]:
        """
        Obtiene información sobre un archivo en Supabase Storage
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Dict: Información del archivo (tamaño, fecha de modificación, etc.)
        """
        try:
            file_path = self.get_metrics_file_path(filename)
            
            # Listar archivos en el directorio para obtener metadatos
            response = self.client.storage.from_(self.bucket_name).list(self.base_prefix)
            
            # Buscar el archivo específico
            file_info = None
            for file_data in response:
                if file_data.get("name") == filename:
                    file_info = file_data
                    break
            
            if not file_info:
                raise Exception(f"Archivo {filename} no encontrado en {self.base_prefix}")
            
            return {
                "name": file_info.get("name"),
                "size": file_info.get("metadata", {}).get("size"),
                "last_modified": file_info.get("updated_at"),
                "content_type": file_info.get("metadata", {}).get("mimetype"),
                "full_path": file_path
            }
            
        except Exception as e:
            logger.error(f"Error al obtener información del archivo: {str(e)}")
            raise Exception(f"Error al obtener información del archivo: {str(e)}")
    
    def list_metrics_files(self) -> list:
        """
        Lista todos los archivos de métricas disponibles en el directorio base
        
        Returns:
            list: Lista de archivos JSON de métricas disponibles
        """
        try:
            response = self.client.storage.from_(self.bucket_name).list(self.base_prefix)
            
            # Filtrar solo archivos JSON de métricas
            metrics_files = []
            for file_data in response:
                filename = file_data.get("name", "")
                if filename.endswith(".json") and ("api_response" in filename or "metrics" in filename):
                    metrics_files.append({
                        "name": filename,
                        "size": file_data.get("metadata", {}).get("size"),
                        "last_modified": file_data.get("updated_at"),
                        "full_path": self.get_metrics_file_path(filename)
                    })
            
            logger.info(f"Encontrados {len(metrics_files)} archivos de métricas en Supabase Storage")
            return metrics_files
            
        except Exception as e:
            logger.error(f"Error al listar archivos de métricas: {str(e)}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica la conectividad y estado del servicio de Supabase Storage
        
        Returns:
            Dict: Estado del servicio y información de conectividad
        """
        try:
            # Intentar listar archivos como test de conectividad
            self.client.storage.from_(self.bucket_name).list(self.base_prefix)
            
            return {
                "status": "healthy",
                "bucket": self.bucket_name,
                "base_prefix": self.base_prefix,
                "supabase_url": self.supabase_url,
                "timestamp": datetime.now().isoformat(),
                "message": "Conexión con Supabase Storage exitosa"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "bucket": self.bucket_name,
                "base_prefix": self.base_prefix,
                "supabase_url": self.supabase_url,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "message": "Error al conectar con Supabase Storage"
            }

# Función para crear instancia con configuración
def create_supabase_storage_service(config=None):
    """
    Crea una instancia del servicio de Supabase Storage
    
    Args:
        config: Objeto de configuración (opcional)
        
    Returns:
        SupabaseStorageService: Instancia del servicio
    """
    try:
        return SupabaseStorageService(config)
    except Exception as e:
        logger.error(f"Error al crear servicio de Supabase Storage: {e}")
        return None

# Variable para almacenar la instancia (será inicializada bajo demanda)
_supabase_storage_instance = None

def get_supabase_storage(config=None):
    """
    Obtiene la instancia del servicio de Supabase Storage (singleton)
    """
    global _supabase_storage_instance
    if _supabase_storage_instance is None:
        _supabase_storage_instance = create_supabase_storage_service(config)
    return _supabase_storage_instance