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
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime

from urllib.parse import quote

import httpx

try:
    from supabase import create_client, Client  # type: ignore
except ImportError:  # pragma: no cover
    create_client = None  # type: ignore
    Client = Any  # type: ignore

REPORT_FILENAME = "estructura_informe.json"

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
        else:
            # Fallback a variables de entorno
            self.supabase_url = os.getenv("SUPABASE_URL")
            self.supabase_service_role = os.getenv("SUPABASE_SERVICE_ROLE")
            self.bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "portfolio-files")
        
        if not self.supabase_url or not self.supabase_service_role:
            raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_ROLE deben estar configurados en el .env o config")
        
        if create_client is None:
            raise ImportError("La librería 'supabase' no está instalada en el entorno actual.")

        # Crear cliente de Supabase con service role key
        self.client: Client = create_client(self.supabase_url, self.supabase_service_role)  # type: ignore[arg-type]
        
        logger.info(f"SupabaseStorageService inicializado - Bucket: {self.bucket_name}")
    
    @staticmethod
    def _normalize_prefix(prefix: Optional[str]) -> str:
        if not prefix:
            return ""
        return str(prefix).strip().strip("/")

    def get_user_base_path(self, user_id: str) -> str:
        """Construye el path base para un usuario específico.

        Args:
            user_id: ID del usuario

        Returns:
            str: Path base del usuario en el bucket (ej: "user_123")
        """
        if not user_id:
            raise ValueError("user_id es requerido para construir rutas en Supabase")
        return str(user_id).strip()

    def get_metrics_file_path(self, user_id: str, filename: str = "api_response_B.json") -> str:
        """Construye el path completo del archivo en Supabase Storage para un usuario.

        Args:
            user_id: ID del usuario
            filename: Nombre del archivo (por defecto: api_response_B.json)

        Returns:
            str: Path completo en el bucket (ej: "user_123/api_response_B.json")
        """
        user_path = self.get_user_base_path(user_id)
        return f"{user_path}/{filename}"

    def get_report_file_path(self, user_id: str, filename: str = REPORT_FILENAME) -> str:
        """Obtiene la ruta completa del informe estratégico en Storage para un usuario.
        
        Args:
            user_id: ID del usuario
            filename: Nombre del archivo de reporte
            
        Returns:
            str: Path completo en el bucket
        """
        user_path = self.get_user_base_path(user_id)
        return f"{user_path}/{filename}"

    def save_portfolio_report_json(self, user_id: str, datos_informe: Dict[str, Any]) -> Dict[str, str]:
        """Guarda o actualiza el informe JSON del agente en Supabase Storage.

        Args:
            user_id: ID del usuario propietario del informe
            datos_informe: Diccionario con el informe generado por el agente.

        Returns:
            dict: Resultado de la operación, indicando éxito o error.
        """
        if not isinstance(datos_informe, dict):
            logger.error("El informe recibido no es un diccionario válido")
            return {
                "status": "error",
                "message": "El parámetro 'datos_informe' debe ser un diccionario.",
            }

        try:
            payload = json.dumps(datos_informe, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            logger.exception("No se pudo serializar el informe a JSON")
            return {
                "status": "error",
                "message": f"No se pudo serializar el informe a JSON: {exc}",
            }

        storage_path = self.get_report_file_path(user_id)
        base_url = (self.supabase_url or "").rstrip("/")
        if not base_url:
            logger.error("SUPABASE_URL no está configurado correctamente para la carga REST")
            return {
                "status": "error",
                "message": "SUPABASE_URL no está configurado para la carga REST.",
            }

        object_path = quote(storage_path, safe="")
        upload_url = f"{base_url}/storage/v1/object/{self.bucket_name}/{object_path}"
        headers = {
            "Authorization": f"Bearer {self.supabase_service_role}",
            "apikey": self.supabase_service_role,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = httpx.put(upload_url, content=payload, headers=headers, timeout=30.0)
        except Exception as exc:
            logger.exception("Error al realizar la petición PUT a Supabase Storage")
            return {
                "status": "error",
                "message": f"Error al subir el informe a Supabase: {exc}",
            }

        if response.status_code not in (200, 201):
            logger.error(
                "Supabase devolvió un código inesperado (%s): %s",
                response.status_code,
                response.text,
            )
            return {
                "status": "error",
                "message": f"Supabase devolvió un error durante la carga: {response.status_code} {response.text}",
            }

        logger.info("Informe estratégico guardado en Supabase mediante REST: %s", storage_path)
        return {
            "status": "success",
            "message": "El informe ha sido actualizado correctamente en Supabase.",
            "path": storage_path,
        }

    def save_portfolio_report_json_custom(self, user_id: str, datos_informe: Dict[str, Any], filename: str) -> Dict[str, str]:
        """Guarda o actualiza un archivo JSON en Supabase Storage con nombre personalizado.

        Args:
            user_id: ID del usuario propietario del informe
            datos_informe: Diccionario con los datos a guardar.
            filename: Nombre del archivo a guardar.

        Returns:
            dict: Resultado de la operación, indicando éxito o error.
        """
        if not isinstance(datos_informe, dict):
            logger.error("Los datos recibidos no son un diccionario válido")
            return {
                "status": "error",
                "message": "El parámetro 'datos_informe' debe ser un diccionario.",
            }

        try:
            payload = json.dumps(datos_informe, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            logger.exception("No se pudo serializar los datos a JSON")
            return {
                "status": "error",
                "message": f"No se pudo serializar los datos a JSON: {exc}",
            }

        storage_path = self.get_report_file_path(user_id, filename)
        base_url = (self.supabase_url or "").rstrip("/")
        if not base_url:
            logger.error("SUPABASE_URL no está configurado correctamente para la carga REST")
            return {
                "status": "error",
                "message": "SUPABASE_URL no está configurado para la carga REST.",
            }

        object_path = quote(storage_path, safe="")
        upload_url = f"{base_url}/storage/v1/object/{self.bucket_name}/{object_path}"
        headers = {
            "Authorization": f"Bearer {self.supabase_service_role}",
            "apikey": self.supabase_service_role,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = httpx.put(upload_url, content=payload, headers=headers, timeout=30.0)
        except Exception as exc:
            logger.exception("Error al realizar la petición PUT a Supabase Storage")
            return {
                "status": "error",
                "message": f"Error al subir los datos a Supabase: {exc}",
            }

        if response.status_code not in (200, 201):
            logger.error(
                "Supabase devolvió un código inesperado (%s): %s",
                response.status_code,
                response.text,
            )
            return {
                "status": "error",
                "message": f"Supabase devolvió un error durante la carga: {response.status_code} {response.text}",
            }

        logger.info("Archivo JSON guardado en Supabase mediante REST: %s", storage_path)
        return {
            "status": "success",
            "message": f"El archivo {filename} ha sido guardado correctamente en Supabase.",
            "path": storage_path,
        }

    def read_report_json(self, user_id: str, filename: str = REPORT_FILENAME) -> Dict[str, Any]:
        """Lee un archivo JSON de informes desde Supabase Storage.
        
        Args:
            user_id: ID del usuario propietario del informe
            filename: Nombre del archivo de reporte
            
        Returns:
            Dict con el contenido del JSON
        """
        file_path = self.get_report_file_path(user_id, filename)

        try:
            response = self.client.storage.from_(self.bucket_name).download(file_path)
        except Exception as exc:  # pragma: no cover - errores de red externos
            logger.exception("Error al descargar informe %s desde Supabase", file_path)
            raise Exception(f"No se pudo descargar el archivo {file_path}: {exc}") from exc

        if not response:
            logger.error("Supabase devolvió respuesta vacía al descargar %s", file_path)
            raise Exception(f"Archivo {file_path} vacío o inexistente en Supabase")

        try:
            data = json.loads(response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.exception("Error al decodificar JSON del archivo %s", file_path)
            raise Exception(f"No se pudo decodificar el JSON del archivo {file_path}: {exc}") from exc

        logger.info("Archivo %s leído desde Supabase Storage", file_path)
        return data
    
    def list_user_files(
        self,
        user_id: str,
        allowed_extensions: Optional[Set[str]] = None,
        include_metadata: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Lista archivos en la carpeta del usuario con filtrado por extensión.

        Args:
            user_id: ID del usuario propietario.
            allowed_extensions: Conjunto de extensiones permitidas (con punto), p.ej. {".json"}.
            include_metadata: Incluir información adicional del objeto.
            limit: Límite máximo de elementos a devolver (None = sin límite).

        Returns:
            Lista de diccionarios con información básica del archivo.
        """
        try:
            normalized_exts: Optional[Set[str]] = None
            if allowed_extensions:
                normalized_exts = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in allowed_extensions}

            user_path = self.get_user_base_path(user_id)
            response = self.client.storage.from_(self.bucket_name).list(user_path)

            files: List[Dict[str, Any]] = []
            for index, file_data in enumerate(response or []):
                if limit is not None and index >= limit:
                    break

                name = file_data.get("name") or ""
                ext = os.path.splitext(name)[1].lower()

                if normalized_exts and ext not in normalized_exts:
                    continue

                item: Dict[str, Any] = {
                    "name": name,
                    "ext": ext.lstrip("."),
                    "full_path": f"{user_path}/{name}",
                }

                if include_metadata:
                    metadata = file_data.get("metadata")
                    if isinstance(metadata, dict):
                        item["size"] = metadata.get("size")
                        item["content_type"] = metadata.get("mimetype")
                    item["updated_at"] = file_data.get("updated_at")

                files.append(item)

            return files
        except Exception as exc:
            logger.error("Error al listar archivos del usuario %s: %s", user_id, exc)
            return []

    def download_user_file(self, user_id: str, filename: str) -> Tuple[bytes, Dict[str, Any]]:
        """Descarga un archivo específico del usuario desde Supabase Storage.

        Returns:
            Tuple con los bytes del archivo y metadatos (cuando existan).
        """
        file_path = self.get_metrics_file_path(user_id, filename)

        try:
            response = self.client.storage.from_(self.bucket_name).download(file_path)
            if not response:
                raise FileNotFoundError(f"Archivo {file_path} vacío o inexistente en Supabase")

            metadata: Dict[str, Any] = {}
            try:
                metadata = self.get_user_file_info(user_id, filename)
            except Exception:
                metadata = {}

            return response, metadata
        except Exception as exc:
            logger.error("Error al descargar archivo %s para usuario %s: %s", filename, user_id, exc)
            raise

    async def read_metrics_json(self, user_id: str, filename: str = "api_response_B.json") -> Dict[str, Any]:
        """
        Lee un archivo JSON de métricas desde Supabase Storage
        
        Args:
            user_id: ID del usuario propietario del archivo
            filename: Nombre del archivo JSON a leer
            
        Returns:
            Dict: Contenido del archivo JSON parseado
            
        Raises:
            Exception: Si el archivo no se puede leer o parsear
        """
        try:
            file_path = self.get_metrics_file_path(user_id, filename)
            
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
    
    def create_signed_url(self, user_id: str, filename: str = "api_response_B.json", expires_in: int = 3600) -> str:
        """
        Crea una URL firmada para acceso directo a un archivo en Supabase Storage
        
        Args:
            user_id: ID del usuario propietario del archivo
            filename: Nombre del archivo
            expires_in: Tiempo de expiración en segundos (por defecto: 1 hora)
            
        Returns:
            str: URL firmada para acceso directo al archivo
            
        Raises:
            Exception: Si no se puede generar la URL firmada
        """
        try:
            file_path = self.get_metrics_file_path(user_id, filename)
            
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
    
    async def read_html_chart(self, user_id: str, chart_name: str) -> str:
        """
        Lee un archivo HTML de gráfico desde Supabase Storage
        
        Args:
            user_id: ID del usuario propietario del gráfico
            chart_name: Nombre del tipo de gráfico (cumulative_returns, etc.)
            
        Returns:
            str: Contenido HTML del gráfico
            
        Raises:
            Exception: Si el archivo no se puede leer
        """
        try:
            filename = self.get_chart_filename(chart_name)
            file_path = self.get_metrics_file_path(user_id, filename)
            
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
            'efficient_frontier': 'efficient_frontier.html',  # Corregido según Supabase Storage
            'portfolio_growth': 'portfolio_growth.html',  # Corregido según Supabase Storage
            'monte_carlo_distribution': 'monte_carlo_distribution.html',
            'monte_carlo_trajectories': 'monte_carlo_simulation.html',  # Corregido según Supabase Storage
            'msr_portfolio': 'msr_treemap.html'  # Nuevo gráfico agregado
        }
        
        filename = chart_mapping.get(chart_name)
        if not filename:
            raise ValueError(f"Tipo de gráfico no reconocido: {chart_name}")
        
        return filename
    
    def create_chart_signed_url(self, user_id: str, chart_name: str, expires_in: int = 3600) -> str:
        """
        Crea una URL firmada para acceso directo a un gráfico HTML
        
        Args:
            user_id: ID del usuario propietario del gráfico
            chart_name: Nombre del tipo de gráfico
            expires_in: Tiempo de expiración en segundos
            
        Returns:
            str: URL firmada para acceso directo al gráfico
        """
        try:
            filename = self.get_chart_filename(chart_name)
            return self.create_signed_url(user_id, filename, expires_in)
        except Exception as e:
            logger.error(f"Error al crear URL firmada para gráfico {chart_name}: {str(e)}")
            raise Exception(f"Error al crear URL firmada para gráfico: {str(e)}")
    
    def list_chart_files(self, user_id: str) -> list:
        """
        Lista todos los archivos HTML de gráficos disponibles en Supabase Storage para un usuario
        
        Args:
            user_id: ID del usuario propietario de los gráficos
        
        Returns:
            list: Lista de archivos HTML de gráficos disponibles
        """
        try:
            user_path = self.get_user_base_path(user_id)
            response = self.client.storage.from_(self.bucket_name).list(user_path)
            
            # Filtrar solo archivos HTML de gráficos
            chart_files = []
            for file_data in response:
                filename = file_data.get("name", "")
                if filename.endswith(".html") and ("interactivo" in filename or "interactive" in filename):
                    chart_files.append({
                        "name": filename,
                        "size": file_data.get("metadata", {}).get("size") if isinstance(file_data.get("metadata"), dict) else None,
                        "last_modified": file_data.get("updated_at"),
                        "full_path": f"{user_path}/{filename}",
                        "chart_type": self.get_chart_type_from_filename(filename)
                    })
            
            logger.info(f"Encontrados {len(chart_files)} archivos de gráficos HTML en Supabase Storage para usuario {user_id}")
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
    
    def get_user_file_info(self, user_id: str, filename: str) -> Dict[str, Any]:
        """Obtiene información detallada de un archivo del usuario."""
        try:
            user_path = self.get_user_base_path(user_id)
            response = self.client.storage.from_(self.bucket_name).list(user_path)

            file_info = None
            for item in response or []:
                if item.get("name") == filename:
                    file_info = item
                    break

            if not file_info:
                raise FileNotFoundError(f"Archivo {filename} no encontrado para usuario {user_id}")

            metadata = file_info.get("metadata") if isinstance(file_info.get("metadata"), dict) else {}
            file_path = self.get_metrics_file_path(user_id, filename)

            return {
                "name": file_info.get("name"),
                "size": metadata.get("size"),
                "last_modified": file_info.get("updated_at"),
                "content_type": metadata.get("mimetype"),
                "full_path": file_path,
            }
        except Exception as exc:
            logger.error("Error al obtener información del archivo %s para usuario %s: %s", filename, user_id, exc)
            raise

    def get_file_info(self, user_id: str, filename: str = "api_response_B.json") -> Dict[str, Any]:
        """Compatibilidad retro: alias de get_user_file_info con filename por defecto."""
        return self.get_user_file_info(user_id, filename)
    
    def list_metrics_files(self, user_id: str) -> list:
        """
        Lista todos los archivos de métricas disponibles en el directorio del usuario
        
        Args:
            user_id: ID del usuario propietario de los archivos
        
        Returns:
            list: Lista de archivos JSON de métricas disponibles
        """
        try:
            user_path = self.get_user_base_path(user_id)
            response = self.client.storage.from_(self.bucket_name).list(user_path)
            
            # Filtrar solo archivos JSON de métricas
            metrics_files = []
            for file_data in response:
                filename = file_data.get("name", "")
                if filename.endswith(".json") and ("api_response" in filename or "metrics" in filename):
                    metrics_files.append({
                        "name": filename,
                        "size": file_data.get("metadata", {}).get("size"),
                        "last_modified": file_data.get("updated_at"),
                        "full_path": f"{user_path}/{filename}"
                    })
            
            logger.info(f"Encontrados {len(metrics_files)} archivos de métricas en Supabase Storage para usuario {user_id}")
            return metrics_files
            
        except Exception as e:
            logger.error(f"Error al listar archivos de métricas: {str(e)}")
            return []
    
    def health_check(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifica la conectividad y estado del servicio de Supabase Storage
        
        Args:
            user_id: ID del usuario (opcional) para verificar su carpeta específica
        
        Returns:
            Dict: Estado del servicio y información de conectividad
        """
        try:
            # Intentar listar archivos como test de conectividad
            test_path = self.get_user_base_path(user_id) if user_id else ""
            self.client.storage.from_(self.bucket_name).list(test_path)
            
            return {
                "status": "healthy",
                "bucket": self.bucket_name,
                "user_id": user_id,
                "test_path": test_path,
                "supabase_url": self.supabase_url,
                "timestamp": datetime.now().isoformat(),
                "message": "Conexión con Supabase Storage exitosa"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "bucket": self.bucket_name,
                "user_id": user_id,
                "supabase_url": self.supabase_url,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "message": "Error al conectar con Supabase Storage"
            }

    def save_json_file(self, user_id: str, filename: str, data: Dict[str, Any]) -> Dict[str, str]:
        """Guarda un archivo JSON en la carpeta del usuario en Supabase Storage.

        Args:
            user_id: ID del usuario propietario del archivo
            filename: Nombre del archivo JSON (ej: 'agente.json')
            data: Diccionario con los datos a guardar

        Returns:
            dict: Resultado de la operación, indicando éxito o error.
        """
        if not isinstance(data, dict):
            logger.error("Los datos recibidos no son un diccionario válido")
            return {
                "status": "error",
                "message": "El parámetro 'data' debe ser un diccionario.",
            }

        try:
            payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        except (TypeError, ValueError) as exc:
            logger.exception("No se pudo serializar los datos a JSON")
            return {
                "status": "error",
                "message": f"No se pudo serializar los datos a JSON: {exc}",
            }

        storage_path = self.get_metrics_file_path(user_id, filename)
        base_url = (self.supabase_url or "").rstrip("/")
        if not base_url:
            logger.error("SUPABASE_URL no está configurado correctamente para la carga REST")
            return {
                "status": "error",
                "message": "SUPABASE_URL no está configurado para la carga REST.",
            }

        object_path = quote(storage_path, safe="")
        upload_url = f"{base_url}/storage/v1/object/{self.bucket_name}/{object_path}"
        headers = {
            "Authorization": f"Bearer {self.supabase_service_role}",
            "apikey": self.supabase_service_role,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = httpx.put(upload_url, content=payload, headers=headers, timeout=30.0)
        except Exception as exc:
            logger.exception("Error al realizar la petición PUT a Supabase Storage")
            return {
                "status": "error",
                "message": f"Error al subir el archivo a Supabase: {exc}",
            }

        if response.status_code not in (200, 201):
            logger.error(
                "Supabase devolvió un código inesperado (%s): %s",
                response.status_code,
                response.text,
            )
            return {
                "status": "error",
                "message": f"Supabase devolvió un error durante la carga: {response.status_code} {response.text}",
            }

        logger.info("Archivo JSON guardado en Supabase mediante REST: %s", storage_path)
        return {
            "status": "success",
            "message": f"El archivo {filename} ha sido guardado correctamente en Supabase.",
            "path": storage_path,
        }

    def read_json_file(self, user_id: str, filename: str) -> Dict[str, Any]:
        """Lee un archivo JSON desde la carpeta del usuario en Supabase Storage.
        
        Args:
            user_id: ID del usuario propietario del archivo
            filename: Nombre del archivo JSON a leer
            
        Returns:
            Dict con el contenido del JSON
        """
        file_path = self.get_metrics_file_path(user_id, filename)

        try:
            response = self.client.storage.from_(self.bucket_name).download(file_path)
        except Exception as exc:
            logger.exception("Error al descargar archivo %s desde Supabase", file_path)
            raise Exception(f"No se pudo descargar el archivo {file_path}: {exc}") from exc

        if not response:
            logger.error("Supabase devolvió respuesta vacía al descargar %s", file_path)
            raise Exception(f"Archivo {file_path} vacío o inexistente en Supabase")

        try:
            data = json.loads(response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.exception("Error al decodificar JSON del archivo %s", file_path)
            raise Exception(f"No se pudo decodificar el JSON del archivo {file_path}: {exc}") from exc

        logger.info("Archivo %s leído desde Supabase Storage", file_path)
        return data

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


def guardar_json_en_supabase(user_id: str, datos_informe: Dict[str, Any], config=None) -> Dict[str, str]:
    """Guarda un informe JSON en Supabase Storage usando upsert y manejo en memoria.
    
    Args:
        user_id: ID del usuario propietario del informe
        datos_informe: Datos del informe a guardar
        config: Configuración opcional
        
    Returns:
        Dict con el resultado de la operación
    """
    service = get_supabase_storage(config)
    if service is None:
        return {
            "status": "error",
            "message": "No se pudo inicializar el servicio de Supabase Storage.",
        }

    return service.save_portfolio_report_json(user_id, datos_informe)