# src/interactive_charts.py
"""
Módulo de gráficos interactivos para análisis de portafolios.

Este módulo proporciona funcionalidades para crear visualizaciones interactivas
de alta calidad usando Plotly, incluyendo gráficos de rendimiento, drawdown,
correlaciones y exportación automática a imágenes PNG.

Funciones principales:
- plot_cumulative_returns: Gráfico de rendimiento acumulado
- plot_drawdown_underwater: Gráfico de drawdown underwater
- plot_correlation_heatmap: Heatmap de correlación entre activos
- save_chart_as_image: Exportación de gráficos a imágenes
- generate_all_charts_and_save: Generación y guardado masivo de gráficos

Autor: Portfolio Analyzer Team
Fecha: Julio 2025
Versión: 2.0.0
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

# Parchear quantstats para evitar el error de IPython
import sys
def patch_quantstats():
    try:
        from IPython.core.getipython import get_ipython
        ipython = get_ipython()
        if ipython:
            # Crear un mock de la función magic que no haga nada
            def dummy_magic(line):
                pass
            # Usar setattr para asignar el atributo de manera segura
            setattr(ipython, 'magic', dummy_magic)
    except:
        pass

patch_quantstats()
import quantstats as qs

def plot_cumulative_returns(
    portfolio_returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    title: str = "Rendimiento Acumulado del Portafolio",
    output_path: Optional[str] = None
) -> go.Figure:
    """
    Genera un gráfico interactivo del rendimiento acumulado a lo largo del tiempo.

    Args:
        portfolio_returns (pd.Series): Retornos diarios del portafolio.
        benchmark_returns (pd.Series, optional): Retornos diarios del benchmark para comparación.
        title (str): Título del gráfico.
        output_path (str, optional): Ruta de salida para guardar el archivo HTML.

    Returns:
        go.Figure: Objeto de figura de Plotly.
    """
    # Asegurarse de que el índice sea DatetimeIndex
    portfolio_returns.index = pd.to_datetime(portfolio_returns.index)
    if benchmark_returns is not None:
        benchmark_returns.index = pd.to_datetime(benchmark_returns.index)

    # Calcular rendimientos acumulados con pandas
    cumulative_returns = (1 + portfolio_returns).cumprod()
    
    fig = go.Figure()

    # Añadir línea de rendimiento del portafolio
    fig.add_trace(go.Scatter(
        x=cumulative_returns.index,
        y=cumulative_returns,
        mode='lines',
        name='Portafolio',
        line=dict(color='blue', width=2)
    ))

    # Añadir línea del benchmark si se proporciona
    if benchmark_returns is not None:
        cumulative_benchmark = (1 + benchmark_returns).cumprod()
        fig.add_trace(go.Scatter(
            x=cumulative_benchmark.index,
            y=cumulative_benchmark,
            mode='lines',
            name='Benchmark',
            line=dict(color='gray', width=1.5, dash='dash')
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title="Rendimiento Acumulado",
        legend_title="Activos"
    )
    
    if output_path:
        fig.write_html(output_path)
        return output_path
    else:
        return fig

def plot_donut_chart(weights, symbols, output_path=None):
    """
    Genera un gráfico de tipo donut para mostrar la distribución de pesos en el portafolio.

    Args:
        weights (list): Lista de pesos de los activos en el portafolio.
        symbols (list): Lista de símbolos de los activos.
        output_path (str, optional): Ruta de salida para guardar el archivo HTML.

    Returns:
        str: Ruta del archivo guardado.
    """
    fig = go.Figure(data=[go.Pie(labels=symbols, values=weights, hole=.3)])
    
    fig.update_layout(
        title="Composición del Portafolio",
        legend_title="Activos"
    )
    
    if output_path:
        fig.write_html(output_path)
        return output_path
    else:
        return fig

def plot_breakdown_chart(weights, symbols, output_path=None):
    """
    Genera un gráfico de barras para mostrar el desglose de pesos por activo en el portafolio.

    Args:
        weights (list): Lista de pesos de los activos en el portafolio.
        symbols (list): Lista de símbolos de los activos.
        output_path (str, optional): Ruta de salida para guardar el archivo HTML.

    Returns:
        str: Ruta del archivo guardado.
    """
    fig = go.Figure(data=[go.Bar(x=symbols, y=weights)])
    
    fig.update_layout(
        title="Desglose del Portafolio por Activo",
        xaxis_title="Activo",
        yaxis_title="Peso en el Portafolio",
        legend_title="Activos"
    )
    
    if output_path:
        fig.write_html(output_path)
        return output_path
    else:
        return fig

def plot_correlation_matrix(returns, output_path=None):
    """
    Genera un gráfico de matriz de correlación para los retornos de los activos.

    Args:
        returns (pd.DataFrame): DataFrame con los retornos de los activos.
        output_path (str, optional): Ruta de salida para guardar el archivo HTML.

    Returns:
        str: Ruta del archivo guardado.
    """
    fig = go.Figure(data=go.Heatmap(
        z=returns.corr().values,
        x=returns.columns.tolist(),
        y=returns.columns.tolist(),
        colorscale='Viridis'
    ))
    
    fig.update_layout(
        title="Matriz de Correlación de Retornos",
    )
    
    if output_path:
        fig.write_html(output_path)
        return output_path
    else:
        return fig

def plot_drawdown_underwater(
    portfolio_returns: pd.Series,
    title: str = "Drawdown del Portafolio (Underwater Plot)",
    output_path: Optional[str] = None
) -> go.Figure:
    """
    Genera un gráfico "underwater" que muestra los drawdowns del portafolio.

    Args:
        portfolio_returns (pd.Series): Retornos diarios del portafolio.
        title (str): Título del gráfico.
        output_path (str, optional): Ruta de salida para guardar el archivo HTML.

    Returns:
        go.Figure: Objeto de figura de Plotly.
    """
    # Asegurarse de que el índice sea DatetimeIndex
    portfolio_returns.index = pd.to_datetime(portfolio_returns.index)
    
    # Calcular la serie de drawdown manualmente
    cumulative_returns = (1 + portfolio_returns).cumprod()
    previous_peaks = cumulative_returns.cummax()
    drawdowns = (cumulative_returns - previous_peaks) / previous_peaks
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=drawdowns.index,
        y=drawdowns,
        fill='tozeroy',
        mode='lines',
        name='Drawdown',
        line=dict(color='red')
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title="Drawdown",
        showlegend=False
    )
    
    if output_path:
        fig.write_html(output_path)
        return output_path
    else:
        return fig
    

def plot_correlation_heatmap(
    asset_returns: pd.DataFrame,
    title: str = "Matriz de Correlación de Activos",
    output_path: Optional[str] = None
) -> go.Figure:
    """
    Genera un heatmap interactivo de la matriz de correlación de los activos.

    Args:
        asset_returns (pd.DataFrame): Retornos diarios de los activos.
        title (str): Título del gráfico.
        output_path (str, optional): Ruta de salida para guardar el archivo HTML.

    Returns:
        go.Figure: Objeto de figura de Plotly.
    """
    corr_matrix = asset_returns.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu',
        zmin=-1,
        zmax=1,
        text=corr_matrix.values,
        texttemplate="%{text:.2f}"
    ))
    
    fig.update_layout(
        title=title,
        xaxis_showgrid=False,
        yaxis_showgrid=False,
        height=600,
        width=600
    )
    
    if output_path:
        fig.write_html(output_path)
        return output_path
    else:
        return fig


def save_chart_as_image(
    fig: go.Figure,
    filename: str,
    output_dir: str = "outputs",
    format: str = "png",
    width: int = 1200,
    height: int = 600
) -> str:
    """
    Guarda un gráfico de Plotly como imagen en una carpeta local.

    Args:
        fig (go.Figure): Figura de Plotly a guardar.
        filename (str): Nombre del archivo (sin extensión).
        output_dir (str): Directorio donde guardar la imagen.
        format (str): Formato de la imagen ('png', 'jpg', 'svg', 'pdf').
        width (int): Ancho de la imagen en píxeles.
        height (int): Alto de la imagen en píxeles.

    Returns:
        str: Ruta completa del archivo guardado.
    """
    # Crear directorio si no existe
    Path(output_dir).mkdir(exist_ok=True)
    
    # Crear ruta completa del archivo
    filepath = os.path.join(output_dir, f"{filename}.{format}")
    
    try:
        # Intentar guardar la imagen con kaleido
        fig.write_image(filepath, width=width, height=height)
        print(f"✅ Gráfico guardado como {format.upper()}: {filepath}")
        return filepath
    except Exception as e:
        # Si falla kaleido, intentar con HTML como fallback
        print(f"⚠️ Advertencia: No se pudo exportar como {format}. Error: {str(e)[:100]}...")
        print("💡 Guardando como HTML interactivo en su lugar...")
        
        html_filepath = os.path.join(output_dir, f"{filename}.html")
        fig.write_html(html_filepath)
        
        print(f"✅ Gráfico guardado como HTML en: {html_filepath}")
        return html_filepath


def save_chart_with_path(fig: go.Figure, filepath: str) -> str:
    """
    Guarda un gráfico de Plotly usando una ruta específica.
    
    Args:
        fig (go.Figure): Figura de Plotly a guardar.
        filepath (str): Ruta completa del archivo a guardar.
        
    Returns:
        str: Ruta del archivo guardado.
    """
    # Extraer directorio, nombre base y extensión
    output_dir = os.path.dirname(filepath)
    filename_with_ext = os.path.basename(filepath)
    filename, ext = os.path.splitext(filename_with_ext)
    
    # Usar la función existente save_chart_as_image pero con el formato correcto
    if ext.lower() == '.png':
        format_type = 'png'
    elif ext.lower() == '.html':
        format_type = 'html'
    else:
        format_type = 'png'  # default
    
    try:
        # Crear directorio si no existe
        Path(output_dir).mkdir(exist_ok=True)
        
        if format_type == 'png':
            # Intentar guardar como PNG
            fig.write_image(filepath, width=1200, height=600)
            print(f"✅ Gráfico guardado como PNG: {filepath}")
            return filepath
        else:
            # Guardar como HTML
            fig.write_html(filepath)
            print(f"✅ Gráfico guardado como HTML: {filepath}")
            return filepath
            
    except Exception as e:
        # Si falla PNG, guardar como HTML
        print(f"⚠️ No se pudo guardar como {format_type}. Error: {str(e)[:100]}...")
        print("💡 Guardando como HTML interactivo en su lugar...")
        
        html_filepath = filepath.replace('.png', '.html')
        fig.write_html(html_filepath)
        print(f"✅ Gráfico guardado como HTML: {html_filepath}")
        return html_filepath


def generate_all_charts_and_save(
    portfolio_returns: pd.Series,
    asset_returns: pd.DataFrame,
    benchmark_returns: Optional[pd.Series] = None,
    output_dir: str = "outputs",
    portfolio_weights: Optional[Dict[str, float]] = None,
    generate_donut_chart: bool = True,
    generate_html: bool = False
) -> dict:
    """
    Genera todos los gráficos disponibles y los guarda como imágenes.

    Args:
        portfolio_returns (pd.Series): Retornos diarios del portafolio.
        asset_returns (pd.DataFrame): Retornos diarios de los activos.
        benchmark_returns (pd.Series, optional): Retornos del benchmark.
        output_dir (str): Directorio donde guardar las imágenes.
        portfolio_weights (Dict[str, float], optional): Pesos del portafolio para el gráfico donut.
        generate_donut_chart (bool): Si True, genera también el gráfico donut de composición.
        generate_html (bool): Si True, genera también archivos HTML interactivos.

    Returns:
        dict: Diccionario con los nombres de archivos y rutas guardadas.
    """
    # Importar el controlador de generación diaria
    try:
        from .daily_generation_control import DailyGenerationController
    except ImportError:
        # Fallback para cuando se ejecuta desde fuera del paquete
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from daily_generation_control import DailyGenerationController
    
    # Crear controlador con el directorio de salida
    daily_controller = DailyGenerationController(output_dir)
    
    saved_files = {}
    
    # 1. Gráfico de rendimiento acumulado
    fig1 = plot_cumulative_returns(portfolio_returns, benchmark_returns)
    cumulative_path = daily_controller.prepare_daily_file("rendimiento_acumulado", "png")
    saved_files["rendimiento_acumulado"] = save_chart_with_path(fig1, cumulative_path)
    
    # Si se requiere, también generar HTML
    if generate_html:
        cumulative_html_path = daily_controller.prepare_daily_file("rendimiento_acumulado", "html")
        saved_files["rendimiento_acumulado_html"] = save_chart_with_path(fig1, cumulative_html_path)
    
    # 2. Gráfico de drawdown
    fig2 = plot_drawdown_underwater(portfolio_returns)
    drawdown_path = daily_controller.prepare_daily_file("drawdown", "png")
    saved_files["drawdown"] = save_chart_with_path(fig2, drawdown_path)
    
    # Si se requiere, también generar HTML
    if generate_html:
        drawdown_html_path = daily_controller.prepare_daily_file("drawdown", "html")
        saved_files["drawdown_html"] = save_chart_with_path(fig2, drawdown_html_path)
    
    # 3. Heatmap de correlación
    fig3 = plot_correlation_heatmap(asset_returns)
    correlation_path = daily_controller.prepare_daily_file("correlacion", "png")
    saved_files["correlacion"] = save_chart_with_path(fig3, correlation_path)
    
    # Si se requiere, también generar HTML
    if generate_html:
        correlation_html_path = daily_controller.prepare_daily_file("correlacion", "html")
        saved_files["correlacion_html"] = save_chart_with_path(fig3, correlation_html_path)
    
    # 4. Gráfico donut de composición del portafolio (si se proporcionan los pesos)
    if generate_donut_chart and portfolio_weights:
        try:
            # Importar AssetClassifier para generar el gráfico donut
            try:
                from .asset_classifier import AssetClassifier
            except ImportError:
                # Fallback para cuando se ejecuta desde fuera del paquete
                import sys
                import os
                sys.path.append(os.path.dirname(__file__))
                from asset_classifier import AssetClassifier
            
            # Crear tickers y pesos para el clasificador
            tickers = list(portfolio_weights.keys())
            weights = portfolio_weights
            
            # Crear clasificador y generar gráfico donut
            classifier = AssetClassifier(cache_enabled=True)
            classification_df = classifier.classify_portfolio_assets(tickers, weights)
            donut_fig = classifier.create_donut_chart(classification_df)
            
            # Guardar gráfico donut como PNG usando control diario
            donut_path = daily_controller.prepare_daily_file("donut_chart", "png")
            saved_files["donut_chart"] = save_chart_with_path(donut_fig, donut_path)
            
            # También generar el gráfico de desglose usando control diario
            breakdown_fig = classifier.create_detailed_breakdown_chart(classification_df)
            breakdown_path = daily_controller.prepare_daily_file("breakdown_chart", "png")
            saved_files["breakdown_chart"] = save_chart_with_path(breakdown_fig, breakdown_path)
            
            # Si se requiere, también generar HTML para los gráficos de clasificación
            if generate_html:
                donut_html_path = daily_controller.prepare_daily_file("donut_chart", "html")
                saved_files["donut_chart_html"] = save_chart_with_path(donut_fig, donut_html_path)
                
                breakdown_html_path = daily_controller.prepare_daily_file("breakdown_chart", "html")
                saved_files["breakdown_chart_html"] = save_chart_with_path(breakdown_fig, breakdown_html_path)
            
        except Exception as e:
            print(f"⚠️ Advertencia: No se pudo generar el gráfico donut: {str(e)[:100]}...")
    
    return saved_files