from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import (
    ExamGoal,
    StudyRecord,
    StudyTask,
    User,
    UserKnowledge,
    WeeklyGoal,
    WrongQuestion,
)
from ...schemas.domain import (
    PlanOut,
    PlanPhaseOut,
    PlanWeekOut,
    WeeklyGoalCreate,
    WeeklyGoalOut,
    WeeklyGoalUpdate,
)
from ..deps import get_current_user

router = APIRouter(prefix="/plan", tags=["备考计划"])

PHASE_OFFSETS: tuple[tuple[str, int, int], ...] = (
    ("基础阶段", 170, 110),
    ("强化阶段", 109, 49),
    ("冲刺阶段", 48, 19),
    ("模考阶段", 18, 1),
)


def week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def build_phases(exam_date: date | None, today: date) -> list[PlanPhaseOut]:
    if exam_date is None:
        return []
    phases: list[PlanPhaseOut] = []
    for index, (name, from_days, to_days) in enumerate(PHASE_OFFSETS, start=1):
        start = exam_date - timedelta(days=from_days)
        end = exam_date - timedelta(days=to_days)
        if today > end:
            state = "done"
        elif start <= today <= end:
            state = "current"
        else:
            state = "upcoming"
        phases.append(
            PlanPhaseOut(index=index, name=name, start=start, end=end, status=state)
        )
    return phases


def _goal_out(goal: WeeklyGoal) -> WeeklyGoalOut:
    return WeeklyGoalOut(
        id=goal.id,
        title=goal.title,
        target_minutes=goal.target_minutes,
        status=goal.status,
        week_start=goal.week_start,
    )


def _week_tasks(db: Session, user_id: int, start: date, end: date) -> list[StudyTask]:
    return list(
        db.scalars(
            select(StudyTask).where(
                StudyTask.user_id == user_id,
                StudyTask.scheduled_date >= start,
                StudyTask.scheduled_date <= end,
            )
        ).all()
    )


def _ensure_goals(
    db: Session, user_id: int, week_start: date, week_tasks: list[StudyTask]
) -> list[WeeklyGoal]:
    goals = list(
        db.scalars(
            select(WeeklyGoal)
            .where(WeeklyGoal.user_id == user_id, WeeklyGoal.week_start == week_start)
            .order_by(WeeklyGoal.id)
        ).all()
    )
    if goals:
        return goals

    states = list(
        db.scalars(select(UserKnowledge).where(UserKnowledge.user_id == user_id)).all()
    )
    weak = sorted(states, key=lambda item: item.mastery)[:2]
    templates: list[tuple[str, int]] = []
    for state in weak:
        if state.knowledge_point is not None:
            templates.append((f"完成「{state.knowledge_point.name}」专项练习", 120))
    while len(templates) < 2:
        templates.append(("完成一次整卷模拟", 120))

    wrong_count = (
        db.scalar(
            select(func.count())
            .select_from(WrongQuestion)
            .where(WrongQuestion.user_id == user_id, WrongQuestion.status == "待复习")
        )
        or 0
    )
    templates.append(
        (f"复盘 {wrong_count} 道待复习错题" if wrong_count else "整理本周错题", 60)
    )
    pending_minutes = sum(
        task.duration_minutes for task in week_tasks if task.status != "已完成"
    )
    templates.append(("完成本周计划任务", max(60, pending_minutes)))

    seen: set[str] = set()
    created: list[WeeklyGoal] = []
    for title, minutes in templates:
        if title in seen:
            continue
        seen.add(title)
        goal = WeeklyGoal(
            user_id=user_id,
            week_start=week_start,
            title=title,
            target_minutes=minutes,
            status="待开始",
        )
        db.add(goal)
        created.append(goal)
    db.commit()
    for goal in created:
        db.refresh(goal)
    return created


def _build_week(
    db: Session, user_id: int, today: date
) -> tuple[PlanWeekOut, str]:
    start, end = week_bounds(today)
    tasks = _week_tasks(db, user_id, start, end)
    completed = sum(1 for task in tasks if task.status == "已完成")
    total = len(tasks)
    rate = round(completed / total * 100) if total else 0

    record_minutes = (
        db.scalar(
            select(func.coalesce(func.sum(StudyRecord.minutes), 0)).where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= datetime.combine(start, time.min),
                StudyRecord.created_at < datetime.combine(end + timedelta(days=1), time.min),
            )
        )
        or 0
    )

    week_ago = today - timedelta(days=6)
    recent = list(
        db.scalars(
            select(StudyTask).where(
                StudyTask.user_id == user_id,
                StudyTask.status == "已完成",
                StudyTask.completed_at >= datetime.combine(week_ago, time.min),
            )
        ).all()
    )
    active_days = len({task.completed_at.date() for task in recent if task.completed_at})
    avg_daily = round(len(recent) / max(active_days, 1), 1)

    prev_start = start - timedelta(days=7)
    prev_end = start - timedelta(days=1)
    prev_tasks = _week_tasks(db, user_id, prev_start, prev_end)
    prev_done = sum(1 for task in prev_tasks if task.status == "已完成")
    delta = round((completed - prev_done) / prev_done * 100) if prev_done else None

    goals = _ensure_goals(db, user_id, start, tasks)
    week = PlanWeekOut(
        start=start,
        end=end,
        total_tasks=total,
        completed_tasks=completed,
        completion_rate=rate,
        minutes=int(record_minutes),
        avg_daily_tasks=avg_daily,
        delta_week=delta,
        goals=[_goal_out(goal) for goal in goals],
    )

    if total == 0:
        insight = "本周还没有安排计划任务，可以先在「今日任务」里添加。"
    else:
        parts = [f"近 7 天在 {max(active_days, 1)} 个学习日里完成了 {len(recent)} 个任务。"]
        parts.append(f"本周已完成 {completed}/{total} 个，完成率 {rate}%。")
        if delta is not None:
            parts.append(f"完成数较上周 {delta:+d}%。")
        remaining = total - completed
        if remaining:
            parts.append(f"还有 {remaining} 个任务待完成。")
        insight = "".join(parts)
    return week, insight


@router.get("", response_model=PlanOut)
def get_plan(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PlanOut:
    today = date.today()
    goal = db.query(ExamGoal).filter(ExamGoal.user_id == user.id).first()
    week, insight = _build_week(db, user.id, today)
    return PlanOut(
        exam_date=goal.exam_date if goal else None,
        days_remaining=max((goal.exam_date - today).days, 0) if goal else 0,
        phases=build_phases(goal.exam_date if goal else None, today),
        week=week,
        insight=insight,
    )


@router.post("/goals", response_model=WeeklyGoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: WeeklyGoalCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyGoalOut:
    start, _ = week_bounds(date.today())
    goal = WeeklyGoal(
        user_id=user.id,
        week_start=start,
        title=payload.title,
        target_minutes=payload.target_minutes,
        status="待开始",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _goal_out(goal)


def _get_goal(db: Session, user_id: int, goal_id: int) -> WeeklyGoal:
    goal = db.scalar(
        select(WeeklyGoal).where(WeeklyGoal.id == goal_id, WeeklyGoal.user_id == user_id)
    )
    if goal is None:
        raise HTTPException(status_code=404, detail="周目标不存在")
    return goal


@router.patch("/goals/{goal_id}", response_model=WeeklyGoalOut)
def update_goal(
    goal_id: int,
    payload: WeeklyGoalUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyGoalOut:
    goal = _get_goal(db, user.id, goal_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return _goal_out(goal)


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    goal = _get_goal(db, user.id, goal_id)
    db.delete(goal)
    db.commit()
