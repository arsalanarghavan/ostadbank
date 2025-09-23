# models.py

from sqlalchemy import (create_engine, Column, Integer, String, Text,
                        ForeignKey, Boolean)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String)

class Admin(Base):
    __tablename__ = 'admins'
    user_id = Column(Integer, primary_key=True, unique=True)

class BotText(Base):
    __tablename__ = 'bot_texts'
    key = Column(String, primary_key=True, unique=True)
    value = Column(Text, nullable=False)

class Field(Base):
    __tablename__ = 'fields'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    majors = relationship("Major", back_populates="field", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="field", cascade="all, delete-orphan")

class Major(Base):
    __tablename__ = 'majors'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    field_id = Column(Integer, ForeignKey('fields.id'), nullable=False)
    field = relationship("Field", back_populates="majors")

class Professor(Base):
    __tablename__ = 'professors'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    field_id = Column(Integer, ForeignKey('fields.id'), nullable=False)
    field = relationship("Field", back_populates="courses")

class Experience(Base):
    __tablename__ = 'experiences'
    # ... (Columns remain the same as the final previous version)
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
    status = Column(String, default='pending')

    field = relationship("Field")
    major = relationship("Major")
    professor = relationship("Professor")
    course = relationship("Course")


engine = create_engine('sqlite:///bot_db.sqlite')

def create_tables():
    Base.metadata.create_all(engine)