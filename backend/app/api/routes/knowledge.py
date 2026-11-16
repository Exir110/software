from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ...db.session import get_db
from ...models import KnowledgePoint, StudyRecord, User
from ...schemas.domain import KnowledgeOut, KnowledgeUpdateResult, PracticeRequest
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
            note=payload.note,
        )
    )
    db.commit()
    db.refresh(state)
    return KnowledgeUpdateResult(
        knowledge=KnowledgeOut(**knowledge_dict(point, state)),
        delta=delta,
        message=f"练习记录已保存，掌握度变化 {delta:+.1f}%。",
    )
