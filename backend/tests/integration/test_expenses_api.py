from datetime import date
import csv
from io import StringIO


def expense_payload(**changes):
    payload = {
        "supplier_name": "Acme Office Supplies",
        "category_id": 1,
        "invoice_number": "INV-100",
        "invoice_date": "2026-09-02",
        "subtotal": "100.00",
        "gst_amount": "10.00",
        "total_amount": "110.00",
        "description": "Stationery",
        "ocr_confirmed": True,
    }
    payload.update(changes)
    return payload


def test_expense_crud(auth_client):
    client = auth_client
    created = client.post("/api/expenses", json=expense_payload())
    assert created.status_code == 201
    expense_id = created.json()["id"]
    assert client.get(f"/api/expenses/{expense_id}").json()["description"] == "Stationery"
    updated = client.put(
        f"/api/expenses/{expense_id}", json=expense_payload(description="Updated")
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated"
    assert len(client.get("/api/expenses").json()) == 1
    assert client.delete(f"/api/expenses/{expense_id}").status_code == 204
    assert client.get(f"/api/expenses/{expense_id}").status_code == 404


def test_dashboard_excludes_unconfirmed_ocr_drafts(auth_client):
    client = auth_client
    current_date = date.today().isoformat()
    client.post("/api/expenses", json=expense_payload(invoice_date=current_date))
    client.post(
        "/api/expenses",
        json=expense_payload(
            supplier_name="Fuel Station",
            category_id=2,
            invoice_number="INV-101",
            subtotal="50",
            gst_amount="5",
            total_amount="55",
            invoice_date=current_date,
        ),
    )
    client.post(
        "/api/expenses",
        json=expense_payload(
            invoice_number="DRAFT-101",
            total_amount="220",
            subtotal="200",
            gst_amount="20",
            ocr_confirmed=False,
            invoice_date=current_date,
        ),
    )
    summary = client.get("/api/dashboard/summary")
    assert summary.status_code == 200
    assert summary.json()["total_expenses"] == "165.00"
    assert summary.json()["expenses_this_month"] == "165.00"
    assert summary.json()["gst_paid"] == "15.00"
    assert summary.json()["expense_count"] == 2
    assert summary.json()["average_expense"] == "82.50"
    assert summary.json()["top_suppliers"] == [
        {"supplier": "Acme Office Supplies", "total": "110.00", "expense_count": 1},
        {"supplier": "Fuel Station", "total": "55.00", "expense_count": 1},
    ]
    assert summary.json()["category_breakdown"] == [
        {"category": "Office Supplies", "total": "110.00", "expense_count": 1},
        {"category": "Fuel", "total": "55.00", "expense_count": 1},
    ]
    assert len(summary.json()["monthly_trend"]) == 6
    assert summary.json()["monthly_trend"][-1] == {
        "month": date.today().strftime("%Y-%m"),
        "total": "165.00",
    }


def test_unconfirmed_ocr_expense_is_preserved_as_unconfirmed(auth_client):
    client = auth_client
    created = client.post("/api/expenses", json=expense_payload(ocr_confirmed=False))
    assert created.status_code == 201
    assert created.json()["ocr_confirmed"] is False


def test_duplicate_expense_is_saved_with_non_blocking_warning(auth_client):
    client = auth_client
    first = client.post("/api/expenses", json=expense_payload(invoice_number="DUP-1"))
    second = client.post("/api/expenses", json=expense_payload(invoice_number="DUP-1"))

    assert first.status_code == 201
    assert first.json()["duplicate_warning"] is False
    assert second.status_code == 201
    assert second.json()["duplicate_warning"] is True
    assert second.json()["duplicate_expense_id"] == first.json()["id"]
    assert len(client.get("/api/expenses").json()) == 2


def test_expense_filters_and_csv_export_use_the_same_results(auth_client):
    client = auth_client
    client.post(
        "/api/expenses",
        json=expense_payload(
            supplier_name="Fuel Station",
            category_id=2,
            invoice_number="FUEL-1",
            invoice_date="2026-09-15",
            description="=HYPERLINK(\"https://example.invalid\", \"Van fuel\")",
        ),
    )
    client.post(
        "/api/expenses",
        json=expense_payload(
            invoice_number="OFFICE-1",
            invoice_date="2026-09-16",
        ),
    )
    client.post(
        "/api/expenses",
        json=expense_payload(
            supplier_name="Fuel Station",
            category_id=2,
            invoice_number="FUEL-DRAFT",
            invoice_date="2026-09-17",
            description="Draft van fuel",
            ocr_confirmed=False,
        ),
    )

    query = (
        "search=fuel&category_id=2&date_from=2026-09-01&date_to=2026-09-30"
        "&ocr_confirmed=true"
    )
    filtered = client.get(f"/api/expenses?{query}")
    assert filtered.status_code == 200
    assert [row["invoice_number"] for row in filtered.json()] == ["FUEL-1"]

    exported = client.get(f"/api/expenses/export.csv?{query}")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=bizexpense-expenses.csv" == exported.headers[
        "content-disposition"
    ]
    rows = list(csv.DictReader(StringIO(exported.text.lstrip("\ufeff"))))
    assert len(rows) == 1
    assert rows[0]["Invoice number"] == "FUEL-1"
    assert rows[0]["Supplier"] == "Fuel Station"
    assert rows[0]["Status"] == "Confirmed"
    assert rows[0]["Description"].startswith("'=HYPERLINK")
