# src/daily_generation_control.py

import os
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json


class DailyGenerationController:
    """
    Sistema centralizado para el control de generaciones diarias de reportes e imágenes.
    
    Funcionalidades:
    - Controla que solo se genere un reporte/imagen por tipo por día
    - Sobreescribe archivos del mismo día si se generan múltiples veces
    - Preserva archivos de días diferentes
    - Gestiona automáticamente la limpieza de archivos antiguos
    - Proporciona métodos para consultar el estado de las generaciones
    """
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Registro de tipos de archivos que el sistema debe controlar
        self.file_types = {
            # Reportes
            "markdown_report": {
                "pattern": "reporte_portafolio_*.md",
                "prefix": "reporte_portafolio",
                "description": "Reporte de análisis en Markdown"
            },
            "api_response": {
                "pattern": "api_response_*.json",
                "prefix": "api_response",
                "description": "Respuesta API en JSON"
            },
            
            # Gráficos de interactive_charts
            "rendimiento_acumulado": {
                "pattern": "rendimiento_acumulado_*.*",
                "prefix": "rendimiento_acumulado",
                "description": "Gráfico de rendimiento acumulado"
            },
            "drawdown": {
                "pattern": "drawdown_underwater_*.*",
                "prefix": "drawdown_underwater",
                "description": "Gráfico de drawdown"
            },
            "correlacion": {
                "pattern": "matriz_correlacion_*.*",
                "prefix": "matriz_correlacion",
                "description": "Heatmap de correlación"
            },
            
            # Gráficos de asset_classifier
            "donut_chart": {
                "pattern": "donut_chart_*.*",
                "prefix": "donut_chart",
                "description": "Gráfico donut de clasificación"
            },
            "breakdown_chart": {
                "pattern": "breakdown_chart_*.*",
                "prefix": "breakdown_chart",
                "description": "Gráfico breakdown de clasificación"
            },
            "clasificacion_activos": {
                "pattern": "clasificacion_activos_*.*",
                "prefix": "clasificacion_activos",
                "description": "Gráfico HTML de clasificación de activos"
            },
            "desglose_activos": {
                "pattern": "desglose_activos_*.*",
                "prefix": "desglose_activos",
                "description": "Gráfico HTML de desglose de activos"
            }
        }
    
    def _get_today_string(self) -> str:
        """Obtiene el string de la fecha actual en formato YYYYMMDD"""
        return datetime.now().strftime("%Y%m%d")
    
    def _extract_date_from_filename(self, filename: str) -> Optional[str]:
        """
        Extrae la fecha de un nombre de archivo con formato: prefix_YYYYMMDD_HHMMSS.ext
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Fecha en formato YYYYMMDD o None si no se puede extraer
        """
        try:
            # Buscar patrón YYYYMMDD_HHMMSS
            parts = filename.split('_')
            for i, part in enumerate(parts):
                if len(part) == 8 and part.isdigit():
                    # Verificar que el siguiente part sea HHMMSS
                    if i + 1 < len(parts):
                        next_part = parts[i + 1].split('.')[0]  # Remover extensión
                        if len(next_part) == 6 and next_part.isdigit():
                            return part
            return None
        except:
            return None
    
    def _get_existing_files_for_type(self, file_type: str) -> List[Tuple[str, str]]:
        """
        Obtiene todos los archivos existentes para un tipo específico
        
        Args:
            file_type: Tipo de archivo según self.file_types
            
        Returns:
            Lista de tuplas (filepath, date_string)
        """
        if file_type not in self.file_types:
            return []
        
        pattern = self.file_types[file_type]["pattern"]
        search_pattern = str(self.output_dir / pattern)
        
        files_with_dates = []
        for filepath in glob.glob(search_pattern):
            filename = os.path.basename(filepath)
            date_str = self._extract_date_from_filename(filename)
            if date_str:
                files_with_dates.append((filepath, date_str))
        
        return files_with_dates
    
    def _clean_same_day_files(self, file_type: str) -> List[str]:
        """
        Limpia archivos del mismo día para un tipo específico
        
        Args:
            file_type: Tipo de archivo
            
        Returns:
            Lista de archivos eliminados
        """
        today = self._get_today_string()
        existing_files = self._get_existing_files_for_type(file_type)
        
        today_files = [filepath for filepath, date_str in existing_files if date_str == today]
        removed_files = []
        
        for filepath in today_files:
            try:
                os.remove(filepath)
                removed_files.append(filepath)
            except OSError as e:
                print(f"⚠️ Advertencia: No se pudo eliminar {filepath}: {e}")
        
        return removed_files
    
    def generate_daily_filename(self, file_type: str, extension: str = None) -> str:
        """
        Genera un nombre de archivo único para el día actual
        
        Args:
            file_type: Tipo de archivo según self.file_types
            extension: Extensión del archivo (opcional)
            
        Returns:
            Nombre de archivo con formato: prefix_YYYYMMDD_HHMMSS.ext
        """
        if file_type not in self.file_types:
            raise ValueError(f"Tipo de archivo no reconocido: {file_type}")
        
        prefix = self.file_types[file_type]["prefix"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if extension:
            if not extension.startswith('.'):
                extension = '.' + extension
            return f"{prefix}_{timestamp}{extension}"
        else:
            return f"{prefix}_{timestamp}"
    
    def get_daily_filepath(self, file_type: str, extension: str) -> str:
        """
        Obtiene la ruta completa para un archivo del día actual
        
        Args:
            file_type: Tipo de archivo
            extension: Extensión del archivo
            
        Returns:
            Ruta completa del archivo
        """
        filename = self.generate_daily_filename(file_type, extension)
        return str(self.output_dir / filename)
    
    def prepare_daily_file(self, file_type: str, extension: str) -> str:
        """
        Prepara un archivo para generación diaria: limpia archivos del mismo día
        y devuelve la ruta del nuevo archivo
        
        Args:
            file_type: Tipo de archivo
            extension: Extensión del archivo
            
        Returns:
            Ruta del archivo preparado
        """
        # Limpiar archivos del mismo día
        removed_files = self._clean_same_day_files(file_type)
        
        if removed_files:
            print(f"🧹 Limpiando archivos del mismo día para {file_type}:")
            for file in removed_files:
                print(f"   - Eliminado: {os.path.basename(file)}")
        
        # Obtener ruta del nuevo archivo
        filepath = self.get_daily_filepath(file_type, extension)
        
        return filepath
    
    def get_reports_history(self) -> Dict[str, List[Dict]]:
        """
        Obtiene el historial de reportes generados por tipo y fecha
        
        Returns:
            Diccionario con el historial organizado por tipo de archivo
        """
        history = {}
        
        for file_type in self.file_types:
            files_with_dates = self._get_existing_files_for_type(file_type)
            
            # Organizar por fecha
            date_groups = {}
            for filepath, date_str in files_with_dates:
                if date_str not in date_groups:
                    date_groups[date_str] = []
                
                # Obtener información del archivo
                file_info = {
                    "filepath": filepath,
                    "filename": os.path.basename(filepath),
                    "size": os.path.getsize(filepath),
                    "created": datetime.fromtimestamp(os.path.getctime(filepath)).strftime("%Y-%m-%d %H:%M:%S")
                }
                date_groups[date_str].append(file_info)
            
            history[file_type] = dict(sorted(date_groups.items(), reverse=True))
        
        return history
    
    def cleanup_old_reports(self, days_to_keep: int = 30) -> Dict[str, List[str]]:
        """
        Limpia reportes antiguos, manteniendo solo los últimos N días
        
        Args:
            days_to_keep: Número de días a mantener
            
        Returns:
            Diccionario con los archivos eliminados por tipo
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime("%Y%m%d")
        
        removed_files = {}
        
        for file_type in self.file_types:
            files_with_dates = self._get_existing_files_for_type(file_type)
            
            old_files = [filepath for filepath, date_str in files_with_dates if date_str < cutoff_str]
            
            removed_files[file_type] = []
            for filepath in old_files:
                try:
                    os.remove(filepath)
                    removed_files[file_type].append(filepath)
                except OSError as e:
                    print(f"⚠️ Advertencia: No se pudo eliminar {filepath}: {e}")
        
        return removed_files
    
    def check_daily_reports_exist(self) -> Dict[str, bool]:
        """
        Verifica qué tipos de reportes ya existen para el día actual
        
        Returns:
            Diccionario con el estado de existencia por tipo
        """
        today = self._get_today_string()
        status = {}
        
        for file_type in self.file_types:
            files_with_dates = self._get_existing_files_for_type(file_type)
            today_files = [filepath for filepath, date_str in files_with_dates if date_str == today]
            status[file_type] = len(today_files) > 0
        
        return status
    
    def show_daily_reports_status(self) -> None:
        """
        Muestra el estado actual de los reportes diarios
        """
        print("📊 ESTADO DE REPORTES DIARIOS")
        print("=" * 50)
        
        today = self._get_today_string()
        print(f"📅 Fecha actual: {today}")
        print()
        
        status = self.check_daily_reports_exist()
        
        for file_type, exists in status.items():
            description = self.file_types[file_type]["description"]
            icon = "✅" if exists else "❌"
            print(f"{icon} {description}: {'Generado' if exists else 'No generado'}")
        
        print()
        print("💡 Consejo: Los archivos del mismo día se sobreescriben automáticamente.")
        print("📁 Archivos guardados en:", self.output_dir)
    
    def get_summary_stats(self) -> Dict:
        """
        Obtiene estadísticas resumidas del sistema
        
        Returns:
            Diccionario con estadísticas
        """
        history = self.get_reports_history()
        
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "files_by_type": {},
            "dates_with_reports": set(),
            "today_files": 0
        }
        
        today = self._get_today_string()
        
        for file_type, date_groups in history.items():
            type_count = 0
            type_size = 0
            
            for date_str, files in date_groups.items():
                stats["dates_with_reports"].add(date_str)
                
                for file_info in files:
                    type_count += 1
                    type_size += file_info["size"]
                    
                    if date_str == today:
                        stats["today_files"] += 1
            
            stats["files_by_type"][file_type] = {
                "count": type_count,
                "size_bytes": type_size
            }
            
            stats["total_files"] += type_count
            stats["total_size_bytes"] += type_size
        
        stats["unique_dates"] = len(stats["dates_with_reports"])
        stats["dates_with_reports"] = sorted(list(stats["dates_with_reports"]), reverse=True)
        
        return stats


# Instancia global para uso en todo el proyecto
daily_controller = DailyGenerationController()
