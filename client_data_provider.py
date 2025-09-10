"""
Cliente/Portfolio Data Provider

Este módulo centraliza la obtención del portafolio del cliente y la descarga de
datos de mercado desde yfinance para ser reutilizado por ambos procesos:
- Portfolio_analizer (API y scripts)
- porfolio analizer v2 (script monolítico)

Notas:
- A futuro, este proveedor debe leer el portafolio desde una base de datos.
  Se deja documentado el punto de conexión (ver función get_client_portfolio).
- Por ahora, devuelve un portafolio por defecto y pesos equiponderados.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf


# Portafolio por defecto solicitado
DEFAULT_TICKERS: List[str] = [
    "NVDA", "GOOG", "GOOGL", "AAPL", "TLT", "IEF", "MBB", "BTC-USD", "ETH-USD", "PAXG-USD",
]


@dataclass
class ClientPortfolio:
    """Estructura de portafolio de un cliente."""

    client_id: Optional[str]
    tickers: List[str]
    weights: Dict[str, float]
    start_date: Optional[str] = None
    end_date: Optional[str] = None


def _build_equal_weights(tickers: List[str]) -> Dict[str, float]:
    if not tickers:
        return {}
    w = 1.0 / float(len(tickers))
    return {t: w for t in tickers}


def get_client_portfolio(client_id: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> Dict[str, object]:
    """
    Obtiene el portafolio del cliente.

    Futuro (comentado): leer desde BD según client_id.
    """
    # Punto de conexión a BD (placeholder):
    # ------------------------------------------------------
    # from database import get_db
    # def fetch_portfolio_from_db(client_id: str) -> Dict[str, Any]:
    #     db = get_db()
    #     row = db.query(...).filter(...client_id...).first()
    #     return {"tickers": row.tickers, "weights": row.weights, ...}
    # if client_id:
    #     return fetch_portfolio_from_db(client_id)
    # ------------------------------------------------------

    # Por ahora: portafolio por defecto con pesos equiponderados
    tickers = list(DEFAULT_TICKERS)
    weights = _build_equal_weights(tickers)

    return {
        "client_id": client_id,
        "tickers": tickers,
        "weights": weights,
        "start_date": start_date,
        "end_date": end_date,
    }


def fetch_portfolio_market_data(
    tickers: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = "5y",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Descarga precios de cierre ajustados y calcula retornos diarios limpios.

    Retorna (prices_df, daily_returns_df), ambos indexados por fecha y columnas por ticker.
    """
    if not tickers:
        return pd.DataFrame(), pd.DataFrame()

    # Descarga datos (preferimos Close auto-ajustado via auto_adjust=True)
    try:
        if start_date or end_date:
            raw = yf.download(tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)
        else:
            raw = yf.download(tickers, period=period or "5y", progress=False, auto_adjust=True)

        close = raw["Close"] if isinstance(raw, pd.DataFrame) and "Close" in raw.columns else raw

        # Si es Serie (un solo ticker), convertir a DataFrame con nombre de columna consistente
        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers[0])

        # Saneamiento básico
        close = close.copy()
        close[close <= 0] = np.nan
        close.dropna(inplace=True)

        # Retornos diarios simples, limpios
        daily_returns = close.pct_change()
        daily_returns.replace([np.inf, -np.inf], np.nan, inplace=True)
        daily_returns.dropna(inplace=True)

        return close, daily_returns
    except Exception as e:
        print(f"[client_data_provider] Error descargando datos: {e}")
        return pd.DataFrame(), pd.DataFrame()


def get_default_period_dates(years: int = 2) -> Tuple[str, str]:
    """Utilidad para obtener (start_date, end_date) últimos N años aprox."""
    end = datetime.now()
    start = end.replace(year=end.year - years)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


