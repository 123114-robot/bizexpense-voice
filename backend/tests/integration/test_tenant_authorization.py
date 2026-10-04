def register(client, email: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"name": email.split("@")[0], "email": email, "password": "secure-password-123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def expense_payload():
    return {
        "supplier_name": "Private Supplier",
        "category_id": 1,
        "invoice_number": "PRIVATE-1",
        "invoice_date": "2026-09-30",
        "subtotal": "100.00",
        "gst_amount": "10.00",
        "total_amount": "110.00",
        "description": "Tenant-only expense",
        "ocr_confirmed": True,
    }


def test_business_endpoints_require_authentication(client):
    assert client.get("/api/expenses").status_code == 401
    assert client.get("/api/suppliers").status_code == 401
    assert client.get("/api/dashboard/summary").status_code == 401
    assert client.post(
        "/api/documents/upload",
        files={"file": ("receipt.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    ).status_code == 401


def test_expenses_suppliers_and_dashboard_are_isolated_by_user(client):
    first = register(client, "first@example.com")
    second = register(client, "second@example.com")

    created = client.post("/api/expenses", json=expense_payload(), headers=first)
    assert created.status_code == 201
    expense_id = created.json()["id"]

    assert client.get("/api/expenses", headers=second).json() == []
    assert client.get(f"/api/expenses/{expense_id}", headers=second).status_code == 404
    assert client.get("/api/suppliers", headers=second).json() == []
    assert client.get("/api/dashboard/summary", headers=second).json()["expense_count"] == 0

    assert len(client.get("/api/expenses", headers=first).json()) == 1
    assert len(client.get("/api/suppliers", headers=first).json()) == 1


def test_documents_are_isolated_by_user(client):
    first = register(client, "first@example.com")
    second = register(client, "second@example.com")
    uploaded = client.post(
        "/api/documents/upload",
        headers=first,
        files={"file": ("receipt.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    )
    assert uploaded.status_code == 201

    document_id = uploaded.json()["id"]
    assert client.post(
        f"/api/documents/{document_id}/extract", headers=second
    ).status_code == 404
    assert client.post(
        f"/api/documents/{document_id}/extract", headers=first
    ).status_code == 200
