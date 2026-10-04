from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.voice import pending_actions
from app.models.user import User
from app.schemas.expense import ExpenseCreate
from app.services.expense_service import ExpenseService


@pytest.fixture(autouse=True)
def clear_pending_actions():
    pending_actions.clear()
    yield
    pending_actions.clear()


def create_expense(db, *, category_id=1, total="110.00", confirmed=True):
    user = db.scalar(select(User).where(User.email == "owner@example.com"))
    return ExpenseService(db, user).create(
        ExpenseCreate(
            supplier_name="Acme",
            category_id=category_id,
            invoice_date=date(2026, 9, 30),
            subtotal=Decimal(total),
            gst_amount=Decimal("10.00"),
            total_amount=Decimal(total),
            currency="AUD",
            description="Existing expense",
            ocr_confirmed=confirmed,
        )
    )


def test_voice_token_requires_server_configuration(auth_client, monkeypatch):
    monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)

    response = auth_client.get("/api/voice/token")

    assert response.status_code == 503
    assert response.json()["detail"] == "AssemblyAI is not configured"


def test_voice_tools_require_authentication(client):
    response = client.post("/api/voice/tools/summary", json={})

    assert response.status_code == 401


def test_voice_token_is_minted_server_side(auth_client, monkeypatch):
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "server-only-key")
    monkeypatch.setenv("ASSEMBLYAI_AGENT_ID", "agent-123")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"token": "single-use-token"}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.api.voice.httpx.get", fake_get)

    response = auth_client.get("/api/voice/token")

    assert response.status_code == 200
    assert response.json() == {
        "token": "single-use-token",
        "agent_id": "agent-123",
    }
    assert captured["url"] == "https://agents.assemblyai.com/v1/token"
    assert captured["headers"] == {"Authorization": "Bearer server-only-key"}
    assert captured["params"]["expires_in_seconds"] == 60


def test_voice_summary(auth_client, db):
    create_expense(db)

    response = auth_client.post("/api/voice/tools/summary", json={})

    assert response.status_code == 200
    assert response.json()["total_expenses"] == "110.00"
    assert response.json()["gst_paid"] == "10.00"


def test_prepare_expense(auth_client):
    response = auth_client.post(
        "/api/voice/tools/prepare-expense",
        json={
            "supplier_name": "Woolworths",
            "amount": "38.50",
            "invoice_date": "2026-09-30",
            "category_name": "Other",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmation_required"
    assert body["action"] == "create_expense"
    assert body["preview"] == {
        "supplier_name": "Woolworths",
        "amount": "38.50",
        "invoice_date": "2026-09-30",
        "category_name": "Other",
        "currency": "AUD",
    }


def test_prepare_expense_resolves_today(auth_client):
    response = auth_client.post(
        "/api/voice/tools/prepare-expense",
        json={
            "supplier_name": "Woolworths",
            "amount": "38.50",
            "invoice_date": "today",
        },
    )

    assert response.status_code == 200
    assert response.json()["preview"]["invoice_date"] == date.today().isoformat()


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"supplier_name": "Acme", "invoice_date": "2026-09-30"}, "amount"),
        ({"amount": "10.00", "invoice_date": "2026-09-30"}, "supplier_name"),
    ],
)
def test_prepare_expense_requires_fields(auth_client, payload, field):
    response = auth_client.post("/api/voice/tools/prepare-expense", json=payload)

    assert response.status_code == 422
    assert field in response.text


def test_confirm_create_expense(auth_client):
    prepared = auth_client.post(
        "/api/voice/tools/prepare-expense",
        json={
            "supplier_name": "Woolworths",
            "amount": "38.50",
            "invoice_date": "2026-09-30",
            "category_name": "Other",
        },
    ).json()

    response = auth_client.post(
        f"/api/voice/actions/{prepared['pending_action_id']}/confirm"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "executed"
    assert body["expense"]["total_amount"] == "38.50"
    assert body["expense"]["ocr_confirmed"] is True


def test_confirmation_is_idempotent(auth_client):
    prepared = auth_client.post(
        "/api/voice/tools/prepare-expense",
        json={
            "supplier_name": "Woolworths",
            "amount": "38.50",
            "invoice_date": "2026-09-30",
        },
    ).json()
    url = f"/api/voice/actions/{prepared['pending_action_id']}/confirm"

    assert auth_client.post(url).status_code == 200
    duplicate = auth_client.post(url)

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Pending action already executed"


def test_pending_action_is_isolated_by_user(auth_client):
    prepared = auth_client.post(
        "/api/voice/tools/prepare-expense",
        json={
            "supplier_name": "Woolworths",
            "amount": "38.50",
            "invoice_date": "2026-09-30",
        },
    ).json()
    other = auth_client.post(
        "/api/auth/register",
        json={
            "name": "Other Owner",
            "email": "other@example.com",
            "password": "secure-password-456",
        },
    ).json()

    response = auth_client.post(
        f"/api/voice/actions/{prepared['pending_action_id']}/confirm",
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Pending action not found"


def test_failed_confirmation_can_be_retried(auth_client, monkeypatch):
    prepared = auth_client.post(
        "/api/voice/tools/prepare-expense",
        json={
            "supplier_name": "Woolworths",
            "amount": "38.50",
            "invoice_date": "2026-09-30",
        },
    ).json()
    url = f"/api/voice/actions/{prepared['pending_action_id']}/confirm"
    original_create = ExpenseService.create

    def fail_create(self, payload):
        raise HTTPException(500, "Database unavailable")

    monkeypatch.setattr(ExpenseService, "create", fail_create)
    assert auth_client.post(url).status_code == 500
    monkeypatch.setattr(ExpenseService, "create", original_create)

    assert auth_client.post(url).status_code == 200


def test_prepare_update_latest_expense(auth_client, db):
    expense = create_expense(db, category_id=2)

    response = auth_client.post(
        "/api/voice/tools/prepare-update",
        json={"category_name": "Office Supplies"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "update_expense"
    assert body["preview"]["expense_id"] == expense.id
    assert body["preview"]["current_category"] == "Fuel"
    assert body["preview"]["proposed_category"] == "Office Supplies"


def test_update_preserves_existing_fields(auth_client, db):
    expense = create_expense(db, category_id=2, total="55.00")
    prepared = auth_client.post(
        "/api/voice/tools/prepare-update",
        json={"category_name": "Office Supplies"},
    ).json()

    result = auth_client.post(
        f"/api/voice/actions/{prepared['pending_action_id']}/confirm"
    ).json()["expense"]

    assert result["id"] == expense.id
    assert result["category_name"] == "Office Supplies"
    assert result["supplier_name"] == "Acme"
    assert result["total_amount"] == "55.00"
    assert result["gst_amount"] == "10.00"
    assert result["invoice_date"] == "2026-09-30"
    assert result["description"] == "Existing expense"
