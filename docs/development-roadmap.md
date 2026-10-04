# Development Roadmap

| Phase | Goal and tasks | Acceptance criteria | Tests |
|---|---|---|---|
| 0 Planning | Requirements and design | Docs reviewed and consistent | Document review |
| 1 Base setup | React, FastAPI, DB wiring | Both apps start locally | Health/smoke checks |
| 2 CRUD | Models, validation, services, UI | Full expense lifecycle | Schema and API CRUD |
| 3 Upload | Validate and store documents | Supported files persist | Upload edge cases |
| 4 OCR | Add Tesseract implementation | Real fields extracted with confidence | Provider fixtures |
| 5 Review | Harden confirmation workflow | Unconfirmed OCR cannot be finalized accidentally | UI/API workflow |
| 6 Analytics | Trends and category summaries | Metrics reconcile to ledger | Aggregate tests |
| 7 Search/export | Filters and CSV export | Results/export match filters | Query/export tests |
| 8A Foundation | Environment configuration, migrations, request tracing and response hardening | Migration round-trip and security-header tests pass | Integration/migration tests |
| 8B Perimeter | Trusted hosts and upload content verification | Spoofed hosts/files are rejected | Security integration/unit tests |
| 8C1 Authentication | Registration, secure password storage and JWT identity | Register/login/me tests and migration checks pass | Auth integration tests |
| 8C2 Authorization | JWT enforcement and per-user tenant isolation across business APIs | Cross-tenant access is denied | API authorization tests |
| 8C3 Web auth | Registration/login UI and authenticated shared API client | Web flows send JWT and handle sign-out | UI/auth tests |
| 8D Security | Rate limits and deeper security review | Production readiness review passes | E2E/security/load |
| 9 Deploy/docs | CI/CD and operating guide | Repeatable deployment and support handoff | Deployment smoke test |

This run completes the prototype workflow through Phase 8C3. Business APIs require JWT and scope data to the authenticated user; the Web app provides registration/login, stores the token and attaches it to shared API calls. Rate limits and production hardening remain Phase 8D.
