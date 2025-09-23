# models.py

import enum
from sqlalchemy import (create_engine, Column, Integer, String, Text,
                        ForeignKey, Boolean, DateTime, Enum as EnumType)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

from config import DATABASE_URL

Base = declarative_base()

# --- Enums for Data Integrity ---
class ExperienceStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# --- Table Models ---
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True) # Indexed for faster lookups
    first_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True) # Indexed for faster lookups
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BotText(Base):
    __tablename__ = 'bot_texts'
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Field(Base):
    __tablename__ = 'fields'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    majors = relationship("Major", back_populates="field", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Major(Base):
    __tablename__ = 'majors'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    field_id = Column(Integer, ForeignKey('fields.id'), nullable=False)
    field = relationship("Field", back_populates="majors")
    courses = relationship("Course", back_populates="major", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Professor(Base):
    __tablename__ = 'professors'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    major_id = Column(Integer, ForeignKey('majors.id'), nullable=False)
    major = relationship("Major", back_populates="courses")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Experience(Base):
    __tablename__ = 'experiences'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True) # Indexed for faster lookups
    field_id = Column(Integer, ForeignKey('fields.id'))
    major_id = Column(Integer, ForeignKey('majors.id'))
    professor_id = Column(Integer, ForeignKey('professors.id'))
    course_id = Column(Integer, ForeignKey('courses.id'))
    teaching_style = Column(Text)
    notes = Column(Text)
    project = Column(Text)
    attendance_required = Column(Boolean)
    attendance_details = Column(Text)
    exam = Column(Text)
    conclusion = Column(Text)
    status = Column(EnumType(ExperienceStatus), default=ExperienceStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships for easy access to related objects
    field = relationship("Field")
    major = relationship("Major")
    professor = relationship("Professor")
    course = relationship("Course")

class RequiredChannel(Base):
    __tablename__ = 'required_channels'
    id = Column(Integer, primary_key=True)
    channel_id = Column(String(255), unique=True, nullable=False)
    channel_link = Column(String(255), nullable=False)

class Setting(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(String(255), nullable=False)

# --- Database Engine Setup ---
engine = create_engine(DATABASE_URL, echo=False, connect_args={'charset': 'utf8mb4'})

def create_tables():
    """Creates all tables in the database based on the models."""
    Base.metadata.create_all(engine)