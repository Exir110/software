from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ...core.clock import today_local
from ...db.session import get_db
from ...models import KnowledgePoint, StudyRecord, StudyTask, User, UserKnowledge
from ...schemas.domain import StudyRecordOut
from ...services.goals import sync_weekly_goals
from ...services.mastery import clamp
from ..deps import get_current_user
from ..serializers import record_dict

router = APIRouter(prefix="/records", tags=["学习记录"])


def _record_query():
    return select(StudyRecord).options(
        selectinload(StudyRecord.task).selectinload(StudyTask.subject),
        selectinload(StudyRecord.knowledge_point).selectinload(KnowledgePoint.subject),
    )


@router.get("", response_model=list[StudyRecordOut])
def list_records(
    limit: int = Query(default=50, ge=1, le=200),
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StudyRecordOut]:
    since = datetime.combine(today_local() - timedelta(days=days - 1), time.min)
    records = db.scalars(
        _record_query()
        .where(StudyRecord.user_id == user.id, StudyRecord.created_at >= since)
        .order_by(StudyRecord.created_at.desc())
        .limit(limit)
    ).all()
    return [StudyRecordOut(**record_dict(item)) for item in records]


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    record = db.scalar(
        _record_query().where(StudyRecord.id == record_id, StudyRecord.user_id == user.id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="学习记录不存在")

    if record.knowledge_point_id and record.mastery_delta is not None:
        state = db.scalar(
            select(UserKnowledge).where(
                UserKnowledge.user_id == user.id,
                UserKnowledge.knowledge_point_id == record.knowledge_point_id,
            )
        )
        if state is not None:
            state.mastery = clamp(state.mastery - record.mastery_delta)
            state.previous_mastery = state.mastery
            if record.task_id is None:
                state.practice_count = max(0, state.practice_count - 1)
                state.correct_count = max(0, state.correct_count - record.correct_count)
            latest = db.scalar(
                select(func.max(StudyRecord.created_at)).where(
                    StudyRecord.user_id == user.id,
                    StudyRecord.knowledge_point_id == record.knowledge_point_id,
                    StudyRecord.id != record.id,
                )
            )
            state.last_practiced_at = latest

    if record.task_id:
        task = db.get(StudyTask, record.task_id)
        if task is not None and task.user_id == user.id:
            task.status = "待开始"
            task.completed_at = None

    db.delete(record)
    db.commit()
    sync_weekly_goals(db, user.id)
