# 🔧 Guía de Instalación - Portfolio Analyzer

Esta guía proporciona instrucciones detalladas para instalar y configurar el Portfolio Analyzer en diferentes entornos.

## 📋 Requisitos del Sistema

### Mínimos
- **Python**: 3.8 o superior
- **RAM**: 2GB libres
- **Disco**: 500MB libres
- **Internet**: Conexión estable para descargar datos

### Recomendados
- **Python**: 3.10 o 3.11
- **RAM**: 4GB libres
- **Disco**: 2GB libres
- **Procesador**: Multi-core para análisis rápidos

## 🚀 Instalación Rápida

### Windows

```powershell
# 1. Verificar Python
python --version

# 2. Clonar repositorio
git clone <url-del-repositorio>
cd portfolio_analyzer

# 3. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Verificar instalación
python ejemplo_reporte.py
```

### macOS/Linux

```bash
# 1. Verificar Python
python3 --version

# 2. Clonar repositorio
git clone <url-del-repositorio>
cd portfolio_analyzer

# 3. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Verificar instalación
python ejemplo_reporte.py
```

## 🐳 Instalación con Docker

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  portfolio-analyzer:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./outputs:/app/outputs
      - ./data:/app/data
    environment:
      - PYTHONPATH=/app
```

### Comandos Docker

```bash
# Construir imagen
docker build -t portfolio-analyzer .

# Ejecutar contenedor
docker run -p 8000:8000 portfolio-analyzer

# Con docker-compose
docker-compose up -d
```

## ☁️ Instalación en la Nube

### Google Colab

```python
# Instalar en Google Colab
!git clone <url-del-repositorio>
%cd portfolio_analyzer
!pip install -r requirements.txt

# Usar en Colab
from src.portfolio_metrics import generate_complete_analysis
```

### AWS EC2

```bash
# Conectar a EC2
ssh -i your-key.pem ubuntu@your-ec2-instance

# Instalar Python y Git
sudo apt update
sudo apt install python3 python3-pip git

# Clonar e instalar
git clone <url-del-repositorio>
cd portfolio_analyzer
pip3 install -r requirements.txt

# Ejecutar API
python3 main_api.py
```

### Heroku

```bash
# Procfile
web: uvicorn main_api:app --host 0.0.0.0 --port $PORT

# Desplegar
heroku create your-app-name
git push heroku main
```

## 🔧 Configuración Avanzada

### Variables de Entorno

Crear archivo `.env`:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# Data Sources
YAHOO_FINANCE_TIMEOUT=30
DATA_CACHE_ENABLED=True

# Output Configuration
OUTPUT_DIR=outputs
CHART_DPI=300
CHART_WIDTH=1200
CHART_HEIGHT=600

# Performance
MAX_WORKERS=4
CACHE_SIZE=100
```

### Configuración de Base de Datos (Opcional)

```python
# database_config.py
DATABASE_CONFIG = {
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "portfolio_analyzer",
        "username": "postgres",
        "password": "your_password"
    },
    "mongodb": {
        "host": "localhost",
        "port": 27017,
        "database": "portfolio_analyzer"
    }
}
```

## 🧪 Verificación de Instalación

### Test Básico

```python
# test_installation.py
import sys
import importlib

def test_dependencies():
    """Verificar que todas las dependencias estén instaladas"""
    required_packages = [
        'pandas', 'numpy', 'yfinance', 'quantstats',
        'pypfopt', 'plotly', 'fastapi', 'uvicorn'
    ]
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"❌ {package} - FALTA")
            return False
    
    return True

def test_functionality():
    """Test básico de funcionalidad"""
    try:
        from src.data_manager import fetch_portfolio_data
        from src.portfolio_metrics import calculate_portfolio_returns
        
        # Test básico
        print("✅ Módulos principales - OK")
        return True
    except Exception as e:
        print(f"❌ Error en módulos: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verificando instalación...")
    
    deps_ok = test_dependencies()
    func_ok = test_functionality()
    
    if deps_ok and func_ok:
        print("\n🎉 ¡Instalación exitosa!")
    else:
        print("\n⚠️ Problemas encontrados en la instalación")
```

