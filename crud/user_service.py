from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from db_models.models import User
from models.schemas import UserCreate, UserProfileUpdate
from auth.security import get_password_hash, verify_password
from typing import Optional, Dict, Any
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
            password_hash=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name
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
    
    async def update_user_profile(
        self, 
        db: AsyncSession, 
        user_id: uuid.UUID, 
        profile_data: UserProfileUpdate
    ) -> Optional[User]:
        """
        Actualiza los datos del perfil de usuario.
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            profile_data: Datos a actualizar
            
        Returns:
            Usuario actualizado o None si no existe
        """
        # Obtener usuario actual
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return None
        
        # Construir diccionario de actualización solo con campos no nulos
        update_data = profile_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            # No hay nada que actualizar
            return user
        
        # Ejecutar actualización
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(**update_data)
        )
        await db.commit()
        
        # Refrescar y retornar usuario actualizado
        await db.refresh(user)
        return user
    
    async def update_profile_image_path(
        self, 
        db: AsyncSession, 
        user_id: uuid.UUID, 
        image_path: Optional[str]
    ) -> Optional[User]:
        """
        Actualiza el path de la imagen de perfil del usuario.
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            image_path: Path de la imagen en Storage (None para eliminar)
            
        Returns:
            Usuario actualizado o None si no existe
        """
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return None
        
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(profile_image_path=image_path)
        )
        await db.commit()
        await db.refresh(user)
        
        return user
    
    async def mark_onboarding_complete(
        self, 
        db: AsyncSession, 
        user_id: uuid.UUID
    ) -> Optional[User]:
        """
        Marca el onboarding del usuario como completado.
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            
        Returns:
            Usuario actualizado o None si no existe
        """
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return None
        
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(has_completed_onboarding=True)
        )
        await db.commit()
        await db.refresh(user)
        
        return user
    
    async def change_password(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Cambia la contraseña del usuario.
        
        Args:
            db: Sesión de base de datos
            user_id: UUID del usuario
            current_password: Contraseña actual
            new_password: Nueva contraseña
            
        Returns:
            Dict con success y message
        """
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return {"success": False, "message": "Usuario no encontrado"}
        
        # Verificar contraseña actual
        if not verify_password(current_password, str(user.password_hash)):
            return {"success": False, "message": "La contraseña actual es incorrecta"}
        
        # Hashear y actualizar nueva contraseña
        new_hash = get_password_hash(new_password)
        
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(password_hash=new_hash)
        )
        await db.commit()
        
        return {"success": True, "message": "Contraseña actualizada correctamente"}

# Create instance
user_crud = UserCRUD()
