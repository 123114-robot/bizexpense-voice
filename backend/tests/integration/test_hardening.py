from app.api.documents import ocr_rate_limit, upload_rate_limit


def test_responses_include_request_tracking_and_security_headers(client):
    response = client.get("/api/health", headers={"X-Request-ID": "review-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "review-123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_request_id_is_generated_when_missing(client):
    response = client.get("/api/health")

    assert response.headers["x-request-id"]
    assert len(response.headers["x-request-id"]) == 32


def test_invalid_request_id_is_replaced_and_error_responses_remain_hardened(client):
    supplied_id = "unsafe/request id"
    response = client.get(
        "/api/expenses", headers={"X-Request-ID": supplied_id}
    )

    assert response.status_code == 401
    assert response.headers["x-request-id"] != supplied_id
    assert len(response.headers["x-request-id"]) == 32
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_untrusted_host_is_rejected(client):
    response = client.get("/api/health", headers={"Host": "attacker.example"})

    assert response.status_code == 400


def test_document_upload_and_ocr_are_rate_limited(auth_client):
    original_upload_limit = upload_rate_limit.limit
    original_ocr_limit = ocr_rate_limit.limit
    upload_rate_limit.limit = 1
    ocr_rate_limit.limit = 1
    try:
        first_upload = auth_client.post(
            "/api/documents/upload",
            files={"file": ("invalid.txt", b"invalid", "text/plain")},
        )
        blocked_upload = auth_client.post(
            "/api/documents/upload",
            files={"file": ("invalid.txt", b"invalid", "text/plain")},
        )
        first_ocr = auth_client.post("/api/documents/999/extract")
        blocked_ocr = auth_client.post("/api/documents/999/extract")
    finally:
        upload_rate_limit.limit = original_upload_limit
        ocr_rate_limit.limit = original_ocr_limit

    assert first_upload.status_code == 415
    assert blocked_upload.status_code == 429
    assert first_ocr.status_code == 404
    assert blocked_ocr.status_code == 429
