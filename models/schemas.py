from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date
import uuid

# Enum para género (debe coincidir con el de la BD)
from enum import Enum

class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"

# Base schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)

class UserResponse(UserBase):
    user_id: uuid.UUID
    first_name: str
    last_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================
# Schemas para Perfil de Usuario Completo
# ============================================================

class UserProfileResponse(BaseModel):
    """Schema completo para respuesta de perfil de usuario"""
    user_id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    birth_date: Optional[date] = None
    gender: Optional[GenderEnum] = None
    mobile: Optional[str] = None
    country: Optional[str] = None
    identification_number: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None  # URL firmada de Supabase Storage
    tax_id_number: Optional[str] = None  # Número de identificación fiscal
    tax_id_country: Optional[str] = None  # País de identificación fiscal
    residential_address: Optional[str] = None  # Dirección residencial
    created_at: datetime
    has_completed_onboarding: bool = False
    
    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    """Schema para actualizar perfil de usuario"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    birth_date: Optional[date] = None
    gender: Optional[GenderEnum] = None
    mobile: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    identification_number: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=1000)
    tax_id_number: Optional[str] = Field(None, max_length=50)
    tax_id_country: Optional[str] = Field(None, max_length=100)
    residential_address: Optional[str] = Field(None, max_length=500)

class UserAvatarResponse(BaseModel):
    """Schema para respuesta de avatar/imagen de perfil"""
    avatar_url: str
    is_default: bool = False  # True si es avatar por defecto
    gender: Optional[GenderEnum] = None

class UserProfileImageUpload(BaseModel):
    """Schema para subir imagen de perfil"""
    # El archivo se maneja por separado con UploadFile
    pass

# ============================================================
# Authentication schemas
# ============================================================

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None

# API Response schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# ============================================================
# Schemas para cambio de contraseña
# ============================================================

class PasswordChange(BaseModel):
    """Schema para cambiar contraseña"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

class PasswordChangeResponse(BaseModel):
    """Schema de respuesta para cambio de contraseña"""
    success: bool
    message: str
