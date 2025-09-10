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

    class Config:
        env_file = ".env"

settings = Settings() 