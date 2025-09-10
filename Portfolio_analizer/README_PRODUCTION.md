# 📊 Portfolio Analyzer v2.0.0

<div align="center">

![Portfolio Analyzer](https://img.shields.io/badge/Portfolio-Analyzer-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8%2B-green?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-red?style=for-the-badge&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**Sistema completo para el análisis avanzado de portafolios de inversión**

*Combina análisis financiero robusto, optimización de portafolios y visualizaciones profesionales*

</div>

---

## 🚀 Características Principales

### 📈 Análisis Fundamental
- **Análisis Personalizado**: Introduce tickers y ponderaciones personalizadas
- **Métricas Avanzadas**: Rendimiento anualizado, volatilidad, ratios de Sharpe/Sortino/Calmar
- **Análisis de Riesgo**: VaR, máximo drawdown, skewness, kurtosis
- **Benchmarking**: Comparación contra índices de referencia

### 🎯 Optimización de Portafolios
- **Teoría Moderna de Portafolios**: Implementación completa de Markowitz
- **Frontera Eficiente**: Cálculo automático de portafolios óptimos
- **Máximo Ratio de Sharpe**: Optimización riesgo-rendimiento
- **Mínima Volatilidad**: Portafolios conservadores

### 📊 Visualizaciones Profesionales
- **Gráficos Interactivos**: Plotly para visualizaciones de alta calidad
- **Exportación Automática**: PNG de alta resolución (1200x600)
- **Múltiples Formatos**: HTML interactivo y PNG estático
- **Gráficos Incluidos**:
  - Rendimiento acumulado vs benchmark
  - Análisis de drawdown underwater
  - Heatmap de correlaciones
  - Clasificación de activos (donut charts)

### 🔧 API REST Completa
- **FastAPI**: API moderna y rápida con documentación automática
- **Validación Automática**: Pydantic para validación de datos
- **CORS**: Soporte completo para aplicaciones web
- **Endpoints Múltiples**: Análisis personalizado, diversificado y clasificación

### 📑 Reportes Automatizados
- **Markdown Profesional**: Reportes completos automáticos
- **Análisis Automático**: Interpretación inteligente de métricas
- **Recomendaciones**: Sugerencias basadas en análisis
- **Integración de Gráficos**: Imágenes automáticamente incluidas

## 🛠️ Instalación y Configuración

### Requisitos del Sistema
- Python 3.8 o superior
- Conexión a internet (para datos de mercado)
- 4GB RAM recomendados
- 1GB espacio en disco

### Instalación Rápida

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd portfolio_analyzer

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Verificar instalación
python ejemplo_reporte.py
```

### Instalación para Desarrollo

```bash
# Instalar dependencias adicionales de desarrollo
pip install -r requirements.txt
pip install pytest black flake8 mypy

# Ejecutar tests
python -m pytest tests/
```

## 🚀 Guía de Uso

### 1. 📊 Dashboard Interactivo (Jupyter Notebook)

```bash
jupyter notebook notebooks/main_app.ipynb
```

**Perfecto para:**
- Exploración interactiva de datos
- Prototipado rápido
- Análisis ad-hoc
- Educación y aprendizaje

### 2. 🤖 API REST (Producción)

```bash
# Iniciar servidor de desarrollo
python main_api.py

# O usar uvicorn directamente
uvicorn main_api:app --reload --host 0.0.0.0 --port 8000
```

**Endpoints disponibles:**
- `GET /docs` - Documentación interactiva
- `POST /analyze` - Análisis personalizado
- `POST /diversified-analysis` - Análisis diversificado
- `POST /asset-classification` - Clasificación de activos
- `GET /health` - Estado del sistema

### 3. 📝 Generación de Reportes (Scripts)

```bash
python ejemplo_reporte.py
```

**Perfecto para:**
- Reportes automáticos programados
- Análisis batch de múltiples portafolios
- Integración en sistemas existentes

### 4. 🔧 Uso Programático (Biblioteca)

```python
from src.portfolio_metrics import generate_complete_analysis
from src.data_manager import fetch_portfolio_data, calculate_returns

# Configurar portafolio
portfolio_weights = {
    'AAPL': 0.25,
    'GOOGL': 0.25, 
    'MSFT': 0.25,
    'AMZN': 0.25
}

# Descargar datos
start_date = "2022-01-01"
end_date = "2024-12-31"
tickers = list(portfolio_weights.keys())

prices_df = fetch_portfolio_data(tickers, start_date, end_date)
asset_returns = calculate_returns(prices_df)

# Calcular retornos del portafolio
weights_array = np.array(list(portfolio_weights.values()))
portfolio_returns = calculate_portfolio_returns(asset_returns, weights_array)

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

## 📂 Estructura del Proyecto

```
portfolio_analyzer/
├── 📁 src/                          # Código fuente principal
│   ├── 📄 __init__.py              # Módulo principal del paquete
│   ├── 📄 data_manager.py          # Gestión de datos financieros
│   ├── 📄 portfolio_metrics.py     # Métricas y optimización
│   ├── 📄 interactive_charts.py    # Visualizaciones interactivas
│   ├── 📄 api_responses.py         # Respuestas estructuradas para API
│   └── 📄 asset_classifier.py      # Clasificación automática de activos
├── 📁 notebooks/                   # Jupyter Notebooks
│   └── 📄 main_app.ipynb          # Dashboard interactivo principal
├── 📁 tests/                       # Pruebas unitarias
│   ├── 📄 test_data_manager.py     # Tests del gestor de datos
│   └── 📄 test_portfolio_metrics.py # Tests de métricas
├── 📁 outputs/                     # Archivos generados automáticamente
│   ├── 📄 *.png                   # Gráficos exportados
│   ├── 📄 *.md                    # Reportes en Markdown
│   └── 📄 *.json                  # Respuestas de API
├── 📄 main_api.py                 # API FastAPI principal
├── 📄 ejemplo_reporte.py           # Script de ejemplo completo
├── 📄 requirements.txt             # Dependencias del proyecto
├── 📄 .gitignore                   # Archivos ignorados por Git
└── 📄 README.md                   # Esta documentación
```

## 📊 Archivos Generados

El sistema genera automáticamente varios tipos de archivos:

| Archivo | Descripción | Formato | Tamaño |
|---------|-------------|---------|---------|
| `reporte_portafolio_YYYYMMDD_HHMMSS.md` | Reporte completo con análisis y recomendaciones | Markdown | ~15-25KB |
| `rendimiento_acumulado_YYYYMMDD_HHMMSS.png` | Gráfico de evolución del rendimiento | PNG (1200x600) | ~200-400KB |
| `drawdown_underwater_YYYYMMDD_HHMMSS.png` | Gráfico de análisis de drawdown | PNG (1200x600) | ~150-300KB |
| `matriz_correlacion_YYYYMMDD_HHMMSS.png` | Heatmap de correlación entre activos | PNG (1200x600) | ~100-250KB |
| `donut_chart_YYYYMMDD_HHMMSS.png` | Clasificación de activos por sectores | PNG (1200x800) | ~200-350KB |
| `api_response_YYYYMMDD_HHMMSS.json` | Respuesta completa para API | JSON | ~50-100KB |

## 🔧 Dependencias Principales

| Biblioteca | Propósito | Versión | Tamaño |
|------------|-----------|---------|---------|
| **pandas** | Manipulación de datos financieros | ≥1.3.0 | ~20MB |
| **numpy** | Cálculos numéricos y arrays | ≥1.21.0 | ~15MB |
| **yfinance** | Descarga de datos de Yahoo Finance | ≥0.1.87 | ~2MB |
| **quantstats** | Métricas de rendimiento financiero | Latest | ~5MB |
| **PyPortfolioOpt** | Optimización de portafolios | Latest | ~3MB |
| **plotly** | Gráficos interactivos | ≥5.15.0 | ~30MB |
| **kaleido** | Exportación de gráficos | ≥0.2.1 | ~50MB |
| **fastapi** | Framework web para API | ≥0.68.0 | ~10MB |
| **uvicorn** | Servidor ASGI | ≥0.15.0 | ~5MB |
| **pydantic** | Validación de datos | ≥1.8.0 | ~3MB |

## 📚 Documentación de API

### Endpoints Principales

#### POST `/analyze`
Análisis completo de portafolio personalizado.

**Request Body:**
```json
{
  "tickers": ["AAPL", "GOOGL", "MSFT", "AMZN"],
  "weights": {
    "AAPL": 0.25,
    "GOOGL": 0.25,
    "MSFT": 0.25,
    "AMZN": 0.25
  },
  "start_date": "2022-01-01",
  "end_date": "2024-12-31",
  "risk_free_rate": 0.02
}
```

**Response:**
```json
{
  "status": "success",
  "analysis_period": {
    "start_date": "2022-01-01",
    "end_date": "2024-12-31",
    "total_days": 731
  },
  "performance_metrics": {
    "annual_return": 15.2,
    "annual_volatility": 18.5,
    "sharpe_ratio": 0.87,
    "max_drawdown": -12.3
  },
  "optimization_results": {
    "max_sharpe": {...},
    "min_volatility": {...}
  },
  "charts": {
    "cumulative_returns": "path/to/chart.png",
    "drawdown": "path/to/drawdown.png"
  }
}
```

#### POST `/diversified-analysis`
Análisis de portafolio diversificado automático.

#### POST `/asset-classification`
Clasificación automática de activos por sector/industria.

#### GET `/health`
Estado del sistema y verificación de dependencias.

### Documentación Interactiva

Una vez iniciado el servidor, visita:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📈 Ejemplo de Reporte Generado

Los reportes automáticos incluyen:

### 📊 Resumen Ejecutivo
- Composición del portafolio con pesos
- Métricas clave de rendimiento y riesgo
- Período de análisis y datos procesados

### 🎯 Optimización de Portafolios
- Portafolio de máximo ratio de Sharpe
- Portafolio de mínima volatilidad
- Composiciones óptimas recomendadas
- Comparación de performance

### 📈 Análisis de Correlaciones
- Matriz de correlación completa
- Análisis de diversificación
- Identificación de activos correlacionados

### 📊 Visualizaciones Integradas
- Gráficos automáticamente incluidos
- Enlaces a versiones de alta resolución
- Formatos múltiples (PNG/HTML)

### 💡 Conclusiones y Recomendaciones
- Análisis automático basado en métricas
- Recomendaciones de optimización personalizadas
- Evaluación de riesgo y sugerencias

## 🔮 Roadmap y Mejoras Futuras

### v2.1.0 (Q3 2025)
- [ ] **Rolling Statistics**: Métricas móviles para análisis temporal
- [ ] **Análisis de Escenarios**: Simulación Monte Carlo
- [ ] **Base de Datos**: Persistencia de análisis históricos
- [ ] **Autenticación**: Sistema de usuarios y permisos

### v2.2.0 (Q4 2025)
- [ ] **Dashboard Web**: Interfaz web completa independiente
- [ ] **Análisis de Factores**: Descomposición por factores de riesgo
- [ ] **Machine Learning**: Predicción de rendimientos
- [ ] **API Webhooks**: Notificaciones automáticas

### v2.3.0 (Q1 2026)
- [ ] **Backtesting Avanzado**: Pruebas históricas sofisticadas
- [ ] **Análisis ESG**: Métricas de sostenibilidad
- [ ] **Criptomonedas**: Soporte para activos digitales
- [ ] **Integración Brokers**: APIs de brokers populares

## 🧪 Testing y Calidad

### Ejecutar Tests

```bash
# Tests básicos
python -m pytest tests/ -v

# Tests con coverage
python -m pytest tests/ --cov=src --cov-report=html

# Tests específicos
python -m pytest tests/test_portfolio_metrics.py -v
```

### Linting y Formateo

```bash
# Formatear código
black src/ tests/ *.py

# Linting
flake8 src/ tests/ *.py

# Type checking
mypy src/
```

### CI/CD

El proyecto incluye configuración para:
- GitHub Actions para CI/CD
- Tests automáticos en Python 3.8, 3.9, 3.10, 3.11
- Linting y formateo automático
- Generación de reportes de coverage

## 🤝 Contribuciones

Las contribuciones son bienvenidas y apreciadas. Por favor sigue estos pasos:

### Proceso de Contribución

1. **Fork** el proyecto
2. **Crear rama** para tu feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. **Push** a la rama (`git push origin feature/AmazingFeature`)
5. **Abrir Pull Request**

### Estándares de Código

- Seguir PEP 8 para estilo de código Python
- Incluir docstrings en todas las funciones públicas
- Añadir tests para nuevas funcionalidades
- Mantener coverage de tests > 80%

### Tipos de Contribuciones

- 🐛 **Bug Reports**: Reportar errores encontrados
- 💡 **Feature Requests**: Sugerir nuevas funcionalidades
- 📝 **Documentación**: Mejorar docs y ejemplos
- 🧪 **Tests**: Añadir o mejorar tests
- 🔧 **Code**: Implementar features o fixes

## 📜 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

```
MIT License

Copyright (c) 2025 Portfolio Analyzer Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🆘 Soporte y Ayuda

### Documentación
- **README**: Esta documentación completa
- **API Docs**: `/docs` endpoint cuando corres la API
- **Examples**: Revisa `ejemplo_reporte.py` para ejemplos

### Comunidad
- **Issues**: [GitHub Issues](https://github.com/your-repo/portfolio-analyzer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/portfolio-analyzer/discussions)
- **Wiki**: [Project Wiki](https://github.com/your-repo/portfolio-analyzer/wiki)

### Solución de Problemas Comunes

**Error: "No module named 'yfinance'"**
```bash
pip install -r requirements.txt
```

**Error: "Kaleido not found"**
```bash
pip install kaleido>=0.2.1
```

**API no responde**
```bash
# Verificar puerto
netstat -an | grep 8000

# Reiniciar servidor
python main_api.py
```

**Gráficos no se generan**
```bash
# Verificar permisos de escritura
ls -la outputs/

# Crear directorio si no existe
mkdir -p outputs
```

---

<div align="center">

**¿Te resulta útil este proyecto? ⭐ Dale una estrella en GitHub**

Made with ❤️ by Portfolio Analyzer Team

[📊 Reportar Bug](https://github.com/your-repo/issues) • [💡 Solicitar Feature](https://github.com/your-repo/issues) • [📖 Documentación](https://github.com/your-repo/wiki)

</div>
