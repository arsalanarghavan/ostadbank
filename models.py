# models.py

import enum
from sqlalchemy import (create_engine, Column, Integer, String, Text,
                        ForeignKey, Boolean, DateTime, Enum as EnumType, BigInteger)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from dataclasses import dataclass
from typing import Optional

from config import DATABASE_URL

Base = declarative_base()

@dataclass
class ExperienceData:
    """A dataclass to hold experience data independent of the session."""
    id: int
    user_id: int
    teaching_style: str
    notes: str
    project: str
    attendance_required: bool
    attendance_details: str
    exam: str
    conclusion: str
    status: str
    field_name: str
    major_name: str
    professor_name: str
    course_name: str
    channel_message_id: Optional[int] = None
    teaching_rating: Optional[str] = None
    exam_difficulty: Optional[str] = None
    overall_rating: Optional[int] = None
    # --- NEW FIELDS START ---
    has_notes: Optional[bool] = None
    has_project: Optional[bool] = None
    has_exam: Optional[bool] = None
    # --- NEW FIELDS END ---


class ExperienceStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TeachingRating(str, enum.Enum):
    EXCELLENT = "عالی"
    GOOD = "خوب"
    AVERAGE = "متوسط"
    POOR = "ضعیف"

class ExamDifficulty(str, enum.Enum):
    EASY = "آسان"
    MEDIUM = "متوسط"
    HARD = "سخت"


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    first_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
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
    user_id = Column(BigInteger, nullable=False, index=True)
    field_id = Column(Integer, ForeignKey('fields.id'))
    major_id = Column(Integer, ForeignKey('majors.id'))
    professor_id = Column(Integer, ForeignKey('professors.id'))
    course_id = Column(Integer, ForeignKey('courses.id'))
    teaching_style = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    project = Column(Text, nullable=True)
    attendance_required = Column(Boolean)
    attendance_details = Column(Text, nullable=True)
    exam = Column(Text, nullable=True)
    conclusion = Column(Text)
    status = Column(EnumType(ExperienceStatus), default=ExperienceStatus.PENDING, nullable=False)
    admin_message_id = Column(BigInteger, nullable=True)
    admin_chat_id = Column(BigInteger, nullable=True)
    channel_message_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    teaching_rating = Column(EnumType(TeachingRating), nullable=True)
    exam_difficulty = Column(EnumType(ExamDifficulty), nullable=True)
    overall_rating = Column(Integer, nullable=True) # From 1 to 5

    # --- NEW BOOLEAN COLUMNS ---
    has_notes = Column(Boolean, nullable=True)
    has_project = Column(Boolean, nullable=True)
    has_exam = Column(Boolean, nullable=True)
    # --- END NEW BOOLEAN COLUMNS ---

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

engine = create_engine(DATABASE_URL, echo=False, connect_args={'charset': 'utf8mb4'})

def create_tables():
    """Creates all tables in the database based on the models."""
    Base.metadata.create_all(engine)