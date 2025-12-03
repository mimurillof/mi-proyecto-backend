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
            birth_date, gender, created_at, has_completed_onboarding,
            mobile, country, identification_number, bio, profile_image_path
    """
    __tablename__ = "users"
    
    # Usar user_id (UUID) en lugar de id (BigInteger)
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    # first_name y last_name son requeridos en Supabase
    first_name = Column(String, nullable=False, default="")
    last_name = Column(String, nullable=False, default="")
    birth_date = Column(Date, nullable=True)
    gender = Column(Enum(GenderEnum, name='gender_enum'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    has_completed_onboarding = Column(Boolean, default=False)
    
    # Campos adicionales para perfil completo
    mobile = Column(String(20), nullable=True)  # Número de teléfono móvil
    country = Column(String(100), nullable=True)  # País
    identification_number = Column(String(50), nullable=True)  # Número de identificación (cédula, DNI, etc.)
    bio = Column(Text, nullable=True)  # Acerca de mí / Biografía
    profile_image_path = Column(String(500), nullable=True)  # Path de la imagen en Supabase Storage
    
    # Campos adicionales para configuración de cuenta
    tax_id_number = Column(String(50), nullable=True)  # Número de identificación fiscal
    tax_id_country = Column(String(100), nullable=True)  # País de identificación fiscal
    residential_address = Column(Text, nullable=True)  # Dirección residencial
 