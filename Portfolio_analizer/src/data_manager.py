# src/data_manager.py
"""
Módulo de gestión de datos financieros.

Este módulo proporciona funcionalidades para la descarga, limpieza y procesamiento
de datos financieros desde fuentes externas como Yahoo Finance. Incluye manejo
robusto de errores y limpieza automática de datos.

Funciones principales:
- fetch_portfolio_data: Descarga datos históricos de Yahoo Finance
- calculate_returns: Calcula retornos diarios con métodos simple o logarítmico

Autor: Portfolio Analyzer Team
Fecha: Julio 2025
Versión: 2.0.0
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Literal
from datetime import datetime, timedelta

def fetch_portfolio_data(
    tickers: List[str], 
    start_date: str, 
    end_date: str
) -> pd.DataFrame:
    """
    Descarga datos históricos de precios para una lista de tickers.

    Args:
        tickers (List[str]): Lista de símbolos de los activos (ej. ['AAPL', 'MSFT']).
        start_date (str): Fecha de inicio en formato 'YYYY-MM-DD'.
        end_date (str): Fecha de fin en formato 'YYYY-MM-DD'.

    Returns:
        pd.DataFrame: Un DataFrame con los precios de cierre ajustados ('Adj Close')
                      para cada ticker, indexado por fecha. Las filas con datos
                      faltantes (NaN) se eliminan.
    """
    print(f"Descargando datos para {', '.join(tickers)}...")
    try:
        prices_df = yf.download(
            tickers, 
            start=start_date, 
            end=end_date,
            progress=False,
            auto_adjust=True # Usa 'Adj Close' y ajusta por dividendos/splits
        )['Close']
        
        # Si solo se descarga un ticker, yfinance puede devolver una Serie
        if isinstance(prices_df, pd.Series):
            prices_df = prices_df.to_frame(name=tickers[0])

        # Sanear los datos: reemplazar precios <= 0 con NaN para evitar retornos infinitos
        prices_df[prices_df <= 0] = np.nan

        # Eliminar filas donde CUALQUIER activo no tenga datos (ahora incluye los saneados)
        prices_df.dropna(inplace=True)

        if prices_df.empty:
            raise ValueError("No se pudieron obtener datos para los tickers en el rango de fechas especificado.")
            
        print("Datos descargados y limpiados exitosamente.")
        return prices_df

    except Exception as e:
        print(f"Error al descargar los datos: {e}")
        return pd.DataFrame()


def calculate_returns(
    prices_df: pd.DataFrame, 
    method: Literal['simple', 'log'] = 'simple'
) -> pd.DataFrame:
    """
    Calcula los retornos diarios de los activos, asegurando que no haya valores inválidos.

    Args:
        prices_df (pd.DataFrame): DataFrame de precios de cierre ajustados.
        method (Literal['simple', 'log']): El método para calcular los retornos.
                                          'simple' -> (p1 - p0) / p0
                                          'log'    -> ln(p1 / p0)

    Returns:
        pd.DataFrame: Un DataFrame de los retornos calculados. La primera fila
                      será NaN y se eliminará, junto con cualquier otra fila que
                      contenga valores infinitos.
    """
    if method == 'simple':
        returns_df = prices_df.pct_change()
    elif method == 'log':
        returns_df = np.log(prices_df / prices_df.shift(1))
    else:
        raise ValueError("El método debe ser 'simple' o 'log'.")
    
    # Sanear los retornos: Reemplazar inf y -inf con NaN y eliminar todas las filas con NaN.
    # Esto soluciona tanto la primera fila NaN como los posibles infinitos por precios de 0.
    returns_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    returns_df.dropna(inplace=True)
    
    return returns_df

def get_current_asset_info(ticker: str) -> dict:
    """
    Obtiene información completa y actualizada de un activo financiero.

    Args:
        ticker (str): El símbolo del activo (e.g., 'AAPL').

    Returns:
        dict: Un diccionario con información completa del activo incluyendo:
              - Precio actual y cambio diario
              - Capitalización de mercado
              - Volumen de trading
              - Información fundamental básica
              - O un mensaje de error si el activo no se encuentra.
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Obtener datos históricos de los últimos 2 días para calcular el cambio
        hist = stock.history(period="2d")
        
        if hist.empty or len(hist) < 2:
            return {"error": f"No se pudieron obtener datos suficientes para {ticker}"}

        # Precio actual y cambio diario
        current_price = hist['Close'].iloc[-1]
        previous_close = hist['Close'].iloc[-2]
        price_change = current_price - previous_close
        percent_change = (price_change / previous_close) * 100
        
        # Obtener información adicional del activo
        info = stock.info
        
        # Volumen actual (del último día disponible)
        volume = hist['Volume'].iloc[-1] if not hist['Volume'].empty else None
        
        # Información adicional disponible en info
        market_cap = info.get('marketCap')
        avg_volume = info.get('averageVolume')
        pe_ratio = info.get('trailingPE')
        dividend_yield = info.get('dividendYield')
        fifty_two_week_high = info.get('fiftyTwoWeekHigh')
        fifty_two_week_low = info.get('fiftyTwoWeekLow')
        company_name = info.get('shortName') or info.get('longName')
        sector = info.get('sector')
        industry = info.get('industry')

        return {
            "ticker": ticker,
            "company_name": company_name,
            "current_price": round(current_price, 2),
            "price_change": round(price_change, 2),
            "percent_change": round(percent_change, 2),
            "market_cap": market_cap,
            "volume": int(volume) if volume and not pd.isna(volume) else None,
            "avg_volume": avg_volume,
            "pe_ratio": round(pe_ratio, 2) if pe_ratio and not pd.isna(pe_ratio) else None,
            "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield and not pd.isna(dividend_yield) else None,
            "fifty_two_week_high": round(fifty_two_week_high, 2) if fifty_two_week_high and not pd.isna(fifty_two_week_high) else None,
            "fifty_two_week_low": round(fifty_two_week_low, 2) if fifty_two_week_low and not pd.isna(fifty_two_week_low) else None,
            "sector": sector,
            "industry": industry
        }
    except Exception as e:
        return {"error": f"Ocurrió un error al obtener datos para {ticker}: {e}"}