def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_metrics_exposed(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text


def test_index_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "StoryCover" in resp.text
    assert "/api/generate" in resp.text
