from ..models import KnowledgePoint, StudyTask, UserKnowledge, WrongQuestion
from ..services.mastery import trend_from_delta


def knowledge_dict(point: KnowledgePoint, state: UserKnowledge | None) -> dict:
    mastery = round(state.mastery, 1) if state else 0.0
    trend = trend_from_delta(state.mastery - state.previous_mastery) if state else "steady"
    return {
        "id": point.id,
        "name": point.name,
        "subject_id": point.subject_id,
        "subject": point.subject.name,
        "chapter": f"{point.chapter} · {point.name}",
        "mastery": mastery,
        "trend": trend,
        "questions": state.practice_count if state else 0,
        "importance": point.importance,
        "last_practiced_at": state.last_practiced_at if state else None,
    }


def task_dict(task: StudyTask, state: UserKnowledge | None) -> dict:
    point = task.knowledge_point
    return {
        "id": task.id,
        "title": task.title,
        "subject_id": task.subject_id,
        "subject": task.subject.name,
        "knowledge_point_id": task.knowledge_point_id,
        "knowledge_point": point.name if point else None,
        "category": f"{point.chapter} · {point.name}" if point else "自定义任务",
        "scheduled_date": task.scheduled_date,
        "start_time": task.start_time,
        "duration_minutes": task.duration_minutes,
        "status": task.status,
        "priority": task.priority,
        "mastery": round(state.mastery, 1) if state else None,
        "note": task.note,
    }


def wrong_dict(question: WrongQuestion) -> dict:
    return {
        "id": question.id,
        "title": question.title,
        "subject": question.subject.name,
        "knowledge_point": question.knowledge_point.name if question.knowledge_point else None,
        "source": question.source,
        "error_type": question.error_type,
        "analysis": question.analysis,
        "status": question.status,
        "review_count": question.review_count,
        "next_review_at": question.next_review_at,
        "created_at": question.created_at,
    }
