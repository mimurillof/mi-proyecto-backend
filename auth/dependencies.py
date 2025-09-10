from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from crud.user_service import user_crud
from auth.security import verify_token, create_credentials_exception
from db_models.models import User

# OAuth2 scheme
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    email = verify_token(token)
    
    if email is None:
        raise create_credentials_exception()
    
    user = await user_crud.get_user_by_email(db, email=email)
    if user is None:
        raise create_credentials_exception()
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (placeholder for future is_active field)"""
    # For now, all users are considered active
    # In the future, you might want to check user.is_active
    return current_user 