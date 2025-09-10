from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db_models.models import User, UserProfile, UserNotificationSettings, UserVerifications
from models.schemas import UserCreate, UserProfileCreate, UserProfileUpdate, NotificationSettingsUpdate, UserVerificationsUpdate
from auth.security import get_password_hash, verify_password
from typing import Optional

class UserCRUD:
    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID with all relationships loaded"""
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.profile),
                selectinload(User.notification_settings),
                selectinload(User.verifications)
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def create_user(self, db: AsyncSession, user: UserCreate) -> User:
        """Create a new user"""
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            password_hash=hashed_password
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        # Create default profile and notification settings
        await self.create_user_profile(db, db_user.id, UserProfileCreate())
        await self.create_notification_settings(db, db_user.id, None)
        await self.create_user_verifications(db, db_user.id)
        
        return await self.get_user_by_id(db, db_user.id)
    
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.get_user_by_email(db, email)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user
    
    async def get_user_profile(self, db: AsyncSession, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user ID"""
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_user_profile(self, db: AsyncSession, user_id: int, profile: UserProfileCreate) -> UserProfile:
        """Create user profile"""
        db_profile = UserProfile(user_id=user_id, **profile.model_dump(exclude_unset=True))
        db.add(db_profile)
        await db.commit()
        await db.refresh(db_profile)
        return db_profile
    
    async def update_user_profile(self, db: AsyncSession, user_id: int, profile: UserProfileUpdate) -> Optional[UserProfile]:
        """Update user profile"""
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        db_profile = result.scalar_one_or_none()
        
        if not db_profile:
            # Create profile if it doesn't exist
            return await self.create_user_profile(db, user_id, UserProfileCreate(**profile.model_dump(exclude_unset=True)))
        
        # Update existing profile
        for field, value in profile.model_dump(exclude_unset=True).items():
            setattr(db_profile, field, value)
        
        await db.commit()
        await db.refresh(db_profile)
        return db_profile
    
    async def get_notification_settings(self, db: AsyncSession, user_id: int) -> Optional[UserNotificationSettings]:
        """Get notification settings by user ID"""
        result = await db.execute(
            select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_notification_settings(self, db: AsyncSession, user_id: int, settings: Optional[NotificationSettingsUpdate]) -> UserNotificationSettings:
        """Create notification settings"""
        settings_data = settings.model_dump(exclude_unset=True) if settings else {}
        db_settings = UserNotificationSettings(user_id=user_id, **settings_data)
        db.add(db_settings)
        await db.commit()
        await db.refresh(db_settings)
        return db_settings
    
    async def update_notification_settings(self, db: AsyncSession, user_id: int, settings: NotificationSettingsUpdate) -> Optional[UserNotificationSettings]:
        """Update notification settings"""
        result = await db.execute(
            select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id)
        )
        db_settings = result.scalar_one_or_none()
        
        if not db_settings:
            return await self.create_notification_settings(db, user_id, settings)
        
        # Update existing settings
        for field, value in settings.model_dump(exclude_unset=True).items():
            setattr(db_settings, field, value)
        
        await db.commit()
        await db.refresh(db_settings)
        return db_settings
    
    async def create_user_verifications(self, db: AsyncSession, user_id: int) -> UserVerifications:
        """Create default user verifications"""
        db_verifications = UserVerifications(user_id=user_id)
        db.add(db_verifications)
        await db.commit()
        await db.refresh(db_verifications)
        return db_verifications
    
    async def update_user_verifications(self, db: AsyncSession, user_id: int, verifications: UserVerificationsUpdate) -> Optional[UserVerifications]:
        """Update user verifications"""
        result = await db.execute(
            select(UserVerifications).where(UserVerifications.user_id == user_id)
        )
        db_verifications = result.scalar_one_or_none()
        
        if not db_verifications:
            return None
        
        # Update existing verifications
        for field, value in verifications.model_dump(exclude_unset=True).items():
            setattr(db_verifications, field, value)
        
        await db.commit()
        await db.refresh(db_verifications)
        return db_verifications

# Create instance
user_crud = UserCRUD()
