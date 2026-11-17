from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


def now_local() -> datetime:
    return datetime.now()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64), default="考研同学")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_local)

    goal: Mapped["ExamGoal | None"] = relationship(back_populates="user", uselist=False)
    tasks: Mapped[list["StudyTask"]] = relationship(back_populates="user")
    knowledge_states: Mapped[list["UserKnowledge"]] = relationship(back_populates="user")
    records: Mapped[list["StudyRecord"]] = relationship(back_populates="user")
    wrong_questions: Mapped[list["WrongQuestion"]] = relationship(back_populates="user")
    weekly_goals: Mapped[list["WeeklyGoal"]] = relationship(back_populates="user")


class ExamGoal(Base):
    __tablename__ = "exam_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    exam_date: Mapped[date] = mapped_column(Date)
    target_school: Mapped[str] = mapped_column(String(128), default="")
    target_major: Mapped[str] = mapped_column(String(128), default="")
    target_score: Mapped[int] = mapped_column(Integer, default=380)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=180)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_local)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_local, onupdate=now_local
    )

    user: Mapped["User"] = relationship(back_populates="goal")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    code: Mapped[str] = mapped_column(String(16), default="")

    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(back_populates="subject")
    tasks: Mapped[list["StudyTask"]] = relationship(back_populates="subject")


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    __table_args__ = (UniqueConstraint("subject_id", "name", name="uq_kp_subject_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    chapter: Mapped[str] = mapped_column(String(64), default="")
    importance: Mapped[int] = mapped_column(Integer, default=3)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_local)

    subject: Mapped["Subject"] = relationship(back_populates="knowledge_points")
    user_states: Mapped[list["UserKnowledge"]] = relationship(back_populates="knowledge_point")
    tasks: Mapped[list["StudyTask"]] = relationship(back_populates="knowledge_point")


class UserKnowledge(Base):
    __tablename__ = "user_knowledge"
    __table_args__ = (
        UniqueConstraint("user_id", "knowledge_point_id", name="uq_user_kp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    knowledge_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id"), index=True)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    previous_mastery: Mapped[float] = mapped_column(Float, default=0.0)
    practice_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_local, onupdate=now_local
    )

    user: Mapped["User"] = relationship(back_populates="knowledge_states")
    knowledge_point: Mapped["KnowledgePoint"] = relationship(back_populates="user_states")


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_points.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(128))
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[str] = mapped_column(String(5), default="09:00")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45)
    status: Mapped[str] = mapped_column(String(16), default="待开始", index=True)
    priority: Mapped[str] = mapped_column(String(8), default="中")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_local)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="tasks")
    subject: Mapped["Subject"] = relationship(back_populates="tasks")
    knowledge_point: Mapped["KnowledgePoint | None"] = relationship(back_populates="tasks")
    records: Mapped[list["StudyRecord"]] = relationship(back_populates="task")


class StudyRecord(Base):
    __tablename__ = "study_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("study_tasks.id"), nullable=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_points.id"), nullable=True, index=True
    )
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    self_rating: Mapped[int] = mapped_column(Integer, default=3)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_local, index=True)

    user: Mapped["User"] = relationship(back_populates="records")
    task: Mapped["StudyTask | None"] = relationship(back_populates="records")
    knowledge_point: Mapped["KnowledgePoint | None"] = relationship()


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_points.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(64), default="")
    error_type: Mapped[str] = mapped_column(String(64), default="")
    analysis: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="待复习")
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_local)

    user: Mapped["User"] = relationship(back_populates="wrong_questions")
    subject: Mapped["Subject"] = relationship()
    knowledge_point: Mapped["KnowledgePoint | None"] = relationship()


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_local)

    user: Mapped["User"] = relationship()


class WeeklyGoal(Base):
    __tablename__ = "weekly_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(128))
    target_minutes: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(16), default="待开始", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_local)

    user: Mapped["User"] = relationship(back_populates="weekly_goals")
