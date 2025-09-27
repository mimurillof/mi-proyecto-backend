"""Cliente para invocar el servicio externo de generación de PDF."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

try:
    from config import settings  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    settings = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60.0


def _resolve_config(config: Optional[Any] = None) -> Any:
    """Devuelve el objeto de configuración a utilizar."""
    if config is not None:
        return config
    if settings is not None:
        return settings
    return None


def trigger_pdf_generation_task(
    report_payload: Dict[str, Any],
    storage_path: Optional[str] = None,
    *,
    config: Optional[Any] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Invoca el servicio remoto para generar el PDF del informe.

    Este método está pensado para ejecutarse en tareas de fondo.
    """
    if not isinstance(report_payload, dict):
        logger.error("El payload del informe no es un diccionario válido: %s", type(report_payload))
        return

    cfg = _resolve_config(config)
    service_url = None
    api_key = None

    if cfg is not None:
        service_url = getattr(cfg, "PDF_SERVICE_URL", None)
        api_key = getattr(cfg, "INTERNAL_API_KEY", None)

    service_url = (service_url or os.getenv("PDF_SERVICE_URL") or "").strip()
    api_key = (api_key or os.getenv("INTERNAL_API_KEY") or "").strip()

    if not service_url or not api_key:
        logger.error(
            "Variables de entorno PDF_SERVICE_URL o INTERNAL_API_KEY no configuradas; se omite la generación de PDF."
        )
        return

    headers = {
        "X-API-KEY": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload: Dict[str, Any] = {
        "json_data": report_payload,
        "no_upload": False,
        "log_level": "INFO",
    }

    if storage_path:
        payload["supabase_json_path"] = storage_path

    try:
        json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        logger.exception("No se pudo serializar el payload para el servicio de PDF")
        return

    try:
        response = httpx.post(service_url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        logger.info("Generación de PDF solicitada correctamente: %s", response.text)
    except httpx.HTTPError as exc:
        response_obj = getattr(exc, "response", None)
        status = getattr(response_obj, "status_code", None)
        body_preview = None
        if response_obj is not None:
            try:
                body_preview = response_obj.text[:500]
            except Exception:  # pragma: no cover
                body_preview = None
        logger.error(
            "Error al invocar el servicio de generación de PDF (status: %s, endpoint: %s, body: %s)",
            status,
            service_url,
            body_preview,
        )
    except Exception as exc:  # pragma: no cover - precaución general
        logger.exception("Fallo inesperado al invocar el servicio de PDF: %s", exc)
