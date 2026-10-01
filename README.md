# BizExpense Voice

Voice-first expense management for Australian SMEs powered by the AssemblyAI Voice Agent API.

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

## Local setup

Prerequisites: Python 3.11+, Node 20+, Docker, an AssemblyAI API key, and a published stored agent.

```powershell
Copy-Item .env.example .env
# Fill ASSEMBLYAI_API_KEY and ASSEMBLYAI_AGENT_ID in .env
docker compose up -d db
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
pip install -r backend/requirements-dev.txt
uvicorn app.main:app --reload --app-dir backend --env-file .env
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`, allow microphone access, and start BizExpense Voice from the dashboard.

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
