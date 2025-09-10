from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date
from db_models.models import GenderEnum, VerificationStatusEnum, DocumentTypeEnum

# Base schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Profile schemas
class UserProfileBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    mobile_number: Optional[str] = None
    gender: Optional[GenderEnum] = None
    id_number: Optional[str] = None
    tax_id_number: Optional[str] = None
    tax_id_country: Optional[str] = None
    residential_address: Optional[str] = None
    about_me: Optional[str] = None
    birth_date: Optional[date] = None
    id_expedition_date: Optional[date] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    user_id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Notification settings schemas
class NotificationSettingsBase(BaseModel):
    price_limit_notifications: bool = True
    new_report_notifications: bool = False
    important_news_notifications: bool = True
    event_notifications: bool = False
    app_notifications: bool = True
    email_notifications: bool = True
    browser_notifications: bool = False
    google_sync_enabled: bool = True
    linkedin_sync_enabled: bool = False
    facebook_sync_enabled: bool = False

class NotificationSettingsCreate(NotificationSettingsBase):
    pass

class NotificationSettingsUpdate(NotificationSettingsBase):
    pass

class NotificationSettingsResponse(NotificationSettingsBase):
    user_id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Verification schemas
class UserVerificationsBase(BaseModel):
    email_verified: bool = False
    phone_verified: bool = False
    document_type: Optional[DocumentTypeEnum] = None
    document_url: Optional[str] = None
    document_verification_status: VerificationStatusEnum = VerificationStatusEnum.NOT_UPLOADED
    document_rejection_reason: Optional[str] = None
    payment_method_verified: bool = False

class UserVerificationsUpdate(UserVerificationsBase):
    pass

class UserVerificationsResponse(UserVerificationsBase):
    user_id: int
    email_verified_at: Optional[datetime] = None
    phone_verified_at: Optional[datetime] = None
    payment_method_verified_at: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Complete user schema with relations
class UserCompleteResponse(UserResponse):
    profile: Optional[UserProfileResponse] = None
    notification_settings: Optional[NotificationSettingsResponse] = None
    verifications: Optional[UserVerificationsResponse] = None

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# API Response schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
