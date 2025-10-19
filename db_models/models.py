from sqlalchemy import Column, String, Boolean, Text, Date, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum
import uuid

# Enum types que ya existen en Supabase
class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"

class User(Base):
    """
    Modelo adaptado a la tabla 'users' existente en Supabase.
    Campos: user_id (UUID), email, password_hash, first_name, last_name, 
            birth_date, gender, created_at, has_completed_onboarding
    """
    __tablename__ = "users"
    
    # Usar user_id (UUID) en lugar de id (BigInteger)
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    birth_date = Column(Date)
    gender = Column(Enum(GenderEnum, name='gender_enum'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    has_completed_onboarding = Column(Boolean, default=False)
 