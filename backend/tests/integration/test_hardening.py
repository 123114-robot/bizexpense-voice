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


def test_untrusted_host_is_rejected(client):
    response = client.get("/api/health", headers={"Host": "attacker.example"})

    assert response.status_code == 400
