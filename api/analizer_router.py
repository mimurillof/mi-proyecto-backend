"""
Endpoints de backend para integrar el script existente `analizer_script.py` (sin modificarlo).

- Permite ejecutar el script bajo demanda
- Expone el JSON/MD generados y lista/serve archivos HTML/PNG/JSON/MD

Nota: No se hacen cambios en el script; solo se orquesta su ejecuciÃ³n y el servido de outputs.
"""

from __future__ import annotations

import os
import sys
import json
import time
import glob
import shlex
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from auth.dependencies import get_current_user_from_query
from db_models.models import User
from config import settings
from services.supabase_storage import get_supabase_storage


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analizer", tags=["Portfolio Analizer v2"])


# Directorio base del backend
BACKEND_ROOT = Path(__file__).resolve().parent.parent

# Ruta a la carpeta del analizador v2 (con espacio en el nombre, mantener exacto)
ANALYZER_DIR = BACKEND_ROOT / "porfolio analizer v2"
SCRIPT_PATH = ANALYZER_DIR / "analizer_script.py"

# Archivos de salida esperados (generados por el script)
RESULTS_JSON_NAME = "portfolio_analysis_results.json"
REPORT_MD_NAME = "reporte_financiero_exhaustivo.md"


def _ensure_environment() -> None:
    if not ANALYZER_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Directorio del analizador no encontrado: {ANALYZER_DIR}")
    if not SCRIPT_PATH.exists():
        raise HTTPException(status_code=404, detail=f"Script no encontrado: {SCRIPT_PATH}")


