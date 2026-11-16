import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...db.session import get_db
from ...models import AIRecommendation, ExamGoal, StudyRecord, StudyTask, User
from ...schemas.domain import PlanResponse, SummaryOut
from ...services.ai import daily_summary, explain_plan, now_iso
from ...services.scheduling import optimize_tasks
from ...services.tracking import state_map
from ..deps import get_current_user

router = APIRouter(prefix="/ai", tags=["AI 学习助手"])


def _today_tasks(db: Session, user_id: int) -> list[StudyTask]:
    return list(
        db.scalars(
            select(StudyTask)
            .options(
                selectinload(StudyTask.subject), selectinload(StudyTask.knowledge_point)
            )
            .where(
                StudyTask.user_id == user_id,
                StudyTask.scheduled_date == date.today(),
            )
            .order_by(StudyTask.start_time, StudyTask.id)
        ).all()
    )


@router.post("/plan", response_model=PlanResponse)
async def plan_day(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PlanResponse:
    today = date.today()
    tasks = _today_tasks(db, user.id)
    states = state_map(db, user.id)
    goal = db.query(ExamGoal).filter(ExamGoal.user_id == user.id).first()
    recommendations = optimize_tasks(tasks, states, goal, today)

    pending = [task for task in tasks if task.status != "已完成"]
    weak_names = [
        point.name
        for point, state in sorted(
            ((state.knowledge_point, state) for state in states.values()),
            key=lambda item: item[1].mastery,
        )[:2]
    ]
    minutes = sum(task.duration_minutes for task in pending)
    message, provider = await explain_plan(weak_names, minutes)
    if not pending:
        message = "今天的任务已经全部完成。建议做一次 15 分钟的错题回顾，然后让大脑休息。"

    db.add(
        AIRecommendation(
            user_id=user.id,
            kind="daily_plan",
            payload=json.dumps(
                {"recommendations": recommendations, "message": message},
                ensure_ascii=False,
            ),
        )
    )
    db.commit()
    return PlanResponse(
        message=message,
        generated_at=now_iso(),
        provider=provider,
        applied=True,
        recommendations=recommendations,
    )


@router.post("/summary", response_model=SummaryOut)
async def summarize_day(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SummaryOut:
    today = date.today()
    tasks = _today_tasks(db, user.id)
    day_start = datetime.combine(today, time.min)
    records = db.scalars(
        select(StudyRecord).where(
            StudyRecord.user_id == user.id,
            StudyRecord.created_at >= day_start,
            StudyRecord.created_at < day_start + timedelta(days=1),
        )
    ).all()
    states = state_map(db, user.id)
    weak_names = [
        state.knowledge_point.name
        for state in sorted(states.values(), key=lambda item: item.mastery)[:2]
    ]
    completed = sum(1 for task in tasks if task.status == "已完成")
    summary, provider = await daily_summary(
        completed, len(tasks), sum(record.minutes for record in records), weak_names
    )
    db.add(
        AIRecommendation(
            user_id=user.id, kind="daily_summary", payload=json.dumps({"summary": summary})
        )
    )
    db.commit()
    return SummaryOut(summary=summary, provider=provider, generated_at=now_iso())
