"""Utilidades para normalizar informes generados por el agente.

Este módulo elimina claves vacías o nulas y garantiza que el JSON
cumpla con el esquema exigido por el servicio generador de PDF.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportValidationError(ValueError):
    """Señala que el informe no puede normalizarse al esquema requerido."""


_DOCUMENT_ALLOWED_KEYS = {"title", "author", "subject"}
_CONTENT_ALLOWED_KEYS = {
    "type",
    "text",
    "style",
    "height",
    "path",
    "caption",
    "width",
    "headers",
    "rows",
    "items",
    "supabase",
}
_SUPABASE_ALLOWED_KEYS = {
    "bucket",
    "path",
    "public",
    "expires_in",
    "use_url",
    "transform",
}
_SUPABASE_TRANSFORM_ALLOWED_KEYS = {
    "width",
    "height",
    "quality",
    "resize",
    "format",
}

_IMAGE_PX_THRESHOLD = 50.0
_IMAGE_PX_PER_INCH = 96.0
_MAX_IMAGE_INCHES = 10.0
_DEFAULT_IMAGE_WIDTH_INCHES = 6.0
_MAX_TRANSFORM_WIDTH_PX = 1600
_IMAGE_ASPECT_RATIO = 16.0 / 9.0


def _sanitize_image_dimension(value: float) -> float:
    number = float(value)
    if number <= 0:
        return _DEFAULT_IMAGE_WIDTH_INCHES

    if number > _IMAGE_PX_THRESHOLD:
        number = number / _IMAGE_PX_PER_INCH

    if number > _MAX_IMAGE_INCHES:
        number = _MAX_IMAGE_INCHES

    return number


def normalize_report_for_schema(report: Dict[str, Any]) -> Dict[str, Any]:
    """Devuelve una copia saneada del informe conforme al esquema JSON.

    Args:
        report: Diccionario generado por el agente bajo la clave ``report``.

    Returns:
        Nuevo diccionario con sólo las claves y valores válidos.

    Raises:
        ReportValidationError: si faltan campos obligatorios o el formato es inválido.
    """

    if not isinstance(report, dict):
        raise ReportValidationError("El informe debe ser un objeto JSON (dict).")

    file_name = report.get("fileName")
    if not isinstance(file_name, str) or not file_name.strip():
        raise ReportValidationError("El informe debe incluir 'fileName' como cadena válida.")

    raw_content = report.get("content")
    if not isinstance(raw_content, list):
        raise ReportValidationError("El informe debe incluir 'content' como lista.")

    normalized: Dict[str, Any] = {"fileName": file_name}

    document = report.get("document")
    document_payload = _sanitize_document(document)
    if document_payload:
        normalized["document"] = document_payload

    normalized_content: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_content):
        sanitized_item = _sanitize_content_item(item)
        if sanitized_item is None:
            logger.warning(
                "Se descartó el bloque de contenido %s por no cumplir con el esquema.", idx
            )
            continue
        normalized_content.append(sanitized_item)

    normalized["content"] = normalized_content

    return normalized


def ensure_image_sources(
    report: Dict[str, Any],
    *,
    bucket: Optional[str] = None,
    prefix: Optional[str] = None,
    transform_width: Optional[int] = None,
) -> Dict[str, Any]:
    """Adjunta metadatos de Supabase a imágenes y fija dimensiones seguras."""

    if not isinstance(report, dict):
        return report

    if not bucket:
        return report

    safe_transform_width = None
    if transform_width is not None and transform_width > 0:
        safe_transform_width = min(int(transform_width), _MAX_TRANSFORM_WIDTH_PX)

    content = report.get("content")
    if not isinstance(content, list):
        return report

    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "image":
            continue

        path = block.get("path")
        if not isinstance(path, str) or not path.strip():
            continue

        normalized_path = path.strip()
        if prefix:
            normalized_path = f"{prefix.rstrip('/')}/{normalized_path.lstrip('/')}"

        width_value = block.get("width")
        width_inches = None
        if isinstance(width_value, (int, float)) and width_value > 0:
            width_inches = _sanitize_image_dimension(width_value)

        width_inches = width_inches or _DEFAULT_IMAGE_WIDTH_INCHES
        block["width"] = float(width_inches)

        # Forzar relación de aspecto 16:9
        target_height_inches = width_inches / _IMAGE_ASPECT_RATIO
        if target_height_inches > _MAX_IMAGE_INCHES:
            target_height_inches = _MAX_IMAGE_INCHES
        block["height"] = float(target_height_inches)

        supabase_payload: Dict[str, Any] = {
            "bucket": bucket,
            "path": normalized_path,
        }

        if safe_transform_width:
            supabase_payload["transform"] = {
                "width": safe_transform_width,
                "resize": "contain",
            }

        block["supabase"] = supabase_payload

    return report


def _sanitize_document(document: Any) -> Dict[str, str]:
    if not isinstance(document, dict):
        return {}

    clean: Dict[str, str] = {}
    for key in _DOCUMENT_ALLOWED_KEYS:
        value = document.get(key)
        if isinstance(value, str) and value.strip():
            clean[key] = value

    return clean


def _sanitize_content_item(item: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None

    content_type = item.get("type")
    if not isinstance(content_type, str) or not content_type.strip():
        return None

    clean: Dict[str, Any] = {"type": content_type}

    for key in _CONTENT_ALLOWED_KEYS - {"type"}:
        value = item.get(key)
        if value is None:
            continue

        if key in {"text", "style", "path"}:
            if isinstance(value, str):
                clean[key] = value

        elif key == "caption":
            if isinstance(value, str) and value.strip():
                clean[key] = value

        elif key in {"height", "width"}:
            if isinstance(value, (int, float)):
                number = float(value)
                if number <= 0:
                    continue
                if content_type == "image":
                    number = _sanitize_image_dimension(number)
                clean[key] = number

        elif key == "headers":
            headers = _sanitize_string_list(value)
            if headers:
                clean[key] = headers

        elif key == "rows":
            rows = _sanitize_rows(value)
            if rows:
                clean[key] = rows

        elif key == "items":
            items_list = _sanitize_items(value)
            if items_list:
                clean[key] = items_list

        elif key == "supabase":
            supabase_obj = _sanitize_supabase_reference(value)
            if supabase_obj:
                clean[key] = supabase_obj

    if content_type == "image":
        clean.pop("headers", None)
        clean.pop("rows", None)
        clean.pop("items", None)

    return clean


def _sanitize_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for element in value:
        if isinstance(element, str) and element.strip():
            result.append(element)
    return result


def _sanitize_rows(value: Any) -> List[List[Any]]:
    if not isinstance(value, list):
        return []
    rows: List[List[Any]] = []
    for row in value:
        if isinstance(row, list):
            rows.append([cell for cell in row])
    return rows


def _sanitize_items(value: Any) -> List[Any]:
    if not isinstance(value, list):
        return []
    sanitized: List[Any] = []
    for element in value:
        if element is None:
            continue
        if isinstance(element, (str, int, float, bool)):
            sanitized.append(element)
        elif isinstance(element, dict):
            cleaned_dict = _prune_nulls_dict(element)
            if cleaned_dict:
                sanitized.append(cleaned_dict)
        elif isinstance(element, list):
            sanitized.append([sub for sub in element if sub is not None])
    return sanitized


def _sanitize_supabase_reference(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None

    bucket = value.get("bucket")
    path = value.get("path")
    if not isinstance(bucket, str) or not isinstance(path, str):
        return None

    sanitized: Dict[str, Any] = {"bucket": bucket, "path": path}

    for optional_key in ("public", "use_url"):
        optional_value = value.get(optional_key)
        if isinstance(optional_value, bool):
            sanitized[optional_key] = optional_value

    expires_in = value.get("expires_in")
    if isinstance(expires_in, int):
        sanitized["expires_in"] = expires_in

    transform = value.get("transform")
    transform_payload = _sanitize_supabase_transform(transform)
    if transform_payload:
        sanitized["transform"] = transform_payload

    return sanitized


def _sanitize_supabase_transform(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    sanitized: Dict[str, Any] = {}
    for key in _SUPABASE_TRANSFORM_ALLOWED_KEYS:
        field_value = value.get(key)
        if field_value is None:
            continue
        if key in {"width", "height", "quality"} and isinstance(field_value, int):
            sanitized[key] = field_value
        elif key == "resize" and isinstance(field_value, str):
            sanitized[key] = field_value
        elif key == "format" and isinstance(field_value, str):
            sanitized[key] = field_value
    return sanitized


def _prune_nulls_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, dict):
            nested = _prune_nulls_dict(value)
            if nested:
                result[key] = nested
        elif isinstance(value, list):
            result[key] = [elem for elem in value if elem is not None]
        else:
            result[key] = value
    return result


__all__ = [
    "normalize_report_for_schema",
    "ReportValidationError",
    "ensure_image_sources",
]
