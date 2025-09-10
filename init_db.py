"""
Database initialization script
Run this to create all tables in the database
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from db_models.models import Base
from config import settings

async def init_db():
    """Initialize database tables"""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
