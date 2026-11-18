from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.security import create_access_token, hash_password, verify_password
from ...core.clock import today_local
from ...db.seed import next_exam_date
from ...db.session import get_db
from ...models import ExamGoal, KnowledgePoint, User, UserKnowledge
from ...schemas.domain import LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])

LOGIN_WINDOW_SECONDS = 60
LOGIN_MAX_ATTEMPTS = 10
_login_attempts: dict[str, list[float]] = {}


def _check_login_rate(key: str) -> None:
    now = monotonic()
    attempts = [item for item in _login_attempts.get(key, []) if now - item < LOGIN_WINDOW_SECONDS]
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="登录尝试过于频繁，请一分钟后再试")
    attempts.append(now)
    _login_attempts[key] = attempts


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, username=user.username, display_name=user.display_name)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.scalar(select(User).where(User.username == payload.username)) is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    db.add(ExamGoal(user_id=user.id, exam_date=next_exam_date(today_local())))

    for point in db.scalars(select(KnowledgePoint)).all():
        db.add(
            UserKnowledge(
                user_id=user.id,
                knowledge_point_id=point.id,
                mastery=50.0,
                previous_mastery=50.0,
            )
        )
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(str(user.id)), user=_user_out(user))


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    host = request.client.host if request.client else "unknown"
    key = f"{host}:{payload.username}"
    _check_login_rate(key)
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    _login_attempts.pop(key, None)
    return TokenResponse(access_token=create_access_token(str(user.id)), user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
