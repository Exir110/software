from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

TaskStatus = Literal["待开始", "进行中", "已完成"]
Priority = Literal["高", "中", "低"]


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$")
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(default="考研同学", min_length=1, max_length=64)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class GoalIn(BaseModel):
    exam_date: date
    target_school: str = Field(default="", max_length=128)
    target_major: str = Field(default="", max_length=128)
    target_score: int = Field(default=380, ge=100, le=500)
    daily_minutes: int = Field(default=180, ge=30, le=720)


class GoalOut(GoalIn):
    days_remaining: int


class SubjectOut(BaseModel):
    id: int
    name: str
    code: str


class KnowledgeOut(BaseModel):
    id: int
    name: str
    subject_id: int
    subject: str
    chapter: str
    mastery: float
    trend: Literal["up", "down", "steady"]
    questions: int
    importance: int
    last_practiced_at: datetime | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    subject_id: int
    subject: str
    knowledge_point_id: int | None = None
    knowledge_point: str | None = None
    category: str
    scheduled_date: date
    start_time: str
    duration_minutes: int
    status: str
    priority: str
    mastery: float | None = None
    note: str = ""


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    subject_id: int
    knowledge_point_id: int | None = None
    scheduled_date: date | None = None
    start_time: str = "09:00"
    duration_minutes: int = Field(default=45, ge=5, le=480)
    priority: Priority = "中"
    note: str = Field(default="", max_length=1000)

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: str) -> str:
        hours, sep, minutes = value.partition(":")
        if sep != ":" or not hours.isdigit() or not minutes.isdigit():
            raise ValueError("start_time must use HH:MM")
        if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
            raise ValueError("start_time is out of range")
        return f"{int(hours):02d}:{int(minutes):02d}"


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    status: TaskStatus | None = None
    priority: Priority | None = None
    note: str | None = Field(default=None, max_length=1000)
    start_time: str | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    scheduled_date: date | None = None

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return TaskCreate.validate_start_time(value)


class TaskCompleteRequest(BaseModel):
    minutes: int | None = Field(default=None, ge=1, le=720)
    correct_count: int | None = Field(default=None, ge=0)
    total_count: int | None = Field(default=None, ge=0)
    self_rating: int = Field(default=3, ge=1, le=5)
    note: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_counts(self):
        if self.correct_count is not None and self.total_count is not None:
            if self.correct_count > self.total_count:
                raise ValueError("correct_count cannot exceed total_count")
        return self


class PracticeRequest(BaseModel):
    minutes: int = Field(default=20, ge=1, le=720)
    correct_count: int = Field(ge=0)
    total_count: int = Field(ge=1)
    self_rating: int = Field(default=3, ge=1, le=5)
    note: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_counts(self):
        if self.correct_count > self.total_count:
            raise ValueError("correct_count cannot exceed total_count")
        return self


class KnowledgeUpdateResult(BaseModel):
    knowledge: KnowledgeOut
    delta: float
    message: str


class TaskCompleteOut(BaseModel):
    task: TaskOut
    record_id: int
    knowledge: KnowledgeOut | None = None
    delta: float = 0.0
    message: str


class WrongQuestionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    subject_id: int
    knowledge_point_id: int | None = None
    source: str = Field(default="", max_length=64)
    error_type: str = Field(default="", max_length=64)
    analysis: str = Field(default="", max_length=2000)


class WrongQuestionOut(BaseModel):
    id: int
    title: str
    subject: str
    knowledge_point: str | None = None
    source: str
    error_type: str
    analysis: str
    status: str
    review_count: int
    next_review_at: datetime | None = None
    created_at: datetime


class WrongQuestionUpdate(BaseModel):
    status: Literal["待复习", "已掌握"] | None = None
    error_type: str | None = Field(default=None, max_length=64)
    analysis: str | None = Field(default=None, max_length=2000)


class WeeklyPoint(BaseModel):
    date: date
    day: str
    minutes: int


class DashboardOut(BaseModel):
    days_to_exam: int
    study_goal_minutes: int
    today_minutes: int
    today_completed: int
    today_total: int
    completion_rate: int
    average_mastery: int
    streak_days: int
    tasks: list[TaskOut]
    weak_points: list[KnowledgeOut]
    weekly: list[WeeklyPoint]


class PlanRecommendation(BaseModel):
    task_id: int
    title: str
    priority: str
    score: float
    reason: str
    start_time: str


class PlanResponse(BaseModel):
    message: str
    generated_at: datetime
    provider: str
    applied: bool
    recommendations: list[PlanRecommendation]


class WrongAnalysisOut(BaseModel):
    question_id: int
    analysis: str
    suggestions: list[str]
    provider: str


class SummaryOut(BaseModel):
    summary: str
    provider: str
    generated_at: datetime
