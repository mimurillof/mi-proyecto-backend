from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from crud.user_service import user_crud
from auth.security import verify_token, create_credentials_exception
from db_models.models import User
from typing import Optional
import uuid

# OAuth2 scheme
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    token_data = verify_token(token)
    
    if not token_data or not token_data.get("user_id"):
        raise create_credentials_exception()
    
    try:
        user_id = uuid.UUID(token_data["user_id"])
        user = await user_crud.get_user_by_id(db, user_id=user_id)
    except (ValueError, AttributeError):
        raise create_credentials_exception()
    
    if user is None:
        raise create_credentials_exception()
    
    return user

async def get_current_user_from_query(
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from query parameter (for iframes)"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = verify_token(token)
    
    if not token_data or not token_data.get("user_id"):
        raise create_credentials_exception()
    
    try:
        user_id = uuid.UUID(token_data["user_id"])
        user = await user_crud.get_user_by_id(db, user_id=user_id)
    except (ValueError, AttributeError):
        raise create_credentials_exception()
    
    if user is None:
        raise create_credentials_exception()
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (placeholder for future is_active field)"""
    # For now, all users are considered active
    # In the future, you might want to check user.is_active
    return current_user 