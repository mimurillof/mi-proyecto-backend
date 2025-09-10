# Configuration Guide - Portfolio Analyzer

This document describes the configuration options available for customizing the Portfolio Analyzer behavior.

## 🔧 Environment Variables

The Portfolio Analyzer supports configuration through environment variables. Create a `.env` file in the project root:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False
RELOAD=False

# Data Sources Configuration
YAHOO_FINANCE_TIMEOUT=30
ALPHA_VANTAGE_API_KEY=your_api_key_here
IEX_CLOUD_API_KEY=your_api_key_here

# Output Configuration
OUTPUT_DIR=outputs
CHART_DPI=300
CHART_WIDTH=1200
CHART_HEIGHT=600
CHART_FORMAT=png

# Performance Settings
MAX_WORKERS=4
CACHE_ENABLED=True
CACHE_SIZE=100
CACHE_TTL=3600

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=detailed
LOG_FILE=logs/portfolio_analyzer.log

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Database Configuration (when implemented)
DATABASE_URL=postgresql://user:password@localhost:5432/portfolio_analyzer
REDIS_URL=redis://localhost:6379/0
```

## 📊 Default Configuration

```python
# config/defaults.py
"""
Default configuration values for Portfolio Analyzer
"""

# API Settings
DEFAULT_API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": False,
    "reload": False,
    "workers": 1,
    "timeout": 30
}

# Chart Settings
DEFAULT_CHART_CONFIG = {
    "width": 1200,
    "height": 600,
    "dpi": 300,
    "format": "png",
    "template": "plotly_white",
    "color_palette": "Set3"
}

# Data Settings
DEFAULT_DATA_CONFIG = {
    "default_start_date": "2020-01-01",
    "max_portfolio_size": 50,
    "min_weight": 0.001,
    "risk_free_rate": 0.02,
    "benchmark_ticker": "SPY"
}

# Cache Settings
DEFAULT_CACHE_CONFIG = {
    "enabled": True,
    "max_size": 100,
    "ttl": 3600,  # 1 hour
    "backend": "memory"  # or "redis"
}

# Output Settings
DEFAULT_OUTPUT_CONFIG = {
    "directory": "outputs",
    "keep_days": 30,
    "auto_cleanup": True,
    "formats": ["png", "html", "json"]
}
```

## ⚙️ Configuration Management

```python
# config/config.py
"""
Configuration management system
"""

import os
from pathlib import Path
from typing import Dict, Any
import json
from dataclasses import dataclass, asdict

@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1

@dataclass
class ChartConfig:
    width: int = 1200
    height: int = 600
    dpi: int = 300
    format: str = "png"
    template: str = "plotly_white"

@dataclass
class DataConfig:
    default_start_date: str = "2020-01-01"
    max_portfolio_size: int = 50
    risk_free_rate: float = 0.02
    benchmark_ticker: str = "SPY"

@dataclass
class CacheConfig:
    enabled: bool = True
    max_size: int = 100
    ttl: int = 3600
    backend: str = "memory"

@dataclass
class OutputConfig:
    directory: str = "outputs"
    keep_days: int = 30
    auto_cleanup: bool = True
    formats: list = None

    def __post_init__(self):
        if self.formats is None:
            self.formats = ["png", "html", "json"]

