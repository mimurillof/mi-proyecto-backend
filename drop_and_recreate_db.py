"""
Drop all tables and recreate them
Use with caution - this will delete all data!
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from db_models.models import Base
from config import settings

async def drop_and_recreate_db():
    """Drop all tables and recreate them"""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # Drop all tables
        print("⚠️  Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("✅ Tables dropped!")
        
        # Create all tables
        print("\n📦 Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(drop_and_recreate_db())
