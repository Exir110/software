from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import ExamGoal, User
from ...schemas.domain import GoalIn, GoalOut
from ..deps import get_current_user

router = APIRouter(prefix="/goals", tags=["备考目标"])


def _goal_out(goal: ExamGoal) -> GoalOut:
    return GoalOut(
        exam_date=goal.exam_date,
        target_school=goal.target_school,
        target_major=goal.target_major,
        target_score=goal.target_score,
        daily_minutes=goal.daily_minutes,
        days_remaining=max((goal.exam_date - date.today()).days, 0),
    )


@router.get("/current", response_model=GoalOut)
def current_goal(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> GoalOut:
    goal = db.query(ExamGoal).filter(ExamGoal.user_id == user.id).first()
    if goal is None:
        raise HTTPException(status_code=404, detail="尚未设置备考目标")
    return _goal_out(goal)


@router.put("/current", response_model=GoalOut)
def upsert_goal(
    payload: GoalIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalOut:
    goal = db.query(ExamGoal).filter(ExamGoal.user_id == user.id).first()
    if goal is None:
        goal = ExamGoal(user_id=user.id, **payload.model_dump())
        db.add(goal)
    else:
        for field, value in payload.model_dump().items():
            setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return _goal_out(goal)
