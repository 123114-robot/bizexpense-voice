from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth import current_user
from app.models.user import User
from app.schemas.document import DocumentRead, OCRResult
from app.services.document_service import DocumentService
from app.services.ocr_service import get_ocr_provider

router = APIRouter(prefix="/documents", tags=["documents"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"


@router.post("/upload", response_model=DocumentRead, status_code=201)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    return await DocumentService(db, UPLOAD_DIR, user.id).upload(file)


@router.post("/{document_id}/extract", response_model=OCRResult)
def extract_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return DocumentService(db, UPLOAD_DIR, user.id).extract(document_id, get_ocr_provider())
