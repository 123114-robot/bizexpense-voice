from abc import ABC, abstractmethod
import base64
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable

import httpx
from pydantic import ValidationError

from app.schemas.document import OCRResult


class OCRProvider(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> OCRResult: ...


class MockOCRProvider(OCRProvider):
    def extract(self, file_path: str) -> OCRResult:
        today = date.today()
        return OCRResult(
            supplier_name="Acme Office Supplies", abn="12 345 678 901",
            invoice_number="DEMO-1001", invoice_date=today, due_date=today + timedelta(days=14),
            subtotal=Decimal("100.00"), gst=Decimal("10.00"), total=Decimal("110.00"),
            currency="AUD", confidence=0.92, confirmed=False,
        )


class OCRProcessingError(RuntimeError):
    """Raised when a document cannot be processed by the selected OCR provider."""


class TesseractOCRProvider(OCRProvider):
    def __init__(
        self,
        engine: Callable[[str], tuple[str, float]] | None = None,
        pdf_renderer: Callable[[str, str], None] | None = None,
    ):
        self.engine = engine or self._run_tesseract
        self.pdf_renderer = pdf_renderer or self._render_pdf_first_page

    def extract(self, file_path: str) -> OCRResult:
        suffix = Path(file_path).suffix.lower()
        if suffix not in {".pdf", ".png", ".jpg", ".jpeg"}:
            raise OCRProcessingError(
                "Tesseract OCR currently supports PDF, PNG and JPEG invoices only"
            )
        image_path = file_path
        temporary_image: Path | None = None
        try:
            if suffix == ".pdf":
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as image:
                    temporary_image = Path(image.name)
                self.pdf_renderer(file_path, str(temporary_image))
                image_path = str(temporary_image)
            text, confidence_percent = self.engine(image_path)
        except OCRProcessingError:
            raise
        except Exception as exc:
            raise OCRProcessingError(f"Tesseract OCR failed: {exc}") from exc
        finally:
            if temporary_image:
                temporary_image.unlink(missing_ok=True)
        return self._parse(text, confidence_percent)

    @staticmethod
    def _render_pdf_first_page(file_path: str, destination: str) -> None:
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise OCRProcessingError(
                "Install pypdfium2 to process PDF invoices"
            ) from exc
        document = None
        page = None
        bitmap = None
        try:
            document = pdfium.PdfDocument(file_path)
            if len(document) == 0:
                raise OCRProcessingError("PDF invoice has no pages")
            page = document[0]
            bitmap = page.render(scale=3)
            bitmap.to_pil().save(destination, format="PNG")
        except OCRProcessingError:
            raise
        except Exception as exc:
            raise OCRProcessingError(f"PDF rendering failed: {exc}") from exc
        finally:
            for resource in (bitmap, page, document):
                close = getattr(resource, "close", None)
                if close:
                    close()

    @staticmethod
    def _run_tesseract(file_path: str) -> tuple[str, float]:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise OCRProcessingError("Install pytesseract and Pillow to use Tesseract OCR") from exc
        configured_command = os.getenv("TESSERACT_CMD")
        windows_command = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if configured_command:
            pytesseract.pytesseract.tesseract_cmd = configured_command
        elif windows_command.exists():
            pytesseract.pytesseract.tesseract_cmd = str(windows_command)
        try:
            data = pytesseract.image_to_data(Image.open(file_path), output_type=pytesseract.Output.DICT)
        except pytesseract.TesseractNotFoundError as exc:
            raise OCRProcessingError("Tesseract executable is not installed or not on PATH") from exc
        lines: dict[tuple[int, int, int], list[str]] = {}
        for index, raw_word in enumerate(data["text"]):
            word = raw_word.strip()
            if word:
                key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
                lines.setdefault(key, []).append(word)
        confidences = [float(value) for value in data["conf"] if float(value) >= 0]
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return "\n".join(" ".join(words) for words in lines.values()), confidence

    @staticmethod
    def _parse(text: str, confidence_percent: float) -> OCRResult:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        def match(pattern: str) -> str | None:
            result = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            return result.group(1).strip() if result else None

        def money(label: str) -> Decimal:
            value = match(
                rf"^{label}\s*:?\s*(?:AUD\s*)?\$?([\d,]+(?:\.\d{{2}})?)"
            )
            return Decimal(value.replace(",", "")) if value else Decimal("0.00")

        def parsed_date(label: str) -> date | None:
            value = match(
                rf"^(?:{label})\s*:?\s*"
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2}|"
                r"\d{1,2}\s+[A-Z]{3,9}\s+\d{4})"
            )
            if not value:
                return None
            for format_string in (
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%Y-%m-%d",
                "%d %b %Y",
                "%d %B %Y",
            ):
                try:
                    return date.fromisoformat(value) if format_string == "%Y-%m-%d" else datetime.strptime(value, format_string).date()
                except ValueError:
                    continue
            return None

        supplier_name = next(
            (
                line
                for line in lines
                if not re.match(
                    r"^(?:tax\s+invoice|invoice|receipt|abn\b|date\b|due\b|"
                    r"payment\s+due|sub\s*total|gst\b|tax\s*/?\s*gst|amount\s+due|total\b)",
                    line,
                    re.IGNORECASE,
                )
            ),
            "Unknown supplier",
        )

        return OCRResult(
            supplier_name=supplier_name,
            abn=match(r"\bABN\s*:?\s*([\d ]{11,14})"),
            invoice_number=match(r"Invoice\s*(?:No\.?|Number|#)\s*:?\s*([A-Z0-9-]+)"),
            invoice_date=parsed_date(r"Invoice\s+Date|Date") or date.today(),
            due_date=parsed_date(r"Due\s+Date|Payment\s+Due"),
            subtotal=money(r"Sub\s*Total"),
            gst=money(r"(?:GST|Tax\s*/?\s*GST)"),
            total=money(r"(?:Total|Amount\s+Due)"),
            currency="AUD",
            confidence=max(0.0, min(confidence_percent / 100, 1.0)),
            confirmed=False,
        )


