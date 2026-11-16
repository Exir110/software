from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...db.session import get_db
from ...models import KnowledgePoint, StudyRecord, StudyTask, Subject, User, UserKnowledge
from ...schemas.domain import (
    TaskCompleteOut,
    TaskCompleteRequest,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from ...services.mastery import apply_practice, apply_task_completion
from ...services.tracking import get_or_create_state, state_map
from ..deps import get_current_user
from ..serializers import knowledge_dict, task_dict

router = APIRouter(prefix="/tasks", tags=["学习任务"])


def _task_query():
    return select(StudyTask).options(
        selectinload(StudyTask.subject), selectinload(StudyTask.knowledge_point)
    )


def _get_task(db: Session, user_id: int, task_id: int) -> StudyTask:
    task = db.scalar(
        _task_query().where(StudyTask.id == task_id, StudyTask.user_id == user_id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def _validate_reference(db: Session, subject_id: int, knowledge_point_id: int | None) -> None:
    if db.get(Subject, subject_id) is None:
        raise HTTPException(status_code=400, detail="科目不存在")
    if knowledge_point_id is not None:
        point = db.get(KnowledgePoint, knowledge_point_id)
        if point is None:
            raise HTTPException(status_code=400, detail="知识点不存在")
        if point.subject_id != subject_id:
            raise HTTPException(status_code=400, detail="知识点与科目不匹配")


@router.get("", response_model=list[TaskOut])
def list_tasks(
    day: date | None = Query(default=None, alias="date"),
    status_filter: str | None = Query(default=None, alias="status"),
    subject_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    target_day = day or date.today()
    query = _task_query().where(
        StudyTask.user_id == user.id, StudyTask.scheduled_date == target_day
    )
    if status_filter:
        query = query.where(StudyTask.status == status_filter)
    if subject_id is not None:
        query = query.where(StudyTask.subject_id == subject_id)
    tasks = db.scalars(query.order_by(StudyTask.start_time, StudyTask.id)).all()
    states = state_map(db, user.id)
    return [TaskOut(**task_dict(task, states.get(task.knowledge_point_id or -1))) for task in tasks]


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    _validate_reference(db, payload.subject_id, payload.knowledge_point_id)
    task = StudyTask(
        user_id=user.id,
        subject_id=payload.subject_id,
        knowledge_point_id=payload.knowledge_point_id,
        title=payload.title,
        scheduled_date=payload.scheduled_date or date.today(),
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        priority=payload.priority,
        note=payload.note,
    )
    db.add(task)
    db.commit()
    task = _get_task(db, user.id, task.id)
    states = state_map(db, user.id)
    return TaskOut(**task_dict(task, states.get(task.knowledge_point_id or -1)))


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = _get_task(db, user.id, task_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(task, field, value)
    if updates.get("status") == "已完成" and task.completed_at is None:
        task.completed_at = datetime.now()
    if updates.get("status") in {"待开始", "进行中"}:
        task.completed_at = None
    db.commit()
    task = _get_task(db, user.id, task_id)
    states = state_map(db, user.id)
    return TaskOut(**task_dict(task, states.get(task.knowledge_point_id or -1)))


@router.post("/{task_id}/start", response_model=TaskOut)
def start_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = _get_task(db, user.id, task_id)
    if task.status == "已完成":
        raise HTTPException(status_code=409, detail="任务已完成，不能重新开始")
    task.status = "进行中"
    db.commit()
    states = state_map(db, user.id)
    return TaskOut(**task_dict(task, states.get(task.knowledge_point_id or -1)))


@router.post("/{task_id}/complete", response_model=TaskCompleteOut)
def complete_task(
    task_id: int,
    payload: TaskCompleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskCompleteOut:
    task = _get_task(db, user.id, task_id)
    if task.status == "已完成":
        raise HTTPException(status_code=409, detail="该任务已经完成")

    minutes = payload.minutes or task.duration_minutes
    record = StudyRecord(
        user_id=user.id,
        task_id=task.id,
        knowledge_point_id=task.knowledge_point_id,
        minutes=minutes,
        correct_count=payload.correct_count or 0,
        total_count=payload.total_count or 0,
        self_rating=payload.self_rating,
        note=payload.note,
    )
    db.add(record)
    task.status = "已完成"
    task.completed_at = datetime.now()

    state: UserKnowledge | None = None
    delta = 0.0
    if task.knowledge_point_id:
        state = get_or_create_state(db, user.id, task.knowledge_point_id)
        if payload.correct_count is not None and payload.total_count:
            delta = apply_practice(
                state, payload.correct_count, payload.total_count, payload.self_rating
            )
        else:
            delta = apply_task_completion(state, payload.self_rating)

    db.commit()
    task = _get_task(db, user.id, task.id)
    knowledge = (
        knowledge_dict(task.knowledge_point, state)
        if task.knowledge_point is not None and state is not None
        else None
    )
    return TaskCompleteOut(
        task=TaskOut(**task_dict(task, state)),
        record_id=record.id,
        knowledge=knowledge,
        delta=delta,
        message=f"任务已完成，学习记录已保存。掌握度变化 {delta:+.1f}%。",
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    task = _get_task(db, user.id, task_id)
    for record in task.records:
        record.task_id = None
    db.delete(task)
    db.commit()
