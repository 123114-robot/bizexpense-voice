import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text


POSTGRES_TEST_DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="POSTGRES_TEST_DATABASE_URL is only configured in CI",
)
def test_postgres_migrated_schema_accepts_core_records():
    engine = create_engine(POSTGRES_TEST_DATABASE_URL)
    try:
        assert engine.dialect.name == "postgresql"
        tables = set(inspect(engine).get_table_names())
        assert {
            "users",
            "expenses",
            "suppliers",
            "expense_categories",
            "uploaded_documents",
            "refresh_tokens",
        } <= tables

        with engine.connect() as connection:
            transaction = connection.begin()
            email = f"postgres-smoke-{uuid4().hex}@example.com"
            user_id = connection.scalar(
                text(
                    "INSERT INTO users (name, email, password_hash, role) "
                    "VALUES (:name, :email, :password_hash, :role) RETURNING id"
                ),
                {
                    "name": "PostgreSQL Smoke",
                    "email": email,
                    "password_hash": "test-only-hash",
                    "role": "owner",
                },
            )
            assert isinstance(user_id, int)
            transaction.rollback()
    finally:
        engine.dispose()
