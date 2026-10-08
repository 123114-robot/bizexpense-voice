import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.services.document_service import DocumentService


def upload(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


def test_upload_rejects_content_that_does_not_match_declared_type(db, tmp_path):
    service = DocumentService(db, tmp_path, 1)

    with pytest.raises(HTTPException, match="content does not match") as error:
        asyncio.run(service.upload(upload("receipt.png", "image/png", b"not-a-png")))

    assert error.value.status_code == 415
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_mismatched_filename_extension(db, tmp_path):
    service = DocumentService(db, tmp_path, 1)

    with pytest.raises(HTTPException, match="extension does not match") as error:
        asyncio.run(
            service.upload(
                upload("receipt.exe", "image/png", b"\x89PNG\r\n\x1a\ncontent")
            )
        )

    assert error.value.status_code == 415


def test_upload_rejects_empty_files(db, tmp_path):
    service = DocumentService(db, tmp_path, 1)

    with pytest.raises(HTTPException, match="empty") as error:
        asyncio.run(service.upload(upload("receipt.pdf", "application/pdf", b"")))

    assert error.value.status_code == 400


def test_upload_accepts_matching_png_content_and_extension(db, tmp_path):
    service = DocumentService(db, tmp_path, 1)

    document = asyncio.run(
        service.upload(
            upload("receipt.png", "image/png", b"\x89PNG\r\n\x1a\ncontent")
        )
    )

    assert document.filename.endswith(".png")
    assert (tmp_path / document.filename).read_bytes().startswith(b"\x89PNG")
