import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from config import settings
from services.supabase_storage import get_supabase_storage

logger = logging.getLogger(__name__)

PORTFOLIO_NEWS_FILENAME = "portfolio_news.json"
LOCAL_JSON_PATH = Path(__file__).resolve().parent.parent / PORTFOLIO_NEWS_FILENAME
DEFAULT_SMALL_CARD_FALLBACK = "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=1200&q=80"
DEFAULT_LARGE_CARD_FALLBACK = "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?auto=format&fit=crop&w=1200&q=80"


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    try:
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        logger.debug("Fecha en formato desconocido: %s", value)
        return None


def format_relative_time(dt: Optional[datetime], *, now: Optional[datetime] = None) -> Optional[str]:
    if not dt:
        return None

    reference = now or datetime.now(timezone.utc)
    delta = reference - dt
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "hace instantes"
    if seconds < 3600:
        minutes = seconds // 60
        return f"hace {minutes} minuto{'s' if minutes != 1 else ''}"
    if seconds < 86400:
        hours = seconds // 3600
        return f"hace {hours} hora{'s' if hours != 1 else ''}"
    if seconds < 604800:
        days = seconds // 86400
        return f"hace {days} día{'s' if days != 1 else ''}"
    weeks = seconds // 604800
    return f"hace {weeks} semana{'s' if weeks != 1 else ''}"


def determine_sentiment_bucket(value: Optional[int]) -> Tuple[str, str]:
    score = value if isinstance(value, int) else 50

    if score <= 20:
        return "extreme-fear", "Extreme Fear"
    if score <= 40:
        return "fear", "Fear"
    if score <= 60:
        return "neutral", "Neutral"
    if score <= 80:
        return "greed", "Greed"
    return "extreme-greed", "Extreme Greed"


def format_score(score: Optional[int]) -> str:
    if score is None:
        return "0"
    return f"{score:,}".replace(",", "·")


def extract_source_name(source: Optional[str], url: Optional[str]) -> Optional[str]:
    if source:
        return source
    if not url:
        return None
    hostname = urlparse(url).netloc
    return hostname or None


def load_portfolio_news_payload() -> Dict[str, Any]:
    service = get_supabase_storage(settings)
    last_error: Optional[Exception] = None

    if service:
        try:
            data = service.read_report_json(PORTFOLIO_NEWS_FILENAME)
            data["_source"] = "supabase"
            return data
        except Exception as exc:  # pragma: no cover - dependencia externa
            last_error = exc
            logger.warning("Fallo al leer %s desde Supabase: %s", PORTFOLIO_NEWS_FILENAME, exc)

    if LOCAL_JSON_PATH.exists():
        try:
            with LOCAL_JSON_PATH.open("r", encoding="utf-8") as file:
                data = json.load(file)
            data["_source"] = "local"
            return data
        except Exception as exc:
            logger.error("Error al cargar JSON local %s: %s", LOCAL_JSON_PATH, exc)
            raise

    if last_error:
        raise RuntimeError(
            f"No fue posible obtener {PORTFOLIO_NEWS_FILENAME} desde Supabase ni desde el archivo local"
        ) from last_error

    raise FileNotFoundError(
        f"El archivo {PORTFOLIO_NEWS_FILENAME} no está disponible ni en Supabase ni en el repositorio"
    )


def build_news_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    news_entries: List[Dict[str, Any]] = []

    for entry in items:
        news_entries.append(
            {
                "uuid": entry.get("uuid"),
                "title": entry.get("title"),
                "subtitle": entry.get("subtitle"),
                "summary": entry.get("summary"),
                "source": extract_source_name(entry.get("source"), entry.get("url")),
                "url": entry.get("url"),
                "image_url": entry.get("image"),
                "published_at": entry.get("published_at"),
                "type": entry.get("type"),
            }
        )

    return news_entries


def build_reddit_cards(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    sorted_items = sorted(
        items,
        key=lambda entry: (
            entry.get("score", 0),
            parse_datetime(entry.get("created_utc")) or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    cards: List[Dict[str, Any]] = []

    for entry in sorted_items[:3]:
        created_at = parse_datetime(entry.get("created_utc"))
        cards.append(
            {
                "id": entry.get("id"),
                "type": "reddit",
                "layout": "small",
                "badge": f"Reddit • r/{entry.get('subreddit', 'unknown')}",
                "title": entry.get("title") or "Post destacado",
                "description": "Actividad de la comunidad",
                "body": f"Impacto: {format_score(entry.get('score'))} votos.",
                "image_url": entry.get("url") or DEFAULT_SMALL_CARD_FALLBACK,
                "url": entry.get("url"),
                "primary_stat_label": "Upvotes",
                "primary_stat_value": format_score(entry.get("score")),
                "secondary_stat_label": "Publicado",
                "secondary_stat_value": format_relative_time(created_at, now=now),
                "published_at": entry.get("created_utc"),
                "score": entry.get("score"),
            }
        )

    return cards


def build_tradingview_cards(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    sorted_items = sorted(
        items,
        key=lambda entry: parse_datetime(entry.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    cards: List[Dict[str, Any]] = []

    for entry in sorted_items[:2]:
        published_at = parse_datetime(entry.get("published_at"))
        cards.append(
            {
                "id": entry.get("id"),
                "type": "tradingview",
                "layout": "large",
                "badge": f"TradingView • {entry.get('ticker', 'Mercado')}",
                "title": entry.get("title") or "Idea destacada",
                "description": entry.get("author"),
                "body": entry.get("category"),
                "image_url": entry.get("image_url") or DEFAULT_LARGE_CARD_FALLBACK,
                "url": entry.get("idea_url") or entry.get("source_url"),
                "primary_stat_label": "Publicado",
                "primary_stat_value": format_relative_time(published_at, now=now),
                "secondary_stat_label": "Ticker",
                "secondary_stat_value": entry.get("ticker"),
                "published_at": entry.get("published_at"),
                "cta_label": "Ver idea",
            }
        )

    return cards


def get_home_dashboard_data() -> Dict[str, Any]:
    payload = load_portfolio_news_payload()

    generated_at = parse_datetime(payload.get("generated_at"))
    now_iso = (generated_at or datetime.now(timezone.utc)).isoformat()

    market_sentiment = payload.get("market_sentiment", {})
    sentiment_value = market_sentiment.get("value")
    sentiment_bucket, sentiment_label = determine_sentiment_bucket(sentiment_value)

    response: Dict[str, Any] = {
        "updated_at": now_iso,
        "source": payload.get("_source"),
        "market_sentiment": {
            "value": sentiment_value,
            "description": market_sentiment.get("description") or sentiment_label,
            "bucket": sentiment_bucket,
        },
        "portfolio_news": build_news_items(payload.get("portfolio_news", [])),
        "highlights": {
            "small_cards": build_reddit_cards(payload.get("reddit_mentions", [])),
            "large_cards": build_tradingview_cards(payload.get("tradingview_ideas", [])),
        },
    }

    return response