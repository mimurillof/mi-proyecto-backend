"""Cliente para leer datos del Portfolio Manager desde el JSON persistido."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List, Union, Set, Tuple, cast

try:
    from zoneinfo import ZoneInfo
    MARKET_TZ = ZoneInfo("America/New_York")
except ImportError:
    # Fallback para Python < 3.9
    import pytz
    MARKET_TZ = pytz.timezone("America/New_York")

from config import settings
from services.supabase_storage import SupabaseStorageService

logger = logging.getLogger(__name__)


def desanitize_filename_for_storage(filename: str) -> str:
    """
    Desanitiza un nombre de archivo que fue sanitizado para Supabase Storage.
    Revierte los reemplazos hechos por sanitize_filename_for_storage() en Portfolio Manager.
    
    Args:
        filename: Nombre de archivo sanitizado (ej: "_CARET_SPX_chart.html")
    
    Returns:
        Nombre de archivo original (ej: "^SPX_chart.html")
    
    Examples:
        >>> desanitize_filename_for_storage("_CARET_SPX_chart.html")
        "^SPX_chart.html"
        >>> desanitize_filename_for_storage("BTC-USD_chart.html")
        "BTC-USD_chart.html"
    """
    # Mapeo inverso de la sanitización
    reverse_replacements = {
        '_CARET_': '^',      # Índices como ^SPX, ^GSPC
        '_LT_': '<',         # Menor que
        '_GT_': '>',         # Mayor que
        '_COLON_': ':',      # Dos puntos
        '_QUOTE_': '"',      # Comillas dobles
        '_BSLASH_': '\\',    # Barra invertida
        '_PIPE_': '|',       # Pipe
        '_QMARK_': '?',      # Signo de interrogación
        '_STAR_': '*',       # Asterisco
    }
    
    desanitized = filename
    for sanitized_token, original_char in reverse_replacements.items():
        desanitized = desanitized.replace(sanitized_token, original_char)
    
    return desanitized


class PortfolioManagerClient:
    """Cliente que entrega datos del Portfolio Manager leyendo el JSON en disco."""

    def __init__(self, user_id: str) -> None:
        """
        Inicializa el cliente del Portfolio Manager para un usuario específico.
        
        Args:
            user_id: ID del usuario para acceder a sus datos en Supabase Storage
        """
        if not user_id:
            raise ValueError("user_id es requerido para inicializar PortfolioManagerClient")
        
        self._user_id = user_id
        self._enabled = settings.PORTFOLIO_MANAGER_ENABLED
        self._refresh_interval = timedelta(minutes=settings.PORTFOLIO_MANAGER_REFRESH_MINUTES or 15)
        self._default_period = settings.PORTFOLIO_MANAGER_DEFAULT_PERIOD
        self._lock = asyncio.Lock()

        self._portfolio_data_path: Path
        self._portfolio_path_candidates: List[Path]

        base_path = Path(__file__).resolve().parent
        backend_root = base_path.parent
        project_root = backend_root.parent
        configured_path = Path(getattr(settings, "PORTFOLIO_DATA_PATH", "Portfolio manager/data/portfolio_data.json"))

        candidates = self._build_portfolio_path_candidates(configured_path, base_path, backend_root, project_root)
        self._portfolio_data_path = self._select_portfolio_path(candidates, project_root)
        self._portfolio_path_candidates = candidates
        logger.debug("Rutas candidatas evaluadas para portfolio_data.json (user_id=%s): %s", user_id, ", ".join(str(p) for p in candidates))

        data_dir = self._portfolio_data_path.parent
        charts_root = data_dir.parent if data_dir else None
        self._charts_dir = charts_root / "charts" if charts_root else data_dir / "charts"

        self._supabase_service: Optional[SupabaseStorageService] = None
        self._supabase_enabled: bool = False
        self._supabase_bucket: str = settings.SUPABASE_BUCKET_NAME or "portfolio-files"
        
        # ✅ ELIMINADOS: prefijos hardcodeados
        # Ya no usamos "Informes" ni "Graficos", ahora usamos {user_id}/

        self._chart_paths: Dict[str, Union[Path, str]] = {}
        self._chart_cache: Dict[str, str] = {}
        self._missing_supabase_charts: Set[str] = set()

        try:
            self._supabase_service = SupabaseStorageService(settings)
            self._supabase_enabled = True
            logger.debug("SupabaseStorageService habilitado para Portfolio Manager (bucket=%s)", self._supabase_bucket)
        except Exception as exc:
            self._supabase_service = None
            self._supabase_enabled = False
            logger.warning("SupabaseStorageService no disponible; se usará el sistema de archivos local. Detalle: %s", exc)

        self._cache: Optional[Dict[str, Any]] = None
        self._summary: Optional[Dict[str, Any]] = None
        self._market: Optional[Dict[str, Any]] = None
        self._last_refresh: Optional[datetime] = None
        self._data_timestamp: Optional[datetime] = None
        self._file_timestamp: Optional[datetime] = None
        self._status: str = "idle"

        self._update_chart_index(None, supabase_asset_files=[])

        if not self._enabled:
            logger.info("Portfolio Manager remoto deshabilitado. Configure PORTFOLIO_MANAGER_ENABLED=true para activar la integración.")

    def _is_market_open(self, now: Optional[datetime] = None) -> bool:
        """Verifica si el mercado de valores está abierto (NYSE/NASDAQ)."""
        try:
            if now:
                if hasattr(now, 'astimezone'):
                    current = now.astimezone(MARKET_TZ)
                else:
                    current = MARKET_TZ.localize(now) if hasattr(MARKET_TZ, 'localize') else now.replace(tzinfo=MARKET_TZ)  # type: ignore[attr-defined]
            else:
                current = datetime.now(MARKET_TZ)
            
            # Fin de semana (sábado=5, domingo=6)
            if current.weekday() >= 5:
                return False
            
            # Horario de mercado: 9:30 AM - 4:00 PM ET
            open_time = current.replace(hour=9, minute=30, second=0, microsecond=0)
            close_time = current.replace(hour=16, minute=0, second=0, microsecond=0)
            
            return open_time <= current <= close_time
        except Exception as e:
            logger.error(f"Error verificando estado del mercado: {e}")
            return False

    def _get_next_market_open(self, now: Optional[datetime] = None) -> datetime:
        """Calcula la próxima apertura del mercado."""
        try:
            if now:
                if hasattr(now, 'astimezone'):
                    current = now.astimezone(MARKET_TZ)
                else:
                    current = MARKET_TZ.localize(now) if hasattr(MARKET_TZ, 'localize') else now.replace(tzinfo=MARKET_TZ)  # type: ignore[attr-defined]
            else:
                current = datetime.now(MARKET_TZ)
            
            # Si es fin de semana, ir al lunes
            if current.weekday() == 5:  # Sábado
                days_ahead = 2
            elif current.weekday() == 6:  # Domingo
                days_ahead = 1
            else:  # Día laboral (lunes-viernes)
                open_time = current.replace(hour=9, minute=30, second=0, microsecond=0)
                if current < open_time:
                    return open_time
                # Si ya pasó el cierre, ir al siguiente día laborable
                days_ahead = 1
                # Si es viernes, saltar al lunes (3 días)
                if current.weekday() == 4:  # Viernes
                    days_ahead = 3
            
            next_day = current + timedelta(days=days_ahead)
            return next_day.replace(hour=9, minute=30, second=0, microsecond=0)
        except Exception as e:
            logger.error(f"Error calculando próxima apertura del mercado: {e}")
            # Fallback: devolver mañana a las 9:30 AM
            tomorrow = datetime.now(MARKET_TZ) + timedelta(days=1)
            return tomorrow.replace(hour=9, minute=30, second=0, microsecond=0)

    def _needs_refresh(self) -> bool:
        if self._cache is None:
            return True
        if not self._data_timestamp:
            return True
        age = datetime.utcnow() - self._data_timestamp
        return age >= self._refresh_interval

    def _get_file_last_modified(self) -> Optional[datetime]:
        if self._supabase_enabled and self._file_timestamp:
            return self._file_timestamp
        try:
            stat = self._portfolio_data_path.stat()
        except Exception:
            return None
        try:
            return datetime.utcfromtimestamp(stat.st_mtime)
        except Exception:
            return None

    @staticmethod
    def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value or not isinstance(value, str):
            return None
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            return None

    @staticmethod
    def _normalize_supabase_segment(segment: Optional[str]) -> str:
        if not segment:
            return ""
        return str(segment).strip().strip("/\\")

    def _build_supabase_path(self, filename: str) -> str:
        """
        Construye la ruta de Supabase usando user_id.
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Ruta completa: {user_id}/{filename}
        """
        return f"{self._user_id}/{filename}"

    @staticmethod
    def _split_supabase_path(path: str) -> Tuple[str, str]:
        normalized = str(path or "").strip().strip("/\\")
        if not normalized:
            return "", ""
        prefix, _, name = normalized.rpartition("/")
        if not name:
            return prefix, ""
        return prefix, name

    def _update_chart_index(self, data: Optional[Dict[str, Any]], *, supabase_asset_files: Optional[List[str]] = None) -> None:
        if self._supabase_enabled and self._supabase_service:
            mapping = cast(Dict[str, Union[Path, str]], self._build_supabase_chart_index(data, supabase_asset_files))
            self._chart_paths = mapping
            if mapping:
                logger.debug(
                    "Gráficos disponibles en Supabase: %s",
                    {alias: path for alias, path in mapping.items()},
                )
            return

        mapping: Dict[str, Union[Path, str]] = {}
        charts_dir = getattr(self, "_charts_dir", None)

        def register(path: Optional[Path], aliases: List[str]) -> None:
            if not path:
                return
            try:
                resolved = path if path.is_absolute() else path.resolve()
            except Exception:
                return
            if not resolved.exists():
                return
            for alias in aliases:
                normalized = alias.strip().lower()
                if not normalized:
                    continue
                mapping[normalized] = resolved

        def resolve_candidate(raw: str) -> Optional[Path]:
            candidate = Path(raw)
            if candidate.is_absolute():
                return candidate

            search_roots: List[Path] = []
            if charts_dir:
                search_roots.append(charts_dir)
            search_roots.append(self._portfolio_data_path.parent)

            for root in search_roots:
                try:
                    resolved = (root / candidate).resolve()
                except Exception:
                    continue
                if resolved.exists():
                    return resolved

            try:
                return (search_roots[0] / candidate).resolve()
            except Exception:
                return None

        if charts_dir and charts_dir.exists():
            default_map = {
                charts_dir / "portfolio_chart.html": [
                    "portfolio",
                    "portfolio_chart",
                    "portfolio_performance",
                    "performance",
                    "cumulative_returns",
                ],
                charts_dir / "allocation_chart.html": [
                    "allocation",
                    "allocation_chart",
                    "composition",
                    "composition_donut",
                    "portfolio_composition",
                ],
            }
            for path, aliases in default_map.items():
                register(path, aliases)

            assets_dir = charts_dir / "assets"
            if assets_dir.exists():
                for html_file in assets_dir.glob("*_chart.html"):
                    symbol = html_file.stem.replace("_chart", "")
                    aliases = [symbol, symbol.lower(), symbol.upper(), f"{symbol.lower()}_chart", f"{symbol.upper()}_chart"]
                    register(html_file, aliases)

        charts_section: Optional[Dict[str, Any]] = None
        if isinstance(data, dict):
            charts_section = data.get("charts") if isinstance(data.get("charts"), dict) else None

        if charts_section:
            for key, raw_path in charts_section.items():
                if not isinstance(raw_path, str):
                    continue
                if raw_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif")) or key.endswith("_png"):
                    continue

                candidate = Path(raw_path) if Path(raw_path).is_absolute() else resolve_candidate(raw_path)
                if not candidate:
                    continue

                alias_candidates = {
                    key,
                    key.replace(".html", ""),
                    key.replace("_html", ""),
                    key.replace("_chart", ""),
                }
                if "portfolio" in key:
                    alias_candidates.update({"portfolio", "portfolio_chart", "portfolio_performance", "performance", "cumulative_returns"})
                if "allocation" in key or "composition" in key:
                    alias_candidates.update({"allocation", "allocation_chart", "composition", "composition_donut", "portfolio_composition"})

                register(candidate, list(alias_candidates))

        self._chart_paths = mapping
        if mapping:
            logger.debug(
                "Gráficos disponibles indexados localmente: %s",
                {alias: str(path) for alias, path in mapping.items()},
            )

    def _build_supabase_chart_index(
        self,
        data: Optional[Dict[str, Any]],
        supabase_asset_files: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        mapping: Dict[str, str] = {}

        def register(path: str, aliases: List[str]) -> None:
            if not path:
                return
            for alias in aliases:
                normalized = alias.strip().lower()
                if not normalized:
                    continue
                mapping[normalized] = path

        portfolio_path = self._build_supabase_path("portfolio_chart.html")
        allocation_path = self._build_supabase_path("allocation_chart.html")

        register(
            portfolio_path,
            [
                "portfolio",
                "portfolio_chart",
                "portfolio_performance",
                "performance",
                "cumulative_returns",
            ],
        )
        register(
            allocation_path,
            [
                "allocation",
                "allocation_chart",
                "composition",
                "composition_donut",
                "portfolio_composition",
            ],
        )

        asset_files = supabase_asset_files
        if asset_files is None:
            try:
                asset_files = self._list_supabase_asset_files()
            except Exception as exc:
                logger.warning("No se pudo listar gráficos de activos en Supabase: %s", exc)
                asset_files = []

        for file_name in asset_files or []:
            if not isinstance(file_name, str) or not file_name.endswith(".html"):
                continue
            
            # Desanitizar el nombre del archivo para obtener el símbolo original
            desanitized_name = desanitize_filename_for_storage(file_name)
            symbol = desanitized_name.replace("_chart.html", "").replace(".html", "")
            
            if not symbol:
                continue
            
            path = self._build_supabase_path(file_name)  # Usar nombre sanitizado para la ruta
            register(
                path,
                [
                    symbol,
                    symbol.lower(),
                    symbol.upper(),
                    f"{symbol.lower()}_chart",
                    f"{symbol.upper()}_chart",
                ],
            )

        charts_section = data.get("charts") if isinstance(data, dict) else None
        if isinstance(charts_section, dict):
            for key in charts_section.keys():
                normalized = str(key).strip().lower()
                if not normalized or normalized in mapping:
                    continue
                if normalized in {"portfolio", "allocation"}:
                    continue
                if normalized.endswith("_chart") and mapping.get(normalized):
                    continue

                # Intentar mapear el alias a un archivo conocido
                if normalized.startswith("portfolio"):
                    mapping[normalized] = portfolio_path
                elif normalized.startswith("allocation") or normalized.startswith("composition"):
                    mapping[normalized] = allocation_path

        return mapping

    def _list_supabase_asset_files(self) -> List[str]:
        """Lista archivos de gráficos de activos en Supabase para el usuario actual."""
        if not self._supabase_service:
            return []
        
        # Listar archivos en la carpeta del usuario
        try:
            response = self._supabase_service.client.storage.from_(self._supabase_bucket).list(self._user_id)
        except Exception as exc:
            logger.debug("Fallo al listar archivos en Supabase (user_id=%s): %s", self._user_id, exc)
            return []

        files: List[str] = []
        for item in response or []:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name.endswith(".html"):
                files.append(name)
        return files

    def _download_supabase_file(self, path: str) -> bytes:
        if not self._supabase_service:
            raise RuntimeError("Supabase no está configurado")
        return self._supabase_service.client.storage.from_(self._supabase_bucket).download(path)

    def _get_supabase_metadata(self, full_path: str) -> Optional[Dict[str, Any]]:
        if not self._supabase_service:
            return None
        prefix, name = self._split_supabase_path(full_path)
        try:
            response = self._supabase_service.client.storage.from_(self._supabase_bucket).list(prefix or "")
        except Exception as exc:
            logger.debug("No se pudo obtener metadatos de Supabase (%s): %s", full_path, exc)
            return None

        for item in response or []:
            if isinstance(item, dict) and item.get("name") == name:
                return item
        return None

    async def _load_from_supabase(self) -> Optional[Dict[str, Any]]:
        """Carga datos desde Supabase para el usuario específico."""
        if not self._supabase_enabled or not self._supabase_service:
            return None

        # ✅ Nueva ruta con user_id
        try:
            # Usar el método del servicio de Supabase que ya acepta user_id
            content = self._supabase_service.read_report_json(self._user_id, "portfolio_data.json")
            data = content if isinstance(content, dict) else json.loads(content)
        except Exception as exc:
            logger.warning("No se pudo descargar portfolio_data.json desde Supabase (user_id=%s): %s", self._user_id, exc)
            return None

        # Obtener metadata del archivo (timestamp) - ya no es necesario, usaremos el timestamp del JSON
        file_timestamp = None

        asset_files = await asyncio.to_thread(self._list_supabase_asset_files)

        async with self._lock:
            dt = self._parse_iso_datetime(data.get("generated_at")) if isinstance(data, dict) else None
            now = datetime.utcnow()
            self._cache = {
                "enabled": True,
                "status": "success",
                "message": "Datos desde Supabase Storage",
                "data": data,
                "persisted": True,
                "summary": data.get("summary") if isinstance(data, dict) else None,
                "market": data.get("market_overview") if isinstance(data, dict) else None,
                "period": data.get("period") if isinstance(data, dict) else self._default_period,
                "last_refresh": now.isoformat(),
                "source": "supabase",
                "data_timestamp": dt.isoformat() if dt else None,
            }
            self._summary = self._cache.get("summary")
            self._market = self._cache.get("market")
            self._last_refresh = now
            self._data_timestamp = dt
            self._file_timestamp = file_timestamp or now
            self._status = "success"
            self._chart_cache.clear()
            self._missing_supabase_charts.clear()
            self._update_chart_index(data, supabase_asset_files=asset_files)
        return self._cache

    def _resolve_supabase_chart_path(self, chart_name: str) -> Optional[str]:
        if not chart_name:
            return None
        raw = chart_name.strip()
        if not raw:
            return None

        normalized = raw.lower()

        if "/" in raw or "\\" in raw:
            return self._normalize_supabase_segment(raw)

        if normalized.endswith(".html"):
            return self._normalize_supabase_segment(raw)

        if normalized in {"portfolio", "portfolio_chart", "portfolio_performance", "performance", "cumulative_returns"}:
            return self._build_supabase_path("portfolio_chart.html")

        if normalized in {"allocation", "allocation_chart", "composition", "composition_donut", "portfolio_composition"}:
            return self._build_supabase_path("allocation_chart.html")

        base_symbol = raw
        if normalized.endswith("_chart"):
            base_symbol = raw[: -len("_chart")]

        base_symbol = base_symbol.replace(" ", "").upper()
        if not base_symbol:
            return None

        filename = f"{base_symbol}_chart.html"
        return self._build_supabase_path(filename)

    async def _fetch_supabase_chart(self, path: str) -> Optional[str]:
        if not self._supabase_service:
            return None
        normalized_path = self._normalize_supabase_segment(path)
        if not normalized_path:
            return None

        if normalized_path in self._missing_supabase_charts:
            return None

        cached = self._chart_cache.get(normalized_path)
        if cached is not None:
            return cached

        try:
            raw_bytes = await asyncio.to_thread(self._download_supabase_file, normalized_path)
        except Exception as exc:
            logger.warning("No se pudo descargar el gráfico desde Supabase (%s): %s", normalized_path, exc)
            self._missing_supabase_charts.add(normalized_path)
            return None

        try:
            html = raw_bytes.decode("utf-8")
        except Exception as exc:
            logger.warning("No se pudo decodificar el gráfico de Supabase (%s): %s", normalized_path, exc)
            self._missing_supabase_charts.add(normalized_path)
            return None

        self._chart_cache[normalized_path] = html
        if normalized_path in self._missing_supabase_charts:
            self._missing_supabase_charts.discard(normalized_path)
        return html

    def _build_chart_fallbacks(self, chart_name: str) -> List[Path]:
        candidates: List[Path] = []
        charts_dir = getattr(self, "_charts_dir", None)
        if not charts_dir:
            return candidates

        normalized = chart_name.strip().lower().replace(" ", "_")
        base_candidates = [normalized]
        if not normalized.endswith("_chart"):
            base_candidates.append(f"{normalized}_chart")

        unique_paths = []
        for base in base_candidates:
            for suffix in (".html", ".htm"):
                unique_paths.append(charts_dir / f"{base}{suffix}")

        symbol = chart_name.strip().upper()
        assets_dir = charts_dir / "assets"
        if assets_dir.exists():
            for suffix in ("_chart.html", ".html"):
                unique_paths.append(assets_dir / f"{symbol}{suffix}")
                unique_paths.append(assets_dir / f"{symbol.lower()}{suffix}")

        seen = set()
        for path in unique_paths:
            if path in seen:
                continue
            seen.add(path)
            candidates.append(path)

        return candidates

    def _build_portfolio_path_candidates(
        self,
        configured_path: Path,
        base_path: Path,
        backend_root: Path,
        project_root: Path,
    ) -> List[Path]:
        candidates: List[Path] = []

        if configured_path.is_absolute():
            candidates.append(configured_path)
        else:
            relative_options = [base_path, backend_root, project_root]
            for root in relative_options:
                candidates.append((root / configured_path).resolve())

            default_relative = Path("Portfolio manager/data/portfolio_data.json")
            if configured_path != default_relative:
                for root in (backend_root, project_root):
                    candidates.append((root / default_relative).resolve())

        seen = set()
        unique_candidates: List[Path] = []
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            unique_candidates.append(candidate)

        if unique_candidates:
            return unique_candidates

        fallback = configured_path if configured_path.is_absolute() else (project_root / configured_path).resolve()
        return [fallback]

    def _select_portfolio_path(self, candidates: List[Path], project_root: Path) -> Path:
        for candidate in candidates:
            if candidate.exists():
                logger.info("Archivo de portafolio configurado en %s", candidate)
                return candidate

        fallback = candidates[0] if candidates else (project_root / "Portfolio manager" / "data" / "portfolio_data.json")
        logger.warning(
            "Archivo de portafolio no encontrado en rutas candidatas. Usando ruta por defecto: %s",
            fallback,
        )
        return fallback

    async def _load_from_disk(self) -> Optional[Dict[str, Any]]:
        try:
            if not self._portfolio_data_path.exists():
                logger.warning("Archivo de portafolio no encontrado en %s", self._portfolio_data_path)
                return None
            text = await asyncio.get_event_loop().run_in_executor(None, self._portfolio_data_path.read_text)
            data = json.loads(text)
            generated_at = data.get("generated_at")
            dt = None
            if isinstance(generated_at, str):
                try:
                    dt = datetime.fromisoformat(generated_at)
                except ValueError:
                    dt = None
            file_timestamp = None
            try:
                stat = self._portfolio_data_path.stat()
                file_timestamp = datetime.utcfromtimestamp(stat.st_mtime)
            except Exception:
                file_timestamp = None
            async with self._lock:
                self._cache = {
                    "enabled": True,
                    "status": "success",
                    "message": "Datos desde JSON persistido",
                    "data": data,
                    "persisted": True,
                    "summary": data.get("summary"),
                    "market": data.get("market_overview"),
                    "period": data.get("period", self._default_period),
                    "last_refresh": datetime.utcnow().isoformat(),
                    "source": "portfolio_json",
                    "data_timestamp": dt.isoformat() if dt else None,
                }
                self._summary = data.get("summary")
                self._market = data.get("market_overview")
                self._last_refresh = datetime.utcnow()
                self._data_timestamp = dt
                self._file_timestamp = file_timestamp
                self._status = "success"
                self._update_chart_index(data)
            return self._cache
        except Exception as exc:
            logger.exception("Error leyendo portfolio_data.json: %s", exc)
            return None

    async def _refresh_cache(self) -> Dict[str, Any]:
        if not self._enabled:
            return self._build_placeholder("Integración con Portfolio Manager pendiente de habilitar.", enabled=False)

        cached = await self._load_from_supabase()
        if not cached:
            cached = await self._load_from_disk()
        if cached:
            # Agregar información del estado del mercado
            market_open = self._is_market_open()
            next_open = None if market_open else self._get_next_market_open()
            
            result = dict(cached)
            result["market_open"] = market_open
            result["next_open_est"] = next_open.isoformat() if next_open else None
            result["timezone"] = "America/New_York"
            return result

        return self._build_placeholder("No hay datos disponibles en Supabase ni en el JSON local.", enabled=False)

    async def ensure_started(self) -> None:
        if not self._enabled:
            return
        await self._refresh_cache()

    async def shutdown(self) -> None:
        return

    async def get_report(self, period: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        if not self._enabled:
            return self._build_placeholder("Integración con Portfolio Manager pendiente de habilitar.", enabled=False)

        if force_refresh or self._needs_refresh():
            return await self._refresh_cache()

        if self._cache is None:
            await self._refresh_cache()

        # Agregar información del estado del mercado al reporte
        if self._cache:
            market_open = self._is_market_open()
            next_open = None if market_open else self._get_next_market_open()
            
            result = dict(self._cache)
            result["market_open"] = market_open
            result["next_open_est"] = next_open.isoformat() if next_open else None
            result["timezone"] = "America/New_York"
            return result

        return self._build_placeholder("No hay datos disponibles.", enabled=False)

    async def poll_portfolio(
        self,
        since: Optional[str] = None,
        *,
        include_report: bool = False,
        include_summary: bool = True,
        include_market: bool = True,
    ) -> Dict[str, Any]:
        if not self._enabled:
            placeholder = self._build_placeholder("Integración con Portfolio Manager pendiente de habilitar.", enabled=False)
            return {
                "updated": False,
                "enabled": False,
                "message": placeholder.get("message"),
                "persisted": False,
            }

        since_dt = self._parse_iso_datetime(since)
        if isinstance(since_dt, datetime) and since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)

        file_timestamp = self._get_file_last_modified()
        if isinstance(file_timestamp, datetime) and file_timestamp.tzinfo is None:
            file_timestamp = file_timestamp.replace(tzinfo=timezone.utc)
        should_refresh = self._cache is None or self._needs_refresh()

        cached_timestamp = self._file_timestamp
        if isinstance(cached_timestamp, datetime) and cached_timestamp.tzinfo is None:
            cached_timestamp = cached_timestamp.replace(tzinfo=timezone.utc)

        if file_timestamp and cached_timestamp and file_timestamp > cached_timestamp:
            should_refresh = True

        if should_refresh:
            await self._refresh_cache()
            refreshed = self._file_timestamp or file_timestamp
            if isinstance(refreshed, datetime) and refreshed.tzinfo is None:
                refreshed = refreshed.replace(tzinfo=timezone.utc)
            file_timestamp = refreshed

        generated_at_dt = self._data_timestamp if isinstance(self._data_timestamp, datetime) else None
        if isinstance(generated_at_dt, datetime) and generated_at_dt.tzinfo is None:
            generated_at_dt = generated_at_dt.replace(tzinfo=timezone.utc)
        generated_at = generated_at_dt.isoformat() if generated_at_dt else None

        last_refresh_dt = self._last_refresh if isinstance(self._last_refresh, datetime) else None
        if isinstance(last_refresh_dt, datetime) and last_refresh_dt.tzinfo is None:
            last_refresh_dt = last_refresh_dt.replace(tzinfo=timezone.utc)
        last_refresh = last_refresh_dt.isoformat() if last_refresh_dt else None

        if since_dt and file_timestamp and file_timestamp <= since_dt:
            return {
                "updated": False,
                "persisted": bool(self._cache),
                "generated_at": generated_at,
                "file_timestamp": file_timestamp.isoformat() if isinstance(file_timestamp, datetime) else None,
                "last_refresh": last_refresh,
            }

        payload: Dict[str, Any] = {
            "updated": True,
            "persisted": bool(self._cache),
            "generated_at": generated_at,
            "file_timestamp": file_timestamp.isoformat() if isinstance(file_timestamp, datetime) else None,
            "last_refresh": last_refresh,
            "status": self._status,
        }

        if include_report:
            payload["report"] = self._cache.get("data") if self._cache else None

        if include_summary:
            payload["summary"] = self._summary

        if include_market:
            payload["market_overview"] = self._market

        return payload

    async def get_summary(self) -> Dict[str, Any]:
        if not self._enabled:
            return {"enabled": False, "message": "Integración con Portfolio Manager pendiente de habilitar."}

        if self._summary is None or self._needs_refresh():
            await self._refresh_cache()

        if not self._summary:
            return {
                "enabled": True,
                "status": self._status,
                "summary": None,
                "message": "No hay datos disponibles del portafolio en este momento.",
                "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
                "period": self._cache.get("period") if self._cache else self._default_period,
            }

        return {
            "enabled": True,
            "status": self._status,
            "summary": self._summary,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "period": self._cache.get("period") if self._cache else self._default_period,
        }

    async def get_market(self) -> Dict[str, Any]:
        if not self._enabled:
            return {"enabled": False, "message": "Integración con Portfolio Manager pendiente de habilitar."}

        if self._market is None or self._needs_refresh():
            await self._refresh_cache()

        market = self._market
        if not market:
            return {
                "enabled": False,
                "message": "No hay datos de mercado disponibles en el JSON.",
            }

        # Agregar información del estado del mercado
        market_open = self._is_market_open()
        next_open = None if market_open else self._get_next_market_open()

        return {
            "enabled": True,
            "status": self._status,
            "market": market,
            "market_overview": market,
            "market_open": market_open,
            "next_open_est": next_open.isoformat() if next_open else None,
            "timezone": "America/New_York",
            "persisted": True,
            "generated_at": self._data_timestamp.isoformat() if isinstance(self._data_timestamp, datetime) else None,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
        }

    async def get_chart(self, chart_type: str) -> Optional[str]:
        if not self._enabled:
            return None

        target = (chart_type or "").strip()
        if not target:
            return None

        normalized = target.lower()

        if self._cache is None or self._needs_refresh():
            await self._refresh_cache()

        if not self._chart_paths:
            self._update_chart_index(self._cache.get("data") if self._cache else None)

        source = self._chart_paths.get(normalized)

        if isinstance(source, str):
            html = await self._fetch_supabase_chart(source)
            if html is not None:
                return html

        if isinstance(source, Path):
            try:
                return await asyncio.to_thread(source.read_text, encoding="utf-8")
            except Exception as exc:
                logger.exception("Error leyendo gráfico '%s' desde %s: %s", chart_type, source, exc)

        if self._supabase_enabled and self._supabase_service:
            supabase_path = self._resolve_supabase_chart_path(target)
            if supabase_path:
                html = await self._fetch_supabase_chart(supabase_path)
                if html is not None:
                    self._chart_paths[normalized] = supabase_path
                    return html

        candidate_paths: List[Path] = []
        resolved_path: Optional[Path] = source if isinstance(source, Path) else None

        if resolved_path is None:
            candidate_paths = self._build_chart_fallbacks(target)
            for candidate in candidate_paths:
                if candidate and candidate.exists():
                    resolved_path = candidate
                    self._chart_paths[normalized] = candidate
                    break

        if resolved_path is None or not resolved_path.exists():
            logger.warning(
                "No se encontró el gráfico '%s'. Rutas evaluadas: %s",
                chart_type,
                ", ".join(str(p) for p in candidate_paths) if candidate_paths else "<sin candidatos>",
            )
            return None

        try:
            return await asyncio.to_thread(resolved_path.read_text, encoding="utf-8")
        except Exception as exc:
            logger.exception("Error leyendo gráfico '%s' desde %s: %s", chart_type, resolved_path, exc)
            return None

    async def add_asset(self, symbol: str, units: int) -> Dict[str, Any]:
        return {
            "success": False,
            "message": "El servicio bajo demanda no admite agregar activos de forma remota.",
        }

    async def update_portfolio(self, assets: Any) -> Dict[str, Any]:
        return {
            "success": False,
            "message": "El servicio bajo demanda no admite actualizar el portafolio de forma remota.",
        }

    def _build_placeholder(self, message: str, *, enabled: bool) -> Dict[str, Any]:
        return {
            "enabled": enabled,
            "message": message,
            "data": None,
            "summary": None,
            "market": None,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "period": self._cache.get("period") if self._cache else self._default_period,
            "source": "portfolio_manager_service",
        }


# ✅ FACTORY PATTERN: Crear cliente por usuario
def get_portfolio_manager_client(user_id: str) -> PortfolioManagerClient:
    """
    Factory para crear un cliente de Portfolio Manager para un usuario específico.
    
    Args:
        user_id: ID del usuario para el cual crear el cliente
        
    Returns:
        PortfolioManagerClient: Cliente configurado para el usuario
    """
    return PortfolioManagerClient(user_id)


# ❌ ELIMINADO: Singleton compartido
# portfolio_runtime = PortfolioManagerClient()


async def startup_portfolio_manager() -> None:
    """Startup hook - ya no es necesario con el patrón factory."""
    pass


async def shutdown_portfolio_manager() -> None:
    """Shutdown hook - ya no es necesario con el patrón factory."""
    pass
