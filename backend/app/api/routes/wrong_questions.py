from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...core.clock import now_local
from ...db.session import get_db
from ...models import KnowledgePoint, Subject, User, UserKnowledge, WrongQuestion
from ...schemas.domain import (
    WrongAnalysisOut,
    WrongQuestionCreate,
    WrongQuestionOut,
    WrongQuestionUpdate,
)
from ...services.ai import analyze_wrong_question
from ...services.goals import sync_weekly_goals
from ..deps import get_current_user
from ..serializers import wrong_dict

router = APIRouter(prefix="/wrong-questions", tags=["错题本"])

REVIEW_INTERVALS = [1, 3, 7, 15, 30]


def _query():
    return select(WrongQuestion).options(
        selectinload(WrongQuestion.subject), selectinload(WrongQuestion.knowledge_point)
    )


def _get_question(db: Session, user_id: int, question_id: int) -> WrongQuestion:
    question = db.scalar(
        _query().where(WrongQuestion.id == question_id, WrongQuestion.user_id == user_id)
    )
    if question is None:
        raise HTTPException(status_code=404, detail="错题不存在")
    return question


@router.get("", response_model=list[WrongQuestionOut])
def list_questions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WrongQuestionOut]:
    questions = db.scalars(
        _query().where(WrongQuestion.user_id == user.id).order_by(WrongQuestion.created_at.desc())
    ).all()
    return [WrongQuestionOut(**wrong_dict(item)) for item in questions]


@router.post("", response_model=WrongQuestionOut, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: WrongQuestionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WrongQuestionOut:
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=400, detail="科目不存在")
    if payload.knowledge_point_id is not None:
        point = db.get(KnowledgePoint, payload.knowledge_point_id)
        if point is None or point.subject_id != payload.subject_id:
            raise HTTPException(status_code=400, detail="知识点与科目不匹配")
    question = WrongQuestion(
        user_id=user.id,
        next_review_at=now_local() + timedelta(days=1),
        **payload.model_dump(),
    )
    db.add(question)
    db.commit()
    question = _get_question(db, user.id, question.id)
    return WrongQuestionOut(**wrong_dict(question))


@router.patch("/{question_id}", response_model=WrongQuestionOut)
def update_question(
    question_id: int,
    payload: WrongQuestionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WrongQuestionOut:
    question = _get_question(db, user.id, question_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(question, field, value)
    if updates.get("status") == "已掌握":
        question.next_review_at = None
    elif updates.get("status") == "待复习" and question.next_review_at is None:
        question.next_review_at = now_local() + timedelta(days=1)
    db.commit()
    sync_weekly_goals(db, user.id)
    question = _get_question(db, user.id, question_id)
    return WrongQuestionOut(**wrong_dict(question))


@router.post("/{question_id}/analyze", response_model=WrongAnalysisOut)
async def analyze(
    question_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WrongAnalysisOut:
    question = _get_question(db, user.id, question_id)
    mastery: float | None = None
    point_name = question.knowledge_point.name if question.knowledge_point else "未关联知识点"
    if question.knowledge_point_id:
        state = db.scalar(
            select(UserKnowledge).where(
                UserKnowledge.user_id == user.id,
                UserKnowledge.knowledge_point_id == question.knowledge_point_id,
            )
        )
        mastery = state.mastery if state else None

    analysis, suggestions, provider = await analyze_wrong_question(question, point_name, mastery)
    question.analysis = analysis
    # 只保存分析内容，不把“分析次数”当成“复习次数”
    db.commit()
    return WrongAnalysisOut(
        question_id=question.id,
        analysis=analysis,
        suggestions=suggestions,
        provider=provider,
    )


@router.post("/{question_id}/review", response_model=WrongQuestionOut)
def review(
    question_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WrongQuestionOut:
    question = _get_question(db, user.id, question_id)
    question.review_count += 1
    days = REVIEW_INTERVALS[min(question.review_count - 1, len(REVIEW_INTERVALS) - 1)]
    question.next_review_at = now_local() + timedelta(days=days)
    question.status = "待复习"
    db.commit()
    sync_weekly_goals(db, user.id)
    question = _get_question(db, user.id, question_id)
    return WrongQuestionOut(**wrong_dict(question))


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    question = _get_question(db, user.id, question_id)
    db.delete(question)
    db.commit()
