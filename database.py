from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings

# Create async engine with proper URL handling
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL and not DATABASE_URL.startswith("postgresql+asyncpg"):
    if DATABASE_URL.startswith("postgresql"):
        DATABASE_URL = DATABASE_URL.replace("postgresql", "postgresql+asyncpg", 1)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
    pool_size=20,  # Aumentar el tamaño del pool de conexiones
    max_overflow=10,  # Permitir hasta 10 conexiones adicionales temporales
    pool_timeout=30,  # Tiempo de espera para obtener una conexión
    pool_recycle=3600,  # Reciclar conexiones cada hora
    pool_pre_ping=True,  # Verificar conexiones antes de usarlas
    connect_args={
        "statement_cache_size": 0,  # CRÍTICO: Deshabilitar prepared statements para compatibilidad con Supabase Transaction Pooler
        "server_settings": {
            "jit": "off"  # Optimización adicional para poolers
        }
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create base class for models
Base = declarative_base()

# Dependency to get database session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 