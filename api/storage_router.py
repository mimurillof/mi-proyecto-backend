"""Router para exponer acceso autorizado a Supabase Storage."""

from __future__ import annotations

import io
import mimetypes
from typing import List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from auth.dependencies import get_current_user
from db_models.models import User

try:
    from services.supabase_storage import get_supabase_storage
    from config import settings

    supabase_storage = get_supabase_storage(settings)
    SUPABASE_ENABLED = supabase_storage is not None
except Exception as exc:  # pragma: no cover - fallback cuando no hay credenciales
    SUPABASE_ENABLED = False
    supabase_storage = None


router = APIRouter(prefix="/api/storage", tags=["Storage"])

DEFAULT_EXTENSIONS: Set[str] = {"json", "md", "png"}
MAX_LIST_LIMIT = 100


def _ensure_supabase_available() -> None:
    if not SUPABASE_ENABLED or not supabase_storage:
        raise HTTPException(
            status_code=503,
            detail="Servicio de Supabase Storage no está disponible",
        )


def _parse_extensions_param(extensions: Optional[str]) -> Set[str]:
    if not extensions:
        return DEFAULT_EXTENSIONS

    parsed: Set[str] = set()
    for ext in extensions.split(","):
        normalized = ext.strip().lower().lstrip(".")
        if normalized:
            parsed.add(normalized)

    return parsed or DEFAULT_EXTENSIONS


@router.get("/files")
async def list_user_storage_files(
    extensions: Optional[str] = Query(
        None,
        description=(
            "Extensiones permitidas separadas por coma. Ej: json,md,png. "
            "Por defecto se usan json, md y png."
        ),
    ),
    limit: int = Query(50, ge=1, le=MAX_LIST_LIMIT),
    current_user: User = Depends(get_current_user),
):
    """Lista archivos filtrados por extensión dentro del bucket del usuario."""

    _ensure_supabase_available()

    allowed_exts = {
        f".{ext}"
        for ext in _parse_extensions_param(extensions)
    }

    files = supabase_storage.list_user_files(  # type: ignore[attr-defined]
        user_id=str(current_user.user_id),
        allowed_extensions=allowed_exts,
        limit=limit,
    )

    return {
        "status": "success",
        "user_id": str(current_user.user_id),
        "total": len(files),
        "files": files,
    }


@router.get("/download")
async def download_user_storage_file(
    filename: str = Query(..., description="Nombre del archivo a descargar"),
    current_user: User = Depends(get_current_user),
):
    """Descarga un archivo del bucket del usuario autenticado."""

    _ensure_supabase_available()

    try:
        file_bytes, metadata = supabase_storage.download_user_file(  # type: ignore[attr-defined]
            user_id=str(current_user.user_id),
            filename=filename,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - errores de red u otros
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    mime_type = (
        metadata.get("content_type")
        if isinstance(metadata, dict)
        else None
    ) or mimetypes.guess_type(filename)[0] or "application/octet-stream"

    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }

    return StreamingResponse(io.BytesIO(file_bytes), media_type=mime_type, headers=headers)


@router.get("/metadata")
async def get_user_storage_file_metadata(
    filename: str = Query(..., description="Nombre del archivo a consultar"),
    current_user: User = Depends(get_current_user),
):
    """Obtiene metadatos del archivo del usuario autenticado."""

    _ensure_supabase_available()

    try:
        info = supabase_storage.get_user_file_info(  # type: ignore[attr-defined]
            user_id=str(current_user.user_id),
            filename=filename,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "status": "success",
        "user_id": str(current_user.user_id),
        "file": info,
    }


