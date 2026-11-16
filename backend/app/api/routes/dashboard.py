from collections import defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from ...db.session import get_db
from ...models import ExamGoal, KnowledgePoint, StudyRecord, StudyTask, User
from ...schemas.domain import DashboardOut, KnowledgeOut, TaskOut, WeeklyPoint
from ...services.scheduling import days_remaining
from ...services.tracking import state_map
from ..deps import get_current_user
from ..serializers import knowledge_dict, task_dict

router = APIRouter(prefix="/dashboard", tags=["学习总览"])


def _streak_days(db: Session, user_id: int, today: date) -> int:
    start = datetime.combine(today - timedelta(days=90), time.min)
    timestamps = db.scalars(
        select(StudyRecord.created_at).where(
            StudyRecord.user_id == user_id, StudyRecord.created_at >= start
        )
    ).all()
    studied = {item.date() for item in timestamps}
    cursor = today if today in studied else today - timedelta(days=1)
    streak = 0
    while cursor in studied:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@router.get("", response_model=DashboardOut)
def dashboard(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DashboardOut:
    today = date.today()
    goal = db.query(ExamGoal).filter(ExamGoal.user_id == user.id).first()
    tasks = db.scalars(
        select(StudyTask)
        .options(selectinload(StudyTask.subject), selectinload(StudyTask.knowledge_point))
        .where(StudyTask.user_id == user.id, StudyTask.scheduled_date == today)
        .order_by(StudyTask.start_time, StudyTask.id)
    ).all()
    states = state_map(db, user.id)

    day_start = datetime.combine(today, time.min)
    day_end = day_start + timedelta(days=1)
    today_records = db.scalars(
        select(StudyRecord).where(
            StudyRecord.user_id == user.id,
            StudyRecord.created_at >= day_start,
            StudyRecord.created_at < day_end,
        )
    ).all()
    today_minutes = sum(record.minutes for record in today_records)

    week_start = day_start - timedelta(days=6)
    week_records = db.scalars(
        select(StudyRecord).where(
            StudyRecord.user_id == user.id,
            StudyRecord.created_at >= week_start,
            StudyRecord.created_at < day_end,
        )
    ).all()
    minutes_by_day: dict[date, int] = defaultdict(int)
    for record in week_records:
        minutes_by_day[record.created_at.date()] += record.minutes
    weekday_names = "一二三四五六日"
    weekly = [
        WeeklyPoint(
            date=today - timedelta(days=offset),
            day=weekday_names[(today - timedelta(days=offset)).weekday()],
            minutes=minutes_by_day[today - timedelta(days=offset)],
        )
        for offset in range(6, -1, -1)
    ]

    points = db.scalars(
        select(KnowledgePoint)
        .options(joinedload(KnowledgePoint.subject))
        .order_by(KnowledgePoint.id)
    ).all()
    knowledge_items = [knowledge_dict(point, states.get(point.id)) for point in points]
    knowledge_items.sort(key=lambda item: item["mastery"])
    weak_points = [KnowledgeOut(**item) for item in knowledge_items[:3]]
    average_mastery = (
        round(sum(item["mastery"] for item in knowledge_items) / len(knowledge_items))
        if knowledge_items
        else 0
    )

    completed = sum(1 for task in tasks if task.status == "已完成")
    return DashboardOut(
        days_to_exam=days_remaining(goal),
        study_goal_minutes=goal.daily_minutes if goal else 180,
        today_minutes=today_minutes,
        today_completed=completed,
        today_total=len(tasks),
        completion_rate=round(completed / len(tasks) * 100) if tasks else 0,
        average_mastery=average_mastery,
        streak_days=_streak_days(db, user.id, today),
        tasks=[TaskOut(**task_dict(task, states.get(task.knowledge_point_id or -1))) for task in tasks],
        weak_points=weak_points,
        weekly=weekly,
    )
