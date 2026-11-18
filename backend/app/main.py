from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401 - register SQLAlchemy models before create_all
from .api.router import api_router
from .core.config import settings
from .db.base import Base
from .db.seed import seed_demo
from .db.session import SessionLocal, engine, ensure_schema


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    if settings.seed_demo:
        with SessionLocal() as db:
            seed_demo(db)
    yield


app = FastAPI(
    title=settings.app_name,
    description="面向考研群体的学习规划与知识追踪系统",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", tags=["系统"])
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.3.0",
        "docs": "/docs",
        "health": "/api/health",
    }
