from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth import current_user
from app.core.config import get_settings
from app.core.rate_limit import RateLimitDependency
from app.models.user import User
from app.schemas.document import DocumentRead, OCRResult
from app.services.document_service import DocumentService
from app.services.ocr_service import get_ocr_provider

router = APIRouter(prefix="/documents", tags=["documents"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
settings = get_settings()
upload_rate_limit = RateLimitDependency(
    "upload", settings.upload_rate_limit_requests, settings.rate_limit_window_seconds
)
ocr_rate_limit = RateLimitDependency(
    "ocr", settings.ocr_rate_limit_requests, settings.rate_limit_window_seconds
)


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=201,
    dependencies=[Depends(upload_rate_limit)],
)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    return await DocumentService(db, UPLOAD_DIR, user.id).upload(file)


@router.post(
    "/{document_id}/extract",
    response_model=OCRResult,
    dependencies=[Depends(ocr_rate_limit)],
)
def extract_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return DocumentService(db, UPLOAD_DIR, user.id).extract(document_id, get_ocr_provider())
