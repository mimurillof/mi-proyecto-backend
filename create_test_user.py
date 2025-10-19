"""
Script para crear usuario de prueba con hash compatible con passlib
"""
import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

# Conexión a Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.tlmdrkthueicqnvbjmie:miguel1016072541@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

# Hash generado con passlib para password "123456"
PASSWORD_HASH = "$2b$12$kVbuQvZcndFiM8aK1mPRnOmezYvOc7ZcqYS.3GhDu0dIOYsGUGWHW"

async def create_test_user():
    """Crea o actualiza el usuario de prueba"""
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with AsyncSession(engine) as session:
        try:
            # Actualizar el password_hash del usuario existente de Miguel
            query = text("""
                UPDATE users 
                SET password_hash = :password_hash
                WHERE email = :email
                RETURNING user_id, email, first_name, last_name;
            """)
            
            result = await session.execute(
                query,
                {
                    "email": "murillofrias.miguel@gmail.com",
                    "password_hash": PASSWORD_HASH
                }
            )
            
            await session.commit()
            
            user = result.fetchone()
            print("\n✅ Usuario actualizado exitosamente!")
            if user:
                print(f"   User ID: {user[0]}")
                print(f"   Email: {user[1]}")
                print(f"   Nombre: {user[2]} {user[3]}")
            print(f"\n🔐 Credenciales actualizadas:")
            print(f"   Email: murillofrias.miguel@gmail.com")
            print(f"   Password: 123456")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            await session.rollback()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_test_user())
