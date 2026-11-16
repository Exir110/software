from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Subject, User
from ...schemas.domain import SubjectOut
from ..deps import get_current_user

router = APIRouter(prefix="/subjects", tags=["科目"])


@router.get("", response_model=list[SubjectOut])
def list_subjects(
    _: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SubjectOut]:
    subjects = db.scalars(select(Subject).order_by(Subject.id)).all()
    return [SubjectOut(id=item.id, name=item.name, code=item.code) for item in subjects]
