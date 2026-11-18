from ..core.clock import now_local
from ..models import KnowledgePoint, StudyRecord, StudyTask, UserKnowledge, WrongQuestion
from ..services.mastery import trend_from_delta


def knowledge_dict(point: KnowledgePoint, state: UserKnowledge | None) -> dict:
    mastery = round(state.mastery, 1) if state else 0.0
    trend = trend_from_delta(state.mastery - state.previous_mastery, state.last_practiced_at) if state else "steady"
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
    due = bool(question.next_review_at and question.next_review_at <= now_local())
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
        "due": due,
        "created_at": question.created_at,
    }


def record_dict(record: StudyRecord) -> dict:
    task = record.task
    point = record.knowledge_point
    subject = None
    if task is not None and task.subject is not None:
        subject = task.subject.name
    elif point is not None and point.subject is not None:
        subject = point.subject.name
    return {
        "id": record.id,
        "task_id": record.task_id,
        "task_title": task.title if task else None,
        "knowledge_point": point.name if point else None,
        "subject": subject,
        "minutes": record.minutes,
        "correct_count": record.correct_count,
        "total_count": record.total_count,
        "self_rating": record.self_rating,
        "mastery_delta": record.mastery_delta,
        "note": record.note,
        "created_at": record.created_at,
    }
