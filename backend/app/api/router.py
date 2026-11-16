from fastapi import APIRouter

from ..core.config import settings
from .routes import ai, auth, dashboard, goals, knowledge, subjects, tasks, wrong_questions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(goals.router)
api_router.include_router(subjects.router)
api_router.include_router(tasks.router)
api_router.include_router(knowledge.router)
api_router.include_router(wrong_questions.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)


@api_router.get("/health", tags=["系统"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
