from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/dbname"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS Settings
    CLIENT_ORIGIN: str = "http://localhost:5173"
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # Producción - Chat Agent Service
        "https://chat-agent-horizon-cc5e16d4b37e.herokuapp.com"
    ]
    
    # Application Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Mi Proyecto API"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # AI Settings
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    
    # Chat Agent Service Settings (Remote)
    # En desarrollo usa localhost, en producción usa Heroku
    CHAT_AGENT_SERVICE_URL: str = "http://localhost:8001"
    CHAT_AGENT_SERVICE_URL_PROD: str = "https://chat-agent-horizon-cc5e16d4b37e.herokuapp.com"
    CHAT_AGENT_TIMEOUT: int = 30
    CHAT_AGENT_RETRIES: int = 3
    
    def get_chat_agent_url(self) -> str:
        """Obtener la URL del servicio de chat según el entorno"""
        if self.ENVIRONMENT == "production":
            return self.CHAT_AGENT_SERVICE_URL_PROD
        return self.CHAT_AGENT_SERVICE_URL
    
    # Supabase Settings
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE: Optional[str] = None
    SUPABASE_BUCKET_NAME: Optional[str] = "portfolio-files"
    SUPABASE_BASE_PREFIX: Optional[str] = "Graficos"
    SUPABASE_BASE_PREFIX_2: Optional[str] = None
    SUPABASE_PORTFOLIO_DATA_PREFIX: Optional[str] = "Informes"
    SUPABASE_PORTFOLIO_CHARTS_PREFIX: Optional[str] = None
    SUPABASE_PORTFOLIO_ASSETS_PREFIX: Optional[str] = None
    ENABLE_SUPABASE_UPLOAD: bool = True
    SUPABASE_CLEANUP_AFTER_TESTS: bool = False

    # PDF Generation Service
    PDF_SERVICE_URL: Optional[str] = None
    INTERNAL_API_KEY: Optional[str] = None

    # Portfolio Manager Service
    PORTFOLIO_MANAGER_ENABLED: bool = True
    PORTFOLIO_MANAGER_REFRESH_MINUTES: int = 15
    PORTFOLIO_MANAGER_DEFAULT_PERIOD: str = "6mo"
    PORTFOLIO_DATA_PATH: str = "../Portfolio manager/data/portfolio_data.json"
    PORTFOLIO_MANAGER_SERVICE_URL: str = "http://localhost:9000"
    PORTFOLIO_MANAGER_TIMEOUT: int = 30
    PORTFOLIO_MANAGER_DEFAULT_USER_ID: str = "default"
    PORTFOLIO_MANAGER_SIMULATE_MARKET_OPEN: bool = False
    PORTFOLIO_MANAGER_FORCE_UPDATES: bool = False
    PORTFOLIO_MANAGER_TEST_REFRESH_SECONDS: Optional[int] = None

    class Config:
        env_file = ".env"

settings = Settings() 