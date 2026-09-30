# BizExpense Voice

BizExpense Voice is an AssemblyAI Voice Agent Hackathon extension of the existing BizExpense expense-management MVP.

It preserves the original expense-management architecture and adds a voice-first interaction layer powered by AssemblyAI.

Original project:
https://github.com/123114-robot/bizexpense

Hackathon extension:
https://github.com/123114-robot/bizexpense-voice

BizExpense is a portfolio-quality MVP for Australian SMEs to record expenses, upload invoices, review mock OCR results and see live spending totals. It deliberately keeps authentication, production OCR and accounting integrations out of scope.

## What works

- Expense create, filtered list/search, CSV export, view, edit and delete
- PDF/JPEG/PNG upload (10 MB limit) and replaceable Mock/Tesseract `OCRProvider`
- Mandatory user confirmation on the OCR review screen
- Database-backed dashboard totals, monthly spend, GST, count, category breakdown and six-month trend
- Seeded demo admin and ten expense categories
- FastAPI OpenAPI docs at `http://localhost:8000/docs`

## Local setup

Prerequisites: Python 3.11+, Node 20+, and Docker (for PostgreSQL).

```powershell
Copy-Item .env.example .env
docker compose up -d db
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
pip install -r backend/requirements-dev.txt
uvicorn app.main:app --reload --app-dir backend
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The API reads `DATABASE_URL`; the `.env.example` value is its default. Tables and reference data are created on API startup for this MVP.

Mock OCR is the default. The Tesseract integration is a prototype with basic PNG/JPEG invoice-field parsing, not production-grade OCR. Enable it with `OCR_PROVIDER=tesseract`; Windows standard installs are detected automatically, otherwise set `TESSERACT_CMD`. Production accuracy, broad layout compatibility, PDF OCR, field-level confidence, cloud OCR and validation against a large real-invoice dataset are intentionally deferred.

## Verification

```powershell
cd backend; python -m pytest -q; ruff check .
cd ../frontend; npm test; npm run build; npm run lint
```

See [docs/project-overview.md](docs/project-overview.md), [PROJECT_TASKS.md](PROJECT_TASKS.md), and the remaining `docs/` files for design decisions and future phases.