def _safe_path_in_analyzer_dir(filename: str) -> Path:
    """Previene path traversal asegurando que el archivo estÃ© dentro del directorio del analizador."""
    candidate = (ANALYZER_DIR / filename).resolve()
    if not str(candidate).startswith(str(ANALYZER_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Ruta invÃ¡lida")
    return candidate


def _list_files_by_ext() -> Dict[str, List[str]]:
    patterns = {
        "html": "*.html",
        "png": "*.png",
        "json": "*.json",
        "md": "*.md",
    }
    result: Dict[str, List[str]] = {k: [] for k in patterns}
    for kind, pattern in patterns.items():
        files = sorted([p.name for p in ANALYZER_DIR.glob(pattern)], reverse=True)
        result[kind] = files
    return result


@router.get("/health")
async def health() -> Dict[str, Any]:
    try:
        # No fallar si el directorio no existe; reportar estado informativo
        if not ANALYZER_DIR.exists() or not SCRIPT_PATH.exists():
            return {
                "status": "missing",
                "analyzer_dir": str(ANALYZER_DIR),
                "script_path": str(SCRIPT_PATH),
                "has_results_json": False,
                "has_report_md": False,
                "files": {"html": [], "png": [], "json": [], "md": []},
            }

        files = _list_files_by_ext()
        has_json = RESULTS_JSON_NAME in files.get("json", []) or (ANALYZER_DIR / RESULTS_JSON_NAME).exists()
        has_md = REPORT_MD_NAME in files.get("md", []) or (ANALYZER_DIR / REPORT_MD_NAME).exists()
        return {
            "status": "ok",
            "analyzer_dir": str(ANALYZER_DIR),
            "script_path": str(SCRIPT_PATH),
            "has_results_json": has_json,
            "has_report_md": has_md,
            "files": files,
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/run")
async def run_script(timeout_seconds: int = 600) -> Dict[str, Any]:
    """Ejecuta el script de anÃ¡lisis de forma sÃ­ncrona y retorna el estado y resumen de outputs.

    timeout_seconds: lÃ­mite de tiempo para la ejecuciÃ³n (por defecto 10 minutos).
    """
    _ensure_environment()

    # Preparar entorno para ejecuciÃ³n headless (matplotlib) y utf-8
    env = os.environ.copy()
    env.setdefault("MPLBACKEND", "Agg")
    env.setdefault("PYTHONIOENCODING", "UTF-8")
    env.setdefault("PYTHONUTF8", "1")

    start = time.time()

    # Elegir intÃ©rprete de Python para ejecutar el script
    # 1) Preferir el venv local si existe
    venv_python_win = BACKEND_ROOT / "venv" / "Scripts" / "python.exe"
    venv_python_posix = BACKEND_ROOT / "venv" / "bin" / "python"
    if venv_python_win.exists():
        python_exec = str(venv_python_win)
    elif venv_python_posix.exists():
        python_exec = str(venv_python_posix)
    else:
        # 2) Usar el mismo intÃ©rprete de Python que ejecuta FastAPI
        python_exec = sys.executable
    cmd = [python_exec, str(SCRIPT_PATH)]

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            cmd,
            cwd=str(ANALYZER_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tiempo de ejecuciÃ³n excedido")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo al ejecutar script: {e}")

    duration = time.time() - start

    files = _list_files_by_ext()

    response: Dict[str, Any] = {
        "status": "completed" if proc.returncode == 0 else "failed",
        "exit_code": proc.returncode,
        "duration_seconds": round(duration, 2),
        "python_executable": python_exec,
        "virtual_env": os.environ.get("VIRTUAL_ENV"),
        "working_dir": str(ANALYZER_DIR),
        "stdout_tail": proc.stdout.splitlines()[-50:] if proc.stdout else [],
        "stderr_tail": proc.stderr.splitlines()[-50:] if proc.stderr else [],
        "files": files,
    }

    # Adjuntar paths canÃ³nicos a resultados clave si existen
    results_json = ANALYZER_DIR / RESULTS_JSON_NAME
    report_md = ANALYZER_DIR / REPORT_MD_NAME
    if results_json.exists():
        response["results_json_path"] = str(results_json)
    if report_md.exists():
        response["report_md_path"] = str(report_md)

    return response


@router.get("/results")
async def get_results() -> Dict[str, Any]:
    """Devuelve el contenido del JSON de resultados y metadatos del reporte MD si existen."""
    _ensure_environment()
    results: Dict[str, Any] = {"json": None, "report_md": None, "files": _list_files_by_ext()}

    json_path = ANALYZER_DIR / RESULTS_JSON_NAME
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                results["json"] = json.load(f)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Error al leer JSON de resultados: {e}")

    md_path = ANALYZER_DIR / REPORT_MD_NAME
    if md_path.exists():
        # No devolvemos el contenido completo para evitar respuestas muy largas
        results["report_md"] = {
            "filename": md_path.name,
            "path": str(md_path),
            "size_bytes": md_path.stat().st_size,
        }

    if not results["json"] and not results["report_md"]:
        raise HTTPException(status_code=404, detail="No hay resultados disponibles aÃºn")

    return results


@router.get("/list-files")
async def list_files() -> Dict[str, List[str]]:
    # Si la carpeta no existe, devolvemos listas vacÃ­as en vez de fallar
    if not ANALYZER_DIR.exists():
        return {"html": [], "png": [], "json": [], "md": []}
    return _list_files_by_ext()


@router.get("/file/{filename}")
async def get_file(
    filename: str,
    current_user: User = Depends(get_current_user_from_query),
):
    """
    Sirve un archivo HTML desde Supabase Storage especÃ­fico del usuario autenticado.
    Requiere token de autenticaciÃ³n en query parameter (?token=xxx) para acceder a los grÃ¡ficos del portafolio del usuario.
    """
    user_id = str(current_user.user_id)
    logger.info("Sirviendo archivo %s para user_id=%s", filename, user_id)
    
    allowed_ext = {".html", ".png", ".json", ".md"}
    # Construir path local de manera segura, aunque la carpeta no exista
    path = _safe_path_in_analyzer_dir(filename)
    
    if path.suffix.lower() not in allowed_ext:
        raise HTTPException(status_code=400, detail="ExtensiÃ³n no permitida")
    
    # Para archivos HTML, intentar servir desde Supabase Storage primero
    if filename.endswith('.html'):
        try:
            supabase_storage = get_supabase_storage(settings)
            if supabase_storage:
                # Mapear nombres de archivo a los de Supabase Storage
                supabase_filename_mapping = {
                    'efficient_frontier_interactive.html': 'efficient_frontier.html',
                    'portfolio_growth_interactive.html': 'portfolio_growth.html',
                    'monte_carlo_trajectories.html': 'monte_carlo_simulation.html',
                    'msr_portfolio_treemap_original.html': 'msr_treemap.html',
                    'rendimiento_acumulado_interactivo.html': 'rendimiento_acumulado_interactivo.html',
                    'donut_chart_interactivo.html': 'donut_chart_interactivo.html',
                    'matriz_correlacion_interactiva.html': 'matriz_correlacion_interactiva.html',
                    'drawdown_underwater_interactivo.html': 'drawdown_underwater_interactivo.html',
                    'breakdown_chart_interactivo.html': 'breakdown_chart_interactivo.html',
                    'monte_carlo_distribution.html': 'monte_carlo_distribution.html'
                }
                
                # Obtener el nombre correcto en Supabase
                supabase_filename = supabase_filename_mapping.get(filename, filename)
                
                try:
                    # Construir la ruta completa en Supabase usando user_id
                    file_path = f"{user_id}/{supabase_filename}"
                    
                    logger.info("Descargando desde Supabase: %s", file_path)
                    
                    # Descargar el archivo HTML desde Supabase Storage
                    response = supabase_storage.client.storage.from_(supabase_storage.bucket_name).download(file_path)
                    
                    if response:
                        html_content = response.decode('utf-8')
                        logger.info("âœ… Sirviendo %s desde Supabase Storage para user_id=%s", filename, user_id)
                        return HTMLResponse(content=html_content)
                        
                except Exception as supabase_error:
                    logger.warning("âš ï¸ Error Supabase para %s (user_id=%s): %s", filename, user_id, str(supabase_error))
                    # Continuar al fallback local
                    
        except Exception as import_error:
            logger.warning("âš ï¸ Error importando Supabase para %s: %s", filename, str(import_error))
            # Continuar al fallback local
    
    # Fallback: servir archivo local (solo si existe; no requerimos que exista la carpeta base)
    if not path.exists():
        logger.error("âŒ Archivo no encontrado (local ni Supabase): %s para user_id=%s", filename, user_id)
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    logger.info("ðŸ“ Sirviendo %s desde archivos locales (fallback) para user_id=%s", filename, user_id)
    return FileResponse(str(path))



