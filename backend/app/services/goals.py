import re
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.clock import today_local
from ..models import KnowledgePoint, StudyRecord, StudyTask, WeeklyGoal, WrongQuestion


def week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def _practice_progress(db: Session, user_id: int, goal: WeeklyGoal, start: date) -> tuple[int, str] | None:
    for point in db.scalars(select(KnowledgePoint)).all():
        if f"「{point.name}」" not in goal.title:
            continue
        minutes = (
            db.scalar(
                select(func.coalesce(func.sum(StudyRecord.minutes), 0)).where(
                    StudyRecord.user_id == user_id,
                    StudyRecord.knowledge_point_id == point.id,
                    StudyRecord.created_at >= datetime.combine(start, time.min),
                    StudyRecord.created_at < datetime.combine(start + timedelta(days=7), time.min),
                )
            )
            or 0
        )
        target = max(goal.target_minutes, 1)
        pct = min(100, round(minutes / target * 100))
        return pct, f"{int(minutes)}/{target} 分钟"
    return None


def _task_progress(db: Session, user_id: int, start: date) -> tuple[int, str]:
    tasks = list(
        db.scalars(
            select(StudyTask).where(
                StudyTask.user_id == user_id,
                StudyTask.scheduled_date >= start,
                StudyTask.scheduled_date <= start + timedelta(days=6),
            )
        ).all()
    )
    total = len(tasks)
    done = sum(1 for task in tasks if task.status == "已完成")
    pct = round(done / total * 100) if total else 0
    return pct, f"{done}/{total} 个任务"


def _wrong_progress(db: Session, user_id: int, goal: WeeklyGoal) -> tuple[int, str]:
    match = re.search(r"(\d+)\s*道", goal.title)
    target = int(match.group(1)) if match else 3
    mastered = (
        db.scalar(
            select(func.count())
            .select_from(WrongQuestion)
            .where(WrongQuestion.user_id == user_id, WrongQuestion.status == "已掌握")
        )
        or 0
    )
    pct = min(100, round(mastered / max(target, 1) * 100))
    return pct, f"{mastered}/{target} 道"


def goal_progress(db: Session, user_id: int, goal: WeeklyGoal) -> tuple[int, str, bool]:
    """Returns (percent, progress_text, is_auto)."""
    start = goal.week_start
    practice = _practice_progress(db, user_id, goal, start)
    if practice is not None:
        return practice[0], practice[1], True
    if goal.title.startswith("完成本周计划任务"):
        pct, text = _task_progress(db, user_id, start)
        return pct, text, True
    if "错题" in goal.title:
        pct, text = _wrong_progress(db, user_id, goal)
        return pct, text, True
    return 0, "", False


def sync_weekly_goals(db: Session, user_id: int) -> None:
    start, _ = week_bounds(today_local())
    goals = list(
        db.scalars(
            select(WeeklyGoal)
            .where(WeeklyGoal.user_id == user_id, WeeklyGoal.week_start == start)
            .order_by(WeeklyGoal.id)
        ).all()
    )
    changed = False
    for goal in goals:
        pct, _, is_auto = goal_progress(db, user_id, goal)
        if not is_auto:
            continue
        if pct >= 100 and goal.status != "已完成":
            goal.status = "已完成"
            changed = True
        elif 0 < pct < 100 and goal.status == "待开始":
            goal.status = "进行中"
            changed = True
    if changed:
        db.commit()
