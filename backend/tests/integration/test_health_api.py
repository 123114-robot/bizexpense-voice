from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import readiness


def test_liveness_does_not_require_database(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_confirms_database_connection(client):
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_returns_safe_error_when_database_is_unavailable():
    class BrokenSession:
        def execute(self, _statement):
            raise SQLAlchemyError("database password should not leak")

    try:
        readiness(BrokenSession())
    except HTTPException as error:
        assert error.status_code == 503
        assert error.detail == "Database unavailable"
    else:
        raise AssertionError("Expected readiness to reject an unavailable database")
