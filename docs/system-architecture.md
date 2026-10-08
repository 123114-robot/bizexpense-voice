# System Architecture

```text
React UI → typed fetch services → FastAPI routes → domain services → repositories → SQLAlchemy → PostgreSQL
                                      ↓
                              DocumentService → OCRProvider
```

Routes translate HTTP requests and responses. Pydantic schemas validate boundary data. Services coordinate rules and use cases. Repositories isolate expense persistence. SQLAlchemy models own relationships. `OCRProvider` is implemented by deterministic Mock, local Tesseract and optional OpenAI-compatible Vision providers, selected through environment configuration without changing route logic.

Uploads are local for development. This is a deliberate MVP limitation, not a production storage design.