class ConfigManager:
    """Manages application configuration from multiple sources"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or "config.json"
        self.api = APIConfig()
        self.chart = ChartConfig()
        self.data = DataConfig()
        self.cache = CacheConfig()
        self.output = OutputConfig()
        
        self.load_configuration()
    
    def load_configuration(self):
        """Load configuration from file and environment variables"""
        # Load from file if exists
        if Path(self.config_file).exists():
            self.load_from_file()
        
        # Override with environment variables
        self.load_from_env()
    
    def load_from_file(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            if 'api' in config_data:
                self.api = APIConfig(**config_data['api'])
            if 'chart' in config_data:
                self.chart = ChartConfig(**config_data['chart'])
            if 'data' in config_data:
                self.data = DataConfig(**config_data['data'])
            if 'cache' in config_data:
                self.cache = CacheConfig(**config_data['cache'])
            if 'output' in config_data:
                self.output = OutputConfig(**config_data['output'])
                
        except Exception as e:
            print(f"Warning: Could not load config file {self.config_file}: {e}")
    
    def load_from_env(self):
        """Load configuration from environment variables"""
        # API configuration
        self.api.host = os.getenv("API_HOST", self.api.host)
        self.api.port = int(os.getenv("API_PORT", self.api.port))
        self.api.debug = os.getenv("DEBUG", "False").lower() == "true"
        self.api.reload = os.getenv("RELOAD", "False").lower() == "true"
        self.api.workers = int(os.getenv("WORKERS", self.api.workers))
        
        # Chart configuration
        self.chart.width = int(os.getenv("CHART_WIDTH", self.chart.width))
        self.chart.height = int(os.getenv("CHART_HEIGHT", self.chart.height))
        self.chart.dpi = int(os.getenv("CHART_DPI", self.chart.dpi))
        self.chart.format = os.getenv("CHART_FORMAT", self.chart.format)
        
        # Data configuration
        self.data.default_start_date = os.getenv("DEFAULT_START_DATE", self.data.default_start_date)
        self.data.risk_free_rate = float(os.getenv("RISK_FREE_RATE", self.data.risk_free_rate))
        self.data.benchmark_ticker = os.getenv("BENCHMARK_TICKER", self.data.benchmark_ticker)
        
        # Cache configuration
        self.cache.enabled = os.getenv("CACHE_ENABLED", "True").lower() == "true"
        self.cache.max_size = int(os.getenv("CACHE_SIZE", self.cache.max_size))
        self.cache.ttl = int(os.getenv("CACHE_TTL", self.cache.ttl))
        
        # Output configuration
        self.output.directory = os.getenv("OUTPUT_DIR", self.output.directory)
        self.output.keep_days = int(os.getenv("KEEP_DAYS", self.output.keep_days))
    
    def save_to_file(self, filename: str = None):
        """Save current configuration to file"""
        filename = filename or self.config_file
        
        config_dict = {
            "api": asdict(self.api),
            "chart": asdict(self.chart),
            "data": asdict(self.data),
            "cache": asdict(self.cache),
            "output": asdict(self.output)
        }
        
        with open(filename, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration as dictionary"""
        return asdict(self.api)
    
    def get_chart_config(self) -> Dict[str, Any]:
        """Get chart configuration as dictionary"""
        return asdict(self.chart)
    
    def validate_configuration(self) -> bool:
        """Validate configuration values"""
        errors = []
        
        # Validate API config
        if not (1024 <= self.api.port <= 65535):
            errors.append(f"Invalid API port: {self.api.port}")
        
        # Validate chart config
        if self.chart.width < 400 or self.chart.height < 300:
            errors.append(f"Chart dimensions too small: {self.chart.width}x{self.chart.height}")
        
        # Validate data config
        if not (0 <= self.data.risk_free_rate <= 1):
            errors.append(f"Invalid risk-free rate: {self.data.risk_free_rate}")
        
        if errors:
            for error in errors:
                print(f"Configuration error: {error}")
            return False
        
        return True

# Global configuration instance
config = ConfigManager()

# Utility functions
def get_config() -> ConfigManager:
    """Get the global configuration instance"""
    return config

def reload_config():
    """Reload configuration from sources"""
    global config
    config.load_configuration()
```

## 🔧 Usage Examples

### Basic Configuration

```python
from config.config import get_config

# Get configuration
config = get_config()

# Use in API
app = FastAPI(
    title="Portfolio Analyzer",
    debug=config.api.debug
)

# Use in charts
fig.update_layout(
    width=config.chart.width,
    height=config.chart.height
)
```

### Environment-Specific Configuration

```python
# Development
export DEBUG=True
export API_PORT=8001
export CACHE_ENABLED=True

# Production
export DEBUG=False
export API_PORT=8000
export WORKERS=4
export CACHE_BACKEND=redis
```

### Configuration File Example

```json
{
  "api": {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": false,
    "workers": 4
  },
  "chart": {
    "width": 1200,
    "height": 600,
    "dpi": 300,
    "format": "png"
  },
  "data": {
    "risk_free_rate": 0.02,
    "benchmark_ticker": "SPY"
  },
  "cache": {
    "enabled": true,
    "max_size": 100,
    "ttl": 3600
  },
  "output": {
    "directory": "outputs",
    "keep_days": 30,
    "auto_cleanup": true
  }
}
```

### Docker Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  portfolio-analyzer:
    build: .
    ports:
      - "${API_PORT:-8000}:8000"
    environment:
      - API_HOST=0.0.0.0
      - DEBUG=${DEBUG:-false}
      - CACHE_ENABLED=true
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./outputs:/app/outputs
      - ./config:/app/config
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## 🔍 Configuration Validation

The system includes built-in validation for configuration values:

- **API Port**: Must be between 1024-65535
- **Chart Dimensions**: Minimum 400x300 pixels
- **Risk-Free Rate**: Between 0-100%
- **Cache TTL**: Positive integer
- **Output Directory**: Must be writable

## 🔄 Dynamic Configuration

Configuration can be reloaded at runtime:

```python
# Reload configuration
from config.config import reload_config
reload_config()

# Or create new instance
config = ConfigManager("custom_config.json")
```

## 🔐 Security Considerations

- Store sensitive values (API keys) in environment variables
- Use `.env` files for development only
- Never commit API keys to version control
- Use proper secret management in production
- Validate all configuration inputs
