# Non-functional Requirements

- Maintainable: routes, services, repositories, schemas and models have separate responsibilities.
- Testable: provider and service boundaries permit deterministic tests; tests use an isolated database.
- Secure baseline: allow-listed MIME types/extensions/signatures, generated storage names, size limit, trusted hosts and no client-controlled paths.
- Identity baseline: passwords use salted PBKDF2 hashes, login errors do not reveal account existence, and production requires a configured JWT secret.
- Correct: decimal database columns and server-side validation protect amounts.
- Usable: responsive forms, explicit labels, error messages and confirmation state.
- Portable: environment-configured PostgreSQL and standard local commands.

Production must add migrations, secrets management, malware scanning, object storage, authentication, rate limits and observability.
