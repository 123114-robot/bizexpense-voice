from contextlib import asynccontextmanager
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import auth, categories, dashboard, documents, expenses, health, suppliers, voice
from app.core.config import get_settings
from app.db.base import Base
from app.db.seed import seed_reference_data
from app.db.session import SessionLocal, engine


settings = get_settings()
logger = logging.getLogger("bizexpense.requests")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_environment != "production":
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            seed_reference_data(db)
    yield


app = FastAPI(title="BizExpense API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)


@app.middleware("http")
async def harden_responses(request: Request, call_next):
    supplied_id = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied_id
        if supplied_id
        and len(supplied_id) <= 128
        and all(char.isalnum() or char in "._-" for char in supplied_id)
        else uuid4().hex
    )
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    logger.info(
        "request_complete method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (perf_counter() - started) * 1000,
        request_id,
    )
    return response


for router in (
    health.router,
    auth.router,
    expenses.router,
    suppliers.router,
    categories.router,
    documents.router,
    dashboard.router,
    voice.router,
):
    app.include_router(router, prefix="/api")
