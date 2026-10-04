# BizExpense Voice demo script

Target length: 2–3 minutes.

## 0:00–0:15 — Problem

“Small-business owners often need to record expenses while travelling, handling stock, or working with receipts. Forms interrupt that work.”

## 0:15–0:30 — Solution and architecture

Show the existing BizExpense dashboard and the voice panel.

“BizExpense Voice adds an AssemblyAI interaction layer. AssemblyAI handles the real-time voice loop and tool selection; the existing BizExpense services still own validation, persistence, and analytics.”

## 0:30–1:10 — Demo A: create

1. Click **Start voice assistant** and wait for **Ready**.
2. Say: “I spent $38.50 at Woolworths today.”
3. Show the live/final transcript and prepared expense card.
4. Point out that no write has happened yet.
5. Click **Confirm** once.
6. Show success and the automatically refreshed dashboard total.

## 1:10–1:35 — Demo B: query

1. Say: “How much did I spend this month?”
2. Show the transcript.
3. Let the agent speak the amount returned by the existing `DashboardService`.

## 1:35–2:05 — Demo C: update

1. Ask: “What expense categories can I use?”
2. Say: “Classify my Woolworths expense as office supplies.”
3. Show the current and proposed categories.
4. Click **Confirm** and show the refreshed category breakdown.

## 2:05–2:25 — Safety and architecture

Show the architecture diagram in the README.

“The browser receives a single-use AssemblyAI token, never the API key. Mutations use prepare-then-confirm and idempotent pending actions. Existing expense and dashboard services are reused.”

## 2:25–2:40 — Close

“BizExpense Voice turns a stable expense-management MVP into a hands-free workflow without rebuilding its accounting foundation.”
