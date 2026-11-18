from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ...db.session import get_db
from ...models import KnowledgePoint, StudyRecord, Subject, User, UserKnowledge
from ...schemas.domain import (
    KnowledgeCreate,
    KnowledgeOut,
    KnowledgeUpdateResult,
    PracticeRequest,
)
from ...services.goals import sync_weekly_goals
from ...services.mastery import apply_practice
from ...services.tracking import get_or_create_state, state_map
from ..deps import get_current_user
from ..serializers import knowledge_dict

router = APIRouter(prefix="/knowledge", tags=["知识追踪"])


@router.get("", response_model=list[KnowledgeOut])
def list_knowledge(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[KnowledgeOut]:
    points = db.scalars(
        select(KnowledgePoint)
        .options(joinedload(KnowledgePoint.subject))
        .order_by(KnowledgePoint.subject_id, KnowledgePoint.id)
    ).all()
    states = state_map(db, user.id)
    items = [knowledge_dict(point, states.get(point.id)) for point in points]
    items.sort(key=lambda item: item["mastery"])
    return [KnowledgeOut(**item) for item in items]


@router.post("", response_model=KnowledgeOut, status_code=status.HTTP_201_CREATED)
def create_knowledge(
    payload: KnowledgeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeOut:
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=400, detail="科目不存在")
    exists = db.scalar(
        select(KnowledgePoint).where(
            KnowledgePoint.subject_id == payload.subject_id,
            KnowledgePoint.name == payload.name,
        )
    )
    if exists is not None:
        raise HTTPException(status_code=409, detail="该科目下已存在同名知识点")

    point = KnowledgePoint(
        subject_id=payload.subject_id,
        name=payload.name.strip(),
        chapter=payload.chapter.strip(),
        importance=payload.importance,
        difficulty=payload.difficulty,
    )
    db.add(point)
    db.flush()
    for item in db.scalars(select(User)).all():
        db.add(
            UserKnowledge(
                user_id=item.id,
                knowledge_point_id=point.id,
                mastery=50.0,
                previous_mastery=50.0,
            )
        )
    db.commit()
    point = db.scalar(
        select(KnowledgePoint)
        .options(joinedload(KnowledgePoint.subject))
        .where(KnowledgePoint.id == point.id)
    )
    state = db.scalar(
        select(UserKnowledge).where(
            UserKnowledge.user_id == user.id,
            UserKnowledge.knowledge_point_id == point.id,
        )
    )
    return KnowledgeOut(**knowledge_dict(point, state))


@router.post("/{point_id}/practice", response_model=KnowledgeUpdateResult)
def record_practice(
    point_id: int,
    payload: PracticeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeUpdateResult:
    point = db.get(KnowledgePoint, point_id)
    if point is None:
        raise HTTPException(status_code=404, detail="知识点不存在")

    state = get_or_create_state(db, user.id, point.id)
    delta = apply_practice(
        state, payload.correct_count, payload.total_count, payload.self_rating
    )
    db.add(
        StudyRecord(
            user_id=user.id,
            knowledge_point_id=point.id,
            minutes=payload.minutes,
            correct_count=payload.correct_count,
            total_count=payload.total_count,
            self_rating=payload.self_rating,
            mastery_delta=delta,
            note=payload.note,
        )
    )
    db.commit()
    sync_weekly_goals(db, user.id)
    db.refresh(state)
    return KnowledgeUpdateResult(
        knowledge=KnowledgeOut(**knowledge_dict(point, state)),
        delta=delta,
        message=f"练习记录已保存，掌握度变化 {delta:+.1f}%。",
    )
