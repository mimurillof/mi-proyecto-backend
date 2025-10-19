from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date
import uuid

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

# Authentication schemas
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