### Test de API

```bash
# Iniciar API
python main_api.py &

# Test endpoint
curl -X GET "http://localhost:8000/health"

# Test análisis básico
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["AAPL", "MSFT"],
    "weights": {"AAPL": 0.5, "MSFT": 0.5}
  }'
```

## 🐛 Solución de Problemas

### Problemas Comunes

#### Error: "No module named 'yfinance'"
```bash
# Solución
pip install yfinance>=0.1.87
```

#### Error: "Kaleido not found"
```bash
# Solución
pip install kaleido>=0.2.1

# Si persiste en Linux
sudo apt-get install -y chromium-browser
```

#### Error: "Permission denied" en outputs/
```bash
# Solución
chmod -R 755 outputs/
mkdir -p outputs
```

#### Error: "ModuleNotFoundError: No module named 'src'"
```bash
# Solución - Agregar al PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# O en Windows
set PYTHONPATH=%PYTHONPATH%;%cd%
```

### Logs y Debugging

```python
# Habilitar logging detallado
import logging
logging.basicConfig(level=logging.DEBUG)

# Ver errores de descarga de datos
import yfinance as yf
yf.pdr_override()
```

### Performance Issues

```python
# Configurar para mejor rendimiento
import os
os.environ['NUMEXPR_MAX_THREADS'] = '4'
os.environ['OMP_NUM_THREADS'] = '4'

# Usar caché para datos
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_fetch_data(ticker, start, end):
    return fetch_portfolio_data([ticker], start, end)
```

## 📊 Configuración de Desarrollo

### Entorno de Desarrollo

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Configurar IDE (VS Code)
cp .vscode/settings.json.example .vscode/settings.json
```

### requirements-dev.txt

```txt
# Todas las dependencias de requirements.txt +
pytest>=6.0.0
pytest-cov>=2.10.0
black>=21.0.0
flake8>=3.8.0
mypy>=0.800
pre-commit>=2.10.0
jupyter>=1.0.0
ipykernel>=6.0.0
```

### Configuración de Tests

```bash
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
```

## 🌐 Configuración para Producción

### Nginx (Proxy Reverso)

```nginx
# /etc/nginx/sites-available/portfolio-analyzer
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service

```ini
# /etc/systemd/system/portfolio-analyzer.service
[Unit]
Description=Portfolio Analyzer API
After=network.target

[Service]
Type=exec
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/portfolio_analyzer
Environment=PATH=/home/ubuntu/portfolio_analyzer/venv/bin
ExecStart=/home/ubuntu/portfolio_analyzer/venv/bin/uvicorn main_api:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### SSL/HTTPS (Let's Encrypt)

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d your-domain.com

# Auto-renovación
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

## 📝 Notas Adicionales

### Compatibilidad de Versiones

| Python | Estado | Notas |
|--------|--------|-------|
| 3.8 | ✅ Soportado | Versión mínima |
| 3.9 | ✅ Soportado | Recomendado |
| 3.10 | ✅ Soportado | Recomendado |
| 3.11 | ✅ Soportado | Mejor rendimiento |
| 3.12 | ⚠️ Beta | Algunas dependencias pueden fallar |

### Recursos del Sistema

- **Memoria**: ~200MB base + ~50MB por análisis
- **CPU**: Beneficia de múltiples cores
- **Disco**: ~100MB de caché por día de datos
- **Red**: ~1MB por ticker por año de datos

### Actualizaciones

```bash
# Actualizar dependencias
pip install --upgrade -r requirements.txt

# Verificar versiones obsoletas
pip list --outdated

# Actualización selectiva
pip install --upgrade pandas numpy plotly
```

---

**¿Problemas con la instalación?**  
Abre un [issue en GitHub](https://github.com/your-repo/issues) con:
- Sistema operativo y versión
- Versión de Python
- Mensaje de error completo
- Pasos que llevaron al error
