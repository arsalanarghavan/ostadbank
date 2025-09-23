# models.py

from sqlalchemy import (create_engine, Column, Integer, String, Text,
                        ForeignKey, Boolean)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime

# وارد کردن رشته اتصال از فایل کانفیگ
from config import DATABASE_URL

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(255))
    # ستون‌های زمانی برای سازگاری با لاراول
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
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
    # بهبود: هر درس به یک گرایش خاص مرتبط می‌شود
    major_id = Column(Integer, ForeignKey('majors.id'), nullable=False)
    major = relationship("Major", back_populates="courses")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Experience(Base):
    __tablename__ = 'experiences'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
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
    status = Column(String(50), default='pending') # طول رشته مشخص شد
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    field = relationship("Field")
    major = relationship("Major")
    professor = relationship("Professor")
    course = relationship("Course")

# استفاده از رشته اتصال MySQL
# encoding="utf8mb4" برای پشتیبانی کامل از کاراکترهای فارسی و اموجی
engine = create_engine(DATABASE_URL, echo=False, connect_args={'charset': 'utf8mb4'})

def create_tables():
    Base.metadata.create_all(engine)