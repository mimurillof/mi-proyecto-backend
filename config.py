import os

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
    CLIENT_ORIGIN: str = "https://mi-proyecto-topaz-omega.vercel.app"
    CORS_ORIGINS: str = "https://mi-proyecto-topaz-omega.vercel.app,https://horizon-next-app.vercel.app,https://chat-agent-horizon-cc5e16d4b37e.herokuapp.com"
    
    def get_cors_origins(self) -> list:
        """Obtener lista de orígenes CORS"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS
    
    # Application Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Mi Proyecto API"
    
    # Environment
    ENVIRONMENT: str = "production"
    
    # AI Settings
    GOOGLE_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    
    # Chat Agent Service Settings (Heroku)
    CHAT_AGENT_SERVICE_URL_PROD: str = "https://chat-agent-horizon-cc5e16d4b37e.herokuapp.com"
    CHAT_AGENT_TIMEOUT: int = 30
    CHAT_AGENT_RETRIES: int = 3
    
    def get_chat_agent_url(self) -> str:
        """Obtener la URL del servicio de chat"""
        return self.CHAT_AGENT_SERVICE_URL_PROD
    
    # Supabase Settings
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE: Optional[str] = None
    
    # Storage: bucket único, archivos en {user_id}/
    SUPABASE_BUCKET_NAME: str = "portfolio-files"
    
    # Prefijos legacy (pueden ser None - ya no se usan, archivos van en {user_id}/)
    SUPABASE_BASE_PREFIX: Optional[str] = None
    SUPABASE_BASE_PREFIX_2: Optional[str] = None
    
    SUPABASE_CLEANUP_AFTER_TESTS: bool = False
    ENABLE_SUPABASE_UPLOAD: bool = True

    # PDF Generation Service
    PDF_SERVICE_URL: Optional[str] = None
    INTERNAL_API_KEY: Optional[str] = None

    # Heroku Settings
    HEROKU_API_KEY: Optional[str] = None

    # Portfolio Manager Service
    PORTFOLIO_MANAGER_ENABLED: bool = True
    PORTFOLIO_MANAGER_REFRESH_MINUTES: int = 15
    PORTFOLIO_MANAGER_DEFAULT_PERIOD: str = "6mo"
    PORTFOLIO_DATA_PATH: str = "data/portfolio_data.json"

    class Config:
        env_file = ".env"

settings = Settings()

# ===================================================================
# CORRECCIÓN PARA DATABASE_URL
# ===================================================================
if settings.DATABASE_URL and settings.DATABASE_URL.startswith("postgresql://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )