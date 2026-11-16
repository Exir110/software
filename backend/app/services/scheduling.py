from datetime import date, datetime, timedelta

from ..models import ExamGoal, StudyTask, UserKnowledge


def days_remaining(goal: ExamGoal | None) -> int:
    if goal is None:
        return 180
    return max((goal.exam_date - date.today()).days, 0)


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
    if (today - task.scheduled_date).days > 0:
        reasons.append("任务已逾期")
    if goal and days_remaining(goal) <= 45:
        reasons.append(f"距离考试仅剩 {days_remaining(goal)} 天")
    return "，".join(reasons)


def optimize_tasks(
    tasks: list[StudyTask],
    states: dict[int, UserKnowledge],
    goal: ExamGoal | None,
    today: date,
) -> list[dict]:
    """Order pending tasks by explainable urgency and assign start times."""
    pending = [task for task in tasks if task.status != "已完成"]
    scored = [
        (
            task,
            task_score(task, states.get(task.knowledge_point_id or -1), goal, today),
        )
        for task in pending
    ]
    scored.sort(key=lambda item: item[1], reverse=True)

    start = datetime.combine(today, datetime.strptime("09:00", "%H:%M").time())
    recommendations = []
    for task, score in scored:
        priority = priority_for_score(score)
        task.priority = priority
        task.start_time = start.strftime("%H:%M")
        recommendations.append(
            {
                "task_id": task.id,
                "title": task.title,
                "priority": priority,
                "score": score,
                "reason": reason_for_task(
                    task, states.get(task.knowledge_point_id or -1), goal, today
                ),
                "start_time": task.start_time,
            }
        )
        start += timedelta(minutes=task.duration_minutes + 10)
    return recommendations
