# Analizador Interactivo de Portafolios de Inversión

Este proyecto ofrece un sistema completo para el análisis avanzado de portafolios de inversión. Combina un dashboard interactivo en Jupyter Notebook con capacidades de generación automática de reportes y exportación de gráficos profesionales.

## 🚀 Características Principales

### Análisis Fundamental
- **Análisis Personalizado:** Introduce tus propios tickers de activos y la ponderación de cada uno en el portafolio.
- **Rendimiento y Riesgo:** Calcula y muestra métricas clave como el Rendimiento Anualizado, Volatilidad, Ratio de Sharpe, Ratio de Sortino, y Máximo Drawdown.
- **Benchmarking:** Compara el rendimiento de tu portafolio contra un benchmark de referencia (ej. S&P 500).

### Visualizaciones Interactivas
- Gráfico de **Rendimiento Acumulado** del portafolio vs. el benchmark
- Gráfico de **Drawdown (Underwater Plot)** para visualizar las caídas del portafolio
- **Heatmap de Correlación** entre los activos para entender la diversificación

### Optimización de Portafolios
- Calcula el portafolio de **Máximo Ratio de Sharpe**
- Calcula el portafolio de **Mínima Volatilidad**
- Utiliza la **Teoría Moderna de Portafolios** para optimización

### 🆕 Funcionalidades Avanzadas
- **Clasificación de Activos:** Clasifica automáticamente los activos del portafolio en categorías como 'Renta Variable', 'Renta Fija', 'Criptomonedas', etc.
- **Datos de Mercado en Tiempo Real:** Obtiene información actualizada de los activos para reflejar el estado del mercado al momento del análisis.
- **Control de Generación de Reportes:** Evita la duplicación de reportes, permitiendo generar solo un reporte por día.
- **Exportación Automática de Gráficos:** Guarda todos los gráficos como imágenes PNG de alta resolución (1200x600)
- **Reportes Completos en Markdown:** Genera reportes profesionales con todas las métricas, análisis y recomendaciones automáticas
- **Análisis de Riesgo Detallado:** Incluye VaR, Skewness, Kurtosis y análisis de correlaciones
- **Interfaz Amigable:** Dashboard interactivo con `ipywidgets` para uso fácil

## 🛠️ Instalación y Configuración

### Requisitos
- Python 3.8 o superior
- Conexión a internet (para descargar datos de mercado)

### Instalación
1. **Clona el repositorio:**
   ```bash
   git clone <url-del-repositorio>
   cd portfolio_analyzer
   ```

2. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **¡Listo para usar!**

## 🚀 Formas de Uso

### 1. Dashboard Interactivo (Recomendado para Exploración)
```bash
jupyter notebook notebooks/main_app.ipynb
```
- Interfaz visual intuitiva
- Configuración interactiva de parámetros
- Visualización inmediata de resultados

### 2. Generación Automática de Reportes (Recomendado para Informes)
```bash
python ejemplo_reporte.py
```
- Genera reportes completos automáticamente
- Exporta gráficos en alta resolución
- Crea análisis profesional en formato Markdown

### 3. Uso Programático (Recomendado para Integración)
```python
from src.portfolio_metrics import generate_complete_analysis

# Configurar datos del portafolio
portfolio_weights = {
    'AAPL': 0.25,
    'GOOGL': 0.25, 
    'MSFT': 0.25,
    'AMZN': 0.25
}

# Ejecutar análisis completo
output_files = generate_complete_analysis(
    portfolio_returns=portfolio_returns,
    asset_returns=asset_returns,
    portfolio_weights=portfolio_weights,
    risk_free_rate=0.02,
    output_dir="mi_analisis"
)

print(f"Reporte generado: {output_files['markdown_report']}")
```

## 📊 Archivos Generados

Cuando ejecutes el análisis completo, se crearán automáticamente en la carpeta `outputs/`:

| Archivo | Descripción | Formato |
|---------|-------------|---------|
| `reporte_portafolio_YYYYMMDD_HHMMSS.md` | Reporte completo con todas las métricas y análisis | Markdown |
| `rendimiento_acumulado_YYYYMMDD_HHMMSS.png` | Gráfico de evolución del rendimiento | PNG (1200x600) |
| `drawdown_underwater_YYYYMMDD_HHMMSS.png` | Gráfico de análisis de drawdown | PNG (1200x600) |
| `matriz_correlacion_YYYYMMDD_HHMMSS.png` | Heatmap de correlación entre activos | PNG (1200x600) |

