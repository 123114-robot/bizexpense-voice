# Testing Strategy

Backend unit tests cover schema business rules and OCR providers. Fast API integration tests cover CRUD, authentication, authorization, confirmation persistence and dashboard aggregation using isolated SQLite for fast local feedback. GitHub CI additionally starts PostgreSQL 17, applies every Alembic migration and runs a PostgreSQL-only schema/write smoke test.

Frontend tests cover form rendering, client validation, extracted field display and required confirmation. TypeScript build and lint provide static checks. Future work: upload integration tests, accessibility scans and Playwright browser workflows.

## Development and CI workflow

During normal development, run only tests and checks related to the files being changed. Before requesting review, run the relevant package-level suite once. GitHub Actions is the authoritative full regression gate for pull requests to `main` and pushes to `main`:

- Backend: install `requirements-dev.txt`, run Ruff, migrate a clean PostgreSQL service, then run the complete Pytest suite including the PostgreSQL smoke test.
- Frontend: run `npm ci`, ESLint, the complete Vitest suite, and `npm run build` (TypeScript checking plus the production Vite build).

No deployment workflow is configured because the project does not yet identify an actual deployment platform.

