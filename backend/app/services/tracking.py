from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import UserKnowledge


def get_or_create_state(db: Session, user_id: int, knowledge_point_id: int) -> UserKnowledge:
    state = db.scalar(
        select(UserKnowledge).where(
            UserKnowledge.user_id == user_id,
            UserKnowledge.knowledge_point_id == knowledge_point_id,
        )
    )
    if state is None:
        state = UserKnowledge(
            user_id=user_id,
            knowledge_point_id=knowledge_point_id,
            mastery=50.0,
            previous_mastery=50.0,
        )
        db.add(state)
        db.flush()
    return state


def state_map(db: Session, user_id: int) -> dict[int, UserKnowledge]:
    states = db.scalars(select(UserKnowledge).where(UserKnowledge.user_id == user_id)).all()
    return {state.knowledge_point_id: state for state in states}
