from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import categories, dashboard, documents, expenses, suppliers, voice
from app.db.base import Base
from app.db.seed import seed_reference_data
from app.db.session import SessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_reference_data(db)
    yield


app = FastAPI(title="BizExpense API", version="0.1.0", lifespan=lifespan)
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


for router in (expenses.router, suppliers.router, categories.router, documents.router, dashboard.router, voice.router):
    app.include_router(router, prefix="/api")

