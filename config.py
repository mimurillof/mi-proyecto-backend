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
    
    # Supabase Settings
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE: Optional[str] = None
    SUPABASE_BUCKET_NAME: Optional[str] = "portfolio-files"
    SUPABASE_BASE_PREFIX: Optional[str] = "Graficos"
    ENABLE_SUPABASE_UPLOAD: bool = True
    SUPABASE_CLEANUP_AFTER_TESTS: bool = False

    class Config:
        env_file = ".env"

settings = Settings() 