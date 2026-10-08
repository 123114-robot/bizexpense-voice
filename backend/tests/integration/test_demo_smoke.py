from pathlib import Path

from app.models.document import UploadedDocument


def test_primary_demo_flow(client, db):
    registered = client.post(
        "/api/auth/register",
        json={"name": "Demo Owner", "email": "demo@example.com", "password": "demo-password-123"},
    )
    assert registered.status_code == 201
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

    expense = client.post(
        "/api/expenses",
        headers=headers,
        json={"supplier_name": "Demo Supplier", "category_id": 1, "invoice_number": "DEMO-1", "invoice_date": "2026-09-30", "subtotal": "100", "gst_amount": "10", "total_amount": "110", "description": "Demo expense", "ocr_confirmed": True},
    )
    assert expense.status_code == 201
    assert client.get("/api/dashboard/summary", headers=headers).json()["total_expenses"] == "110.00"
    export = client.get("/api/expenses/export.csv", headers=headers)
    assert export.status_code == 200
    assert "DEMO-1" in export.text

    uploaded = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("receipt.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    assert client.post(f"/api/documents/{document_id}/extract", headers=headers).status_code == 200
    stored = db.get(UploadedDocument, document_id)
    if stored:
        Path(stored.file_path).unlink(missing_ok=True)
