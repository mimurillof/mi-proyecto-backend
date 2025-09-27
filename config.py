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
    CHAT_AGENT_SERVICE_URL: str = "http://localhost:8001"
    CHAT_AGENT_TIMEOUT: int = 30
    CHAT_AGENT_RETRIES: int = 3
    
    # Supabase Settings
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE: Optional[str] = None
    SUPABASE_BUCKET_NAME: Optional[str] = "portfolio-files"
    SUPABASE_BASE_PREFIX: Optional[str] = "Graficos"
    SUPABASE_BASE_PREFIX_2: Optional[str] = None
    ENABLE_SUPABASE_UPLOAD: bool = True
    SUPABASE_CLEANUP_AFTER_TESTS: bool = False

    # PDF Generation Service
    PDF_SERVICE_URL: Optional[str] = None
    INTERNAL_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings() 