# API Design

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness |
| POST | `/api/auth/register` | Create a user and issue access/refresh tokens |
| POST | `/api/auth/login` | Authenticate and issue access/refresh tokens |
| POST | `/api/auth/refresh` | Rotate a valid refresh token and issue a new token pair |
| POST | `/api/auth/logout` | Revoke a refresh token |
| GET | `/api/auth/me` | Return the authenticated user |
| GET/POST | `/api/expenses` | Search/list or create |
| GET/PUT/DELETE | `/api/expenses/{id}` | Read, replace or delete |
| POST | `/api/documents/upload` | Store supported document |
| POST | `/api/documents/{id}/extract` | Return mock OCR draft |
| GET | `/api/categories` | Seeded categories |
| GET | `/api/suppliers` | Known suppliers |
| GET | `/api/dashboard/summary` | Live aggregate KPIs |

Validation errors use FastAPI's 422 response; missing resources use 404; unsupported media uses 415; oversized uploads use 413. Expense money is serialized as decimal strings to preserve precision.
