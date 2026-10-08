# Project Tasks

## Completed in this MVP

- [x] Phase 0: planning package, architecture, data model, API and test strategy
- [x] Phase 1: Vite/React/TypeScript/Tailwind and FastAPI/SQLAlchemy foundations
- [x] Phase 2: validated expense CRUD, supplier reuse, seeded user/categories and search
- [x] Phase 3: validated local document upload and stored metadata
- [x] Phase 4A: OCR provider abstraction and deterministic Mock provider
- [x] Phase 4B: Tesseract PNG/JPEG prototype and basic invoice field parser
- [ ] Phase 4C: validation against a representative real-invoice dataset
- [x] Phase 4D: parser hardening for common alternate invoice layouts
- [x] Phase 5 (mock workflow): editable review and explicit confirmation
- [x] Database-backed dashboard summary
- [x] Phase 6: confirmed-expense category breakdown and six-month trend
- [x] Phase 7: supplier/description, category, date and status filters with matching CSV export
- [x] Phase 8A: migration baseline, environment configuration, request IDs and security headers
- [x] Phase 8B: trusted-host enforcement and upload content/extension verification
- [x] Phase 8C1: registration, password hashing, JWT login and current-user API
- [x] Backend unit/integration tests and frontend critical-flow tests

## Intentionally deferred

- [ ] Production deployment configuration
- [x] Phase 8C2: enforce JWT authentication and per-user tenant isolation across business APIs
- [x] Phase 8C3: Web registration/login and shared authenticated API client
- [x] Phase 8C4: authenticated CSV download and manual sign-out
- [x] Phase 9: end-to-end demo smoke coverage and final build verification
- [x] Phase 10: runtime liveness and database readiness probes
- [x] Phase 11A: GitHub Actions full regression CI and documented targeted-test workflow
- [x] Phase 11B: configurable rate limits for authentication, uploads and OCR
- [x] Phase 11C1: rotating refresh-token API, hashed persistence and logout revocation
- [x] Phase 11C2: Web automatic refresh and server-side sign-out integration
- [x] Phase 11D: optional OpenAI-compatible Vision OCR with strict response validation
- [x] Phase 11E1: PostgreSQL migration and core-schema smoke coverage in GitHub CI
- [x] Phase 12: non-blocking duplicate expense warning using supplier, invoice number and total
- [x] Phase 13: authentication, tenant mutation and hardened-error security regression tests
- [x] Phase 14: Tesseract parser hardening for alternate labels and month-name dates
- [x] Phase 15: keyboard skip navigation, labelled landmarks and accessible form errors
- [x] Phase 16: first-page PDF rendering for local Tesseract OCR
- [x] Phase 17: average expense and tenant-scoped top-supplier dashboard insights
- [x] Phase 8D: deeper security regression coverage for high-risk API boundaries
- [ ] Multi-page PDF OCR, provider-derived field confidence and representative invoice validation
- [ ] Accounting-system export (dashboard analytics expanded in Phase 17)
- [ ] Object storage, malware scanning and document retention policy
- [ ] Browser E2E hardening (baseline accessibility improvements completed in Phase 15)
