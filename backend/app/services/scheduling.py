from datetime import date, datetime, time, timedelta

from ..core.clock import now_local, today_local
from ..models import ExamGoal, StudyTask, UserKnowledge

DAY_START_MINUTE = 9 * 60
DAY_END_MINUTE = 23 * 60 + 30
BREAK_MINUTES = 10


def days_remaining(goal: ExamGoal | None) -> int:
    if goal is None:
        return 180
    return max((goal.exam_date - today_local()).days, 0)


def task_score(
    task: StudyTask,
    state: UserKnowledge | None,
    goal: ExamGoal | None,
    today: date,
) -> float:
    mastery = state.mastery if state else 50.0
    importance = task.knowledge_point.importance if task.knowledge_point else 3
    remaining = max(days_remaining(goal), 1)
    overdue_days = max((today - task.scheduled_date).days, 0)
    urgency = 1 + min(overdue_days, 14) * 0.12 + max(0, 21 - remaining) * 0.02
    return round(importance * (1 - mastery / 100) * urgency * 10, 2)


def priority_for_score(score: float) -> str:
    if score >= 20:
        return "高"
    if score >= 10:
        return "中"
    return "低"


def reason_for_task(
    task: StudyTask,
    state: UserKnowledge | None,
    goal: ExamGoal | None,
    today: date,
) -> str:
    mastery = state.mastery if state else 50.0
    reasons = [f"掌握度 {mastery:.0f}%"]
    if task.knowledge_point:
        reasons.append(f"知识点重要度 {task.knowledge_point.importance}/5")
    overdue_days = (today - task.scheduled_date).days
    if overdue_days > 0:
        reasons.append(f"已逾期 {overdue_days} 天")
    if goal and days_remaining(goal) <= 45:
        reasons.append(f"距离考试仅剩 {days_remaining(goal)} 天")
    return "，".join(reasons)


def minutes_from_hhmm(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def hhmm_from_minutes(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _overlaps(slot: int, duration: int, blocked: list[tuple[int, int]]) -> bool:
    return any(slot < end and start < slot + duration for start, end in blocked)


def next_free_slot(
    duration: int,
    blocked: list[tuple[int, int]],
    not_before: int,
    end_limit: int = DAY_END_MINUTE,
) -> int | None:
    slot = ((max(not_before, DAY_START_MINUTE) + 4) // 5) * 5
    for _ in range(200):
        if slot + duration > end_limit:
            return None
        conflict = next(
            (
                (start, end)
                for start, end in sorted(blocked)
                if slot < end and start < slot + duration
            ),
            None,
        )
        if conflict is None:
            return slot
        slot = ((conflict[1] + BREAK_MINUTES + 4) // 5) * 5
    return None


def build_plan(
    tasks: list[StudyTask],
    states: dict[int, UserKnowledge],
    goal: ExamGoal | None,
    today: date,
    *,
    now: datetime | None = None,
    daily_limit: int | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Pure planner: returns (scheduled, deferred, warnings) without mutating tasks."""
    pending = [task for task in tasks if task.status != "已完成"]
    if not pending:
        return [], [], []

    scored = sorted(
        (
            (task, task_score(task, states.get(task.knowledge_point_id or -1), goal, today))
            for task in pending
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    # Blocks: completed or in-progress tasks occupy their original slots.
    blocked = [
        (minutes_from_hhmm(task.start_time), minutes_from_hhmm(task.start_time) + task.duration_minutes)
        for task in tasks
        if task.status != "待开始" and task.scheduled_date == today
    ]

    current = now or now_local()
    now_minutes = current.hour * 60 + current.minute
    cursor = max(now_minutes + 5, DAY_START_MINUTE)
    limit = daily_limit if daily_limit and daily_limit > 0 else 180
    scheduled_minutes = 0

    scheduled: list[dict] = []
    deferred: list[dict] = []
    warnings: list[str] = []

    for task, score in scored:
        recommendation = {
            "task_id": task.id,
            "title": task.title,
            "priority": priority_for_score(score),
            "score": score,
            "reason": reason_for_task(task, states.get(task.knowledge_point_id or -1), goal, today),
            "start_time": "",
            "duration_minutes": task.duration_minutes,
        }
        if scheduled_minutes + task.duration_minutes > limit:
            recommendation["reason"] += f"，超出每日计划 {limit} 分钟"
            deferred.append(recommendation)
            continue

        slot = next_free_slot(task.duration_minutes, blocked, cursor)
        if slot is None:
            recommendation["reason"] += "，今天剩余时间不足"
            deferred.append(recommendation)
            continue

        recommendation["start_time"] = hhmm_from_minutes(slot)
        scheduled.append(recommendation)
        blocked.append((slot, slot + task.duration_minutes))
        cursor = slot + task.duration_minutes + BREAK_MINUTES
        scheduled_minutes += task.duration_minutes

    if deferred:
        warnings.append(
            f"有 {len(deferred)} 个任务未排入今天：每日计划上限 {limit} 分钟或剩余时间不足。"
            "可以降低任务时长、调整每日目标，或顺延到明天。"
        )
    if current.hour >= 21:
        warnings.append("当前已较晚，建议只安排轻量复习，避免影响睡眠。")
    return scheduled, deferred, warnings


def apply_plan(tasks: list[StudyTask], recommendations: list[dict], today: date) -> None:
    by_id = {task.id: task for task in tasks}
    for item in recommendations:
        task = by_id.get(item["task_id"])
        if task is None:
            continue
        task.priority = item["priority"]
        task.start_time = item["start_time"]
        if task.scheduled_date < today:
            task.scheduled_date = today
            task.status = "待开始"


def overdue_tasks(tasks: list[StudyTask], today: date) -> list[StudyTask]:
    return [task for task in tasks if task.scheduled_date < today and task.status != "已完成"]


def carry_over_slots(
    overdue: list[StudyTask],
    today_tasks: list[StudyTask],
    today: date,
    now: datetime | None = None,
) -> dict[int, str]:
    """Assign non-conflicting start times for overdue tasks moved to today."""
    blocked = [
        (minutes_from_hhmm(task.start_time), minutes_from_hhmm(task.start_time) + task.duration_minutes)
        for task in today_tasks
    ]
    current = now or now_local()
    cursor = max(current.hour * 60 + current.minute + 5, DAY_START_MINUTE)
    result: dict[int, str] = {}
    for task in overdue:
        slot = next_free_slot(task.duration_minutes, blocked, cursor)
        if slot is None:
            break
        result[task.id] = hhmm_from_minutes(slot)
        blocked.append((slot, slot + task.duration_minutes))
        cursor = slot + task.duration_minutes + BREAK_MINUTES
    return result