## 📂 Estructura del Proyecto

```
portfolio_analyzer/
├── notebooks/
│   └── main_app.ipynb          # Dashboard interactivo principal
├── src/
│   ├── data_manager.py         # Obtención y limpieza de datos
│   ├── portfolio_metrics.py   # Cálculo de métricas y optimización
│   └── interactive_charts.py  # Generación de gráficos
├── tests/
│   ├── test_data_manager.py    # Pruebas del gestor de datos
│   └── test_portfolio_metrics.py # Pruebas de métricas
├── outputs/                    # Archivos generados automáticamente
│   ├── *.png                   # Gráficos exportados
│   └── *.md                    # Reportes en Markdown
├── ejemplo_reporte.py          # Script de ejemplo
├── requirements.txt            # Dependencias
└── README.md                   # Este archivo
```

## 🔧 Dependencias Principales

| Biblioteca | Propósito | Versión |
|------------|-----------|---------|
| `pandas` | Manipulación de datos | Última |
| `numpy` | Cálculos numéricos | Última |
| `yfinance` | Descarga de datos financieros | Última |
| `quantstats` | Métricas de rendimiento financiero | Última |
| `PyPortfolioOpt` | Optimización de portafolios | Última |
| `plotly` | Gráficos interactivos | ≥6.1.1 |
| `kaleido` | Exportación de gráficos | ≥0.2.1 |
| `ipywidgets` | Interfaz interactiva | Última |

## 📚 Documentación de Módulos

### `src/asset_classifier.py`
**Funciones principales:**
- `classify_assets()`: Clasifica los activos de un portafolio en diferentes categorías.

### `src/daily_generation_control.py`
**Funciones principales:**
- `can_generate_report()`: Verifica si ya se ha generado un reporte en el día actual.

### `src/data_manager.py`
**Funciones principales:**
- `fetch_portfolio_data()`: Descarga datos históricos de Yahoo Finance
- `calculate_returns()`: Calcula retornos diarios con métodos simple o logarítmico

### `src/portfolio_metrics.py`
**Funciones principales:**
- `get_current_asset_info()`: Obtiene información de mercado en tiempo real para los activos.
- `calculate_portfolio_returns()`: Calcula retornos del portafolio
- `generate_performance_summary()`: Genera métricas de rendimiento completas
- `find_optimal_portfolios()`: Optimización usando frontera eficiente
- `generate_markdown_report()`: Crea reportes profesionales en Markdown
- `generate_complete_analysis()`: Función principal para análisis completo

### `src/interactive_charts.py`
**Funciones principales:**
- `plot_cumulative_returns()`: Gráfico de rendimiento acumulado
- `plot_drawdown_underwater()`: Gráfico de drawdown
- `plot_correlation_heatmap()`: Heatmap de correlación
- `save_chart_as_image()`: Exportación de gráficos a imágenes
- `generate_all_charts_and_save()`: Generación y guardado masivo

## 📈 Ejemplo de Reporte Generado

El sistema genera reportes profesionales que incluyen:

### 📊 Resumen Ejecutivo
- Composición del portafolio con pesos
- Métricas clave de rendimiento y riesgo
- Ratios de Sharpe, Sortino y Calmar

### 🎯 Optimización de Portafolios
- Portafolio de máximo ratio de Sharpe
- Portafolio de mínima volatilidad
- Composiciones óptimas recomendadas

### 📈 Análisis de Correlaciones
- Matriz de correlación completa
- Análisis de diversificación

### 📊 Visualizaciones
- Gráficos integrados automáticamente
- Enlaces a imágenes de alta resolución

### 💡 Conclusiones y Recomendaciones
- Análisis automático basado en métricas
- Recomendaciones de optimización
- Evaluación de riesgo

## 🔮 Posibles Mejoras Futuras

- **Análisis de Rolling Statistics:** Métricas móviles para análisis temporal
- **Análisis de Escenarios:** Simulación bajo diferentes condiciones de mercado
- **Optimización Avanzada:** Más objetivos y restricciones de optimización
- **Dashboard Web:** Interfaz web independiente
- **Análisis de Factores:** Descomposición por factores de riesgo
- **Backtesting Avanzado:** Pruebas históricas más sofisticadas

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📜 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

---

**¿Necesitas ayuda?** 
- Revisa el archivo `ejemplo_reporte.py` para ver ejemplos de uso
- Consulta la documentación de módulos arriba
- Abre un issue en GitHub para reportar problemas
