from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db_models.models import User
from models.schemas import UserCreate
from auth.security import get_password_hash, verify_password
from typing import Optional
import uuid

class UserCRUD:
    async def get_user_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """Get user by user_id (UUID)"""
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def create_user(self, db: AsyncSession, user: UserCreate) -> User:
        """Create a new user with UUID"""
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            password_hash=hashed_password
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        return db_user
    
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.get_user_by_email(db, email)
        if not user or not verify_password(password, str(user.password_hash)):
            return None
        return user

# Create instance
user_crud = UserCRUD()