class VisionOCRProvider(OCRProvider):
    MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        client: httpx.Client | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = client

    def extract(self, file_path: str) -> OCRResult:
        suffix = Path(file_path).suffix.lower()
        if suffix not in self.MIME_TYPES:
            raise OCRProcessingError("Vision OCR currently supports PNG and JPEG invoices only")
        if not self.api_key:
            raise OCRProcessingError("VISION_API_KEY is required for Vision OCR")

        encoded = base64.b64encode(Path(file_path).read_bytes()).decode()
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{self.MIME_TYPES[suffix]};base64,{encoded}"
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract this invoice without guessing missing values. Return only JSON "
                                "with supplier_name, abn, invoice_number, invoice_date, due_date, "
                                "subtotal, gst, total, currency, and confidence. Dates must be YYYY-MM-DD, "
                                "money must be decimal numbers, currency must be a three-letter ISO code, "
                                "confidence must be between 0 and 1, and nullable fields may be null."
                            ),
                        },
                    ],
                }
            ],
        }
        try:
            response = self._post(payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            extracted = json.loads(content)
            extracted["confirmed"] = False
            return OCRResult.model_validate(extracted)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise OCRProcessingError("Vision OCR request returned an invalid response") from exc
        except ValidationError as exc:
            raise OCRProcessingError("Vision OCR returned invalid invoice data") from exc

    def _post(self, payload: dict) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/chat/completions"
        if self.client:
            return self.client.post(url, headers=headers, json=payload, timeout=30)
        with httpx.Client(timeout=30) as client:
            return client.post(url, headers=headers, json=payload)


def get_ocr_provider() -> OCRProvider:
    provider = os.getenv("OCR_PROVIDER", "mock").lower()
    if provider == "tesseract":
        return TesseractOCRProvider()
    if provider == "vision":
        return VisionOCRProvider(
            api_key=os.getenv("VISION_API_KEY", ""),
            base_url=os.getenv("VISION_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("VISION_MODEL", "gpt-4o-mini"),
        )
    return MockOCRProvider()
