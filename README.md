# BizExpense Voice

BizExpense Voice is an AssemblyAI Voice Agent Hackathon extension of the existing BizExpense expense-management MVP.

It preserves the original expense-management architecture and adds a voice-first interaction layer powered by AssemblyAI.

Busy small-business users often need to record expenses while travelling, handling receipts, or doing other work. BizExpense Voice lets them speak naturally to create, query, and correct expenses without navigating forms.

AssemblyAI runs the real-time speech recognition, turn-taking, agent reasoning, tool selection, and spoken response loop. BizExpense keeps ownership of business rules, PostgreSQL persistence, analytics, OCR, and the dashboard.

- Original project: https://github.com/123114-robot/bizexpense
- Hackathon extension: https://github.com/123114-robot/bizexpense-voice

## Demo

From the existing dashboard, start the microphone and try:

- “I spent $38.50 at Woolworths today.” Review the prepared expense, then click **Confirm**.
- “How much did I spend this month?” The agent reads live `DashboardService` data.
- “Change my last expense to office supplies.” Review the category-only change, then confirm it.

Without AssemblyAI credentials, use the clearly labelled **Prototype demo — mock voice input** buttons. They simulate transcript, intent, and tool selection only; confirmed actions still call the configured BizExpense API. Mock mode is not evidence of a live AssemblyAI integration.

Writes are always prepared first. Nothing reaches the database until the user clicks **Confirm**, and repeated confirmation cannot execute the same action twice.

## Architecture

```text
Browser microphone
  → AssemblyAI Voice Agent API (PCM16, 24 kHz WebSocket)
  → AssemblyAI managed reasoning and function-tool selection
  → BizExpense FastAPI voice endpoints
  → existing ExpenseService / DashboardService
  → PostgreSQL
  → tool result and spoken AssemblyAI reply
  → dashboard refresh
```

The voice layer does not replace the existing REST API, schemas, expense CRUD, dashboard, OCR flow, or database model. A short-lived in-process pending-action store is intentionally used for this hackathon MVP; it is not suitable for multi-instance production deployment.

## Supported voice actions

- Prepare an AUD expense from supplier, amount, and date; an omitted category safely uses the existing `Other` category.
- Read confirmed total, current-month, GST, and category summary data.
- Prepare a category-only change to the latest confirmed expense while preserving every other required field.
- Resolve `today`, `yesterday`, and ISO `YYYY-MM-DD` dates server-side.

## AssemblyAI integration

The backend mints a single-use, 60-second browser token from `GET https://agents.assemblyai.com/v1/token`; the API key never enters the React bundle. The browser then connects to `wss://agents.assemblyai.com/v1/ws` using a stored agent ID.

The stored agent definition is in `assemblyai/agent.json`. Create it once:

```powershell
$env:ASSEMBLYAI_API_KEY = "your-key"
python scripts/create_voice_agent.py
```

Save the printed ID as `ASSEMBLYAI_AGENT_ID`. The agent exposes only three function tools: `prepare_expense`, `get_expense_summary`, and `prepare_expense_update`.

The synchronized BizExpense foundation also includes:

- Expense create, filtered list/search, CSV export, view, edit and delete
- PDF/JPEG/PNG upload (10 MB limit) and replaceable Mock/Tesseract `OCRProvider`
- Mandatory user confirmation on the OCR review screen
- Database-backed dashboard totals, monthly spend, GST, count, category breakdown and six-month trend
- Seeded demo admin and ten expense categories
- FastAPI OpenAPI docs at `http://localhost:8000/docs`
- Alembic migration baseline, environment-based CORS and request/security headers
- Trusted-host enforcement and content-signature validation for PDF/JPEG/PNG uploads
- Authentication foundation with registration, PBKDF2 password hashing, JWT login and current-user lookup

## Local setup

Prerequisites: Python 3.11+, Node 20+, Docker, an AssemblyAI API key, and a published stored agent.

```powershell
Copy-Item .env.example .env
# Fill ASSEMBLYAI_API_KEY and ASSEMBLYAI_AGENT_ID in .env
docker compose up -d db
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
pip install -r backend/requirements-dev.txt
cd backend
python -m alembic upgrade head
cd ..
uvicorn app.main:app --reload --app-dir backend --env-file .env
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The API reads `DATABASE_URL`, `CORS_ORIGINS` and `ALLOWED_HOSTS`. Development mode still creates missing tables for convenience; production mode requires `python -m alembic upgrade head` before startup. Every API response includes a request ID and baseline browser security headers. Uploads must have a permitted MIME type, matching extension and matching file signature.

Authentication endpoints are available at `/api/auth/register`, `/api/auth/login` and `/api/auth/me`. Set a strong `JWT_SECRET` in production; startup rejects the development default. Expense, supplier, dashboard, document and OCR endpoints require a Bearer token and isolate records by the authenticated user. The current MVP treats each user as one tenant; organization membership can be added later without accepting tenant IDs from clients.

The Web app redirects unauthenticated visitors to `/login`, supports registration, login and sign-out, stores the JWT in local storage for this prototype, and attaches it to API requests and CSV downloads.

Runtime probes are available without authentication: `/api/health` is a lightweight liveness check, while `/api/health/ready` verifies the database connection and returns HTTP 503 when it is unavailable.

After signing in, allow microphone access and start BizExpense Voice from the dashboard.

## Deployment

Deploy the Vite frontend and FastAPI backend using their existing build/runtime commands, backed by PostgreSQL. Set `CORS_ORIGINS` to the deployed frontend origin. The current function-tool design works without exposing FastAPI directly to AssemblyAI; the browser calls the same-origin `/api` backend.

Required backend environment variables:

```text
DATABASE_URL
ASSEMBLYAI_API_KEY
ASSEMBLYAI_AGENT_ID
CORS_ORIGINS
```

`PUBLIC_API_BASE_URL` is reserved for a future stored-agent HTTP-tool deployment and is not required by the current function-tool architecture.

## Verification

```powershell
cd backend
python -m pytest -q
python -m ruff check .

cd ../frontend
npm test
npm run build
npm run lint
```

Normal automated tests never call AssemblyAI or a real microphone. See [docs/demo-script.md](docs/demo-script.md) for the manual live acceptance sequence.

## Limitations

- A real AssemblyAI key, stored agent ID, browser microphone, and running PostgreSQL instance are required for the live demo.
- Pending actions are held in process for five minutes and are lost on backend restart.
- Voice updates intentionally support category changes only.
- GST is never inferred: voice-created expenses use `0.00` GST unless a future explicit flow collects it.
- Existing OCR, upload, expense management, CSV export, and dashboard features remain unchanged.

The backend smoke suite verifies the primary demo path: registration, JWT authentication, expense creation, dashboard reconciliation, CSV export, document upload and OCR extraction.

See [docs/project-overview.md](docs/project-overview.md), [PROJECT_TASKS.md](PROJECT_TASKS.md), and the remaining `docs/` files for design decisions and future phases.
