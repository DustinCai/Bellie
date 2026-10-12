import pytest
from fastapi.testclient import TestClient

import main

HEADERS = {"x-api-key": "test-bellie-key"}
BODY = {"question": "How have I been feeling?"}


@pytest.fixture
def client(monkeypatch):
    # stub out the database + LLM calls so only the endpoint logic runs
    monkeypatch.setattr(main, "retrieve", lambda *args, **kwargs: [])
    monkeypatch.setattr(main, "generate", lambda question, entries: "stub answer")

    # rate limit counts live in memory, so clear them between tests
    main.limiter.reset()
    yield TestClient(main.app)
    main.limiter.reset()


def test_ask_allows_10_requests_per_minute(client):
    for _ in range(10):
        resp = client.post("/ask", json=BODY, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == {"answer": "stub answer"}


def test_ask_returns_429_after_limit_exceeded(client):
    for _ in range(10):
        client.post("/ask", json=BODY, headers=HEADERS)

    resp = client.post("/ask", json=BODY, headers=HEADERS)
    assert resp.status_code == 429


def test_rate_limit_does_not_apply_to_health(client):
    for _ in range(11):
        client.post("/ask", json=BODY, headers=HEADERS)

    resp = client.get("/health")
    assert resp.status_code == 200
