from sqlalchemy import Column, BigInteger, String, Boolean, Text, Date, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum

# Enum types
class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"

class VerificationStatusEnum(str, enum.Enum):
    NOT_UPLOADED = "NOT_UPLOADED"
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class DocumentTypeEnum(str, enum.Enum):
    ID_CARD = "ID_CARD"
    PASSPORT = "PASSPORT"
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    OTHER = "OTHER"

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notification_settings = relationship("UserNotificationSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    verifications = relationship("UserVerifications", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    avatar_url = Column(String(512))
    mobile_number = Column(String(30))
    gender = Column(Enum(GenderEnum))
    id_number = Column(String(50))
    tax_id_number = Column(String(50))
    tax_id_country = Column(String(100))
    residential_address = Column(Text)
    about_me = Column(Text)
    birth_date = Column(Date)
    id_expedition_date = Column(Date)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")

class UserNotificationSettings(Base):
    __tablename__ = "user_notification_settings"
    
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    price_limit_notifications = Column(Boolean, default=True)
    new_report_notifications = Column(Boolean, default=False)
    important_news_notifications = Column(Boolean, default=True)
    event_notifications = Column(Boolean, default=False)
    app_notifications = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    browser_notifications = Column(Boolean, default=False)
    google_sync_enabled = Column(Boolean, default=True)
    linkedin_sync_enabled = Column(Boolean, default=False)
    facebook_sync_enabled = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notification_settings")

class UserVerifications(Base):
    __tablename__ = "user_verifications"
    
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True))
    phone_verified = Column(Boolean, default=False)
    phone_verified_at = Column(DateTime(timezone=True))
    document_type = Column(Enum(DocumentTypeEnum))
    document_url = Column(String(512))
    document_verification_status = Column(Enum(VerificationStatusEnum), default=VerificationStatusEnum.NOT_UPLOADED)
    document_rejection_reason = Column(Text)
    payment_method_verified = Column(Boolean, default=False)
    payment_method_verified_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="verifications") 