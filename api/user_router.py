from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from crud.user_service import user_crud
from models.schemas import (
    UserCompleteResponse, UserProfileResponse, UserProfileUpdate,
    NotificationSettingsResponse, NotificationSettingsUpdate,
    UserVerificationsResponse, UserVerificationsUpdate, APIResponse
)
from auth.dependencies import get_current_user
from db_models.models import User

router = APIRouter()

@router.get("/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user profile by user ID"""
    # Check if user is accessing their own profile or has admin rights
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this profile"
        )
    
    profile = await user_crud.get_user_profile(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return profile

@router.put("/{user_id}/profile", response_model=UserProfileResponse)
async def update_user_profile(
    user_id: int,
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    # Check if user is updating their own profile
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this profile"
        )
    
    updated_profile = await user_crud.update_user_profile(db, user_id, profile_update)
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return updated_profile

@router.get("/{user_id}/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user notification settings"""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access these settings"
        )
    
    settings = await user_crud.get_notification_settings(db, user_id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification settings not found"
        )
    
    return settings

@router.put("/{user_id}/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    user_id: int,
    settings_update: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user notification settings"""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update these settings"
        )
    
    updated_settings = await user_crud.update_notification_settings(db, user_id, settings_update)
    if not updated_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification settings not found"
        )
    
    return updated_settings

@router.get("/{user_id}/verifications", response_model=UserVerificationsResponse)
async def get_user_verifications(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user verification status"""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access verification data"
        )
    
    # Get complete user with verifications
    user = await user_crud.get_user_by_id(db, user_id)
    if not user or not user.verifications:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification data not found"
        )
    
    return user.verifications

@router.get("/{user_id}", response_model=UserCompleteResponse)
async def get_complete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get complete user data with all relationships"""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user data"
        )
    
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user 