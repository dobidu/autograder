from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    matricula = Column(String(50), nullable=True)
    role = Column(String(20), nullable=False, default="student")  # 'student' | 'professor'
    created_at = Column(DateTime, default=utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    submissions = relationship("Submission", back_populates="student")
    assignments_created = relationship("Assignment", back_populates="created_by_user")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    module = Column(Integer, nullable=True)
    max_score = Column(Float, default=10.0)
    deadline = Column(DateTime, nullable=False)
    allow_late = Column(Boolean, default=False)
    late_penalty = Column(Float, default=0.0)
    max_submissions = Column(Integer, default=-1)
    scoring_mode = Column(String(20), default="last")  # 'last' | 'best'
    expected_files = Column(Text, nullable=True)  # JSON list
    compile_flags = Column(String(255), default="-Wall -Wextra -pthread")
    github_enabled = Column(Boolean, default=False)
    github_branch = Column(String(100), default="main")
    status = Column(String(20), default="draft")  # 'draft' | 'published' | 'closed'
    created_at = Column(DateTime, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    grading_config = Column(Text, nullable=True)  # JSON
    llm_config = Column(Text, nullable=True)  # JSON

    created_by_user = relationship("User", back_populates="assignments_created")
    submissions = relationship("Submission", back_populates="assignment")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime, default=utcnow)
    source = Column(String(20), default="upload")  # 'upload' | 'github'
    github_url = Column(String(500), nullable=True)
    github_commit = Column(String(64), nullable=True)
    file_path = Column(String(500), nullable=True)
    status = Column(String(20), default="pending")
    # 'pending' | 'compiling' | 'testing' | 'grading' | 'done' | 'error'
    version = Column(Integer, default=1)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", back_populates="submissions")
    grade_result = relationship("GradeResult", back_populates="submission", uselist=False)


class GradeResult(Base):
    __tablename__ = "grade_results"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, unique=True)
    compile_ok = Column(Boolean, nullable=True)
    compile_output = Column(Text, nullable=True)
    test_results = Column(Text, nullable=True)  # JSON
    stress_results = Column(Text, nullable=True)  # JSON
    helgrind_ok = Column(Boolean, nullable=True)
    helgrind_output = Column(Text, nullable=True)
    score_auto = Column(Float, nullable=True)
    score_llm = Column(Float, nullable=True)
    llm_feedback = Column(Text, nullable=True)
    score_final = Column(Float, nullable=True)
    professor_notes = Column(Text, nullable=True)
    is_published = Column(Boolean, default=False)
    graded_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    submission = relationship("Submission", back_populates="grade_result")
