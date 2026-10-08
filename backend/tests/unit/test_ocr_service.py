from decimal import Decimal
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.services.ocr_service import (
    MockOCRProvider,
    OCRProcessingError,
    TesseractOCRProvider,
    VisionOCRProvider,
    get_ocr_provider,
)


def test_mock_ocr_returns_expected_structure():
    result = MockOCRProvider().extract("invoice.pdf")
    assert result.supplier_name == "Acme Office Supplies"
    assert result.total == Decimal("110.00")
    assert result.gst == Decimal("10.00")
    assert result.confidence == 0.92
    assert result.confirmed is False


def test_tesseract_provider_parses_common_invoice_fields():
    text = """Acme Office Supplies
ABN 12 345 678 901
Invoice No: INV-204
Invoice Date: 15/09/2026
Due Date: 29/09/2026
Subtotal $100.00
GST $10.00
Total $110.00
"""
    provider = TesseractOCRProvider(engine=lambda _: (text, 87.5))

    result = provider.extract("invoice.png")

    assert result.supplier_name == "Acme Office Supplies"
    assert result.abn == "12 345 678 901"
    assert result.invoice_number == "INV-204"
    assert result.invoice_date.isoformat() == "2026-09-15"
    assert result.total == Decimal("110.00")
    assert result.confidence == 0.875
    assert result.confirmed is False


def test_tesseract_parser_handles_alternate_labels_and_month_name_dates():
    text = """TAX INVOICE
Harbour IT Services Pty Ltd
ABN: 51 824 753 556
Invoice # HITS-908
Date: 4 Oct 2026
Payment Due 18 Oct 2026
Sub Total: $1,234.50
Tax / GST: $123.45
Amount Due: AUD 1,357.95
"""
    provider = TesseractOCRProvider(engine=lambda _: (text, 81.0))

    result = provider.extract("invoice.jpg")

    assert result.supplier_name == "Harbour IT Services Pty Ltd"
    assert result.invoice_number == "HITS-908"
    assert result.invoice_date.isoformat() == "2026-10-04"
    assert result.due_date and result.due_date.isoformat() == "2026-10-18"
    assert result.subtotal == Decimal("1234.50")
    assert result.gst == Decimal("123.45")
    assert result.total == Decimal("1357.95")


def test_tesseract_provider_renders_pdf_then_removes_temporary_image():
    rendered_path = None

    def render_pdf(source: str, destination: str):
        nonlocal rendered_path
        assert source == "invoice.pdf"
        rendered_path = destination
        with open(destination, "wb") as image:
            image.write(b"\x89PNG\r\n\x1a\nrendered")

    def engine(path: str):
        assert path == rendered_path
        return """Acme Pty Ltd
Invoice No: PDF-1
Total $11.00
GST $1.00
Subtotal $10.00
""", 80.0

    provider = TesseractOCRProvider(engine=engine, pdf_renderer=render_pdf)
    result = provider.extract("invoice.pdf")

    assert result.invoice_number == "PDF-1"
    assert result.total == Decimal("11.00")
    assert rendered_path is not None
    assert not Path(rendered_path).exists()


def test_default_pdf_renderer_creates_png_from_first_page(tmp_path):
    pdf_path = tmp_path / "invoice.pdf"
    png_path = tmp_path / "invoice.png"
    Image.new("RGB", (20, 20), "white").save(pdf_path, format="PDF")

    TesseractOCRProvider._render_pdf_first_page(str(pdf_path), str(png_path))

    assert png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_provider_factory_uses_environment(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "tesseract")
    assert isinstance(get_ocr_provider(), TesseractOCRProvider)


def test_vision_provider_extracts_strict_unconfirmed_invoice_data(tmp_path):
    invoice = tmp_path / "invoice.png"
    invoice.write_bytes(b"\x89PNG\r\n\x1a\nimage")

    def handler(request: httpx.Request):
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "vision-model"
        assert body["messages"][0]["content"][0]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "supplier_name": "Woolworths",
                                    "abn": "88 000 014 675",
                                    "invoice_number": "R-100",
                                    "invoice_date": "2026-10-02",
                                    "due_date": None,
                                    "subtotal": "35.00",
                                    "gst": "3.50",
                                    "total": "38.50",
                                    "currency": "AUD",
                                    "confidence": 0.91,
                                }
                            )
                        }
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = VisionOCRProvider(
        api_key="test-key",
        base_url="https://vision.example/v1",
        model="vision-model",
        client=client,
    ).extract(str(invoice))

    assert result.supplier_name == "Woolworths"
    assert result.total == Decimal("38.50")
    assert result.confirmed is False


def test_vision_provider_rejects_invalid_accounting_values(tmp_path):
    invoice = tmp_path / "invoice.jpg"
    invoice.write_bytes(b"\xff\xd8\xffimage")
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "supplier_name": "Example",
                            "invoice_date": "2026-10-02",
                            "subtotal": "10.00",
                            "gst": "12.00",
                            "total": "10.00",
                            "currency": "AUD",
                            "confidence": 0.8,
                        }
                    )
                }
            }
        ]
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))
    )

    with pytest.raises(OCRProcessingError, match="invalid invoice data"):
        VisionOCRProvider("key", "https://vision.example/v1", "model", client).extract(
            str(invoice)
        )


def test_provider_factory_supports_vision(monkeypatch):
    monkeypatch.setenv("OCR_PROVIDER", "vision")
    monkeypatch.setenv("VISION_API_KEY", "test-key")
    assert isinstance(get_ocr_provider(), VisionOCRProvider)
