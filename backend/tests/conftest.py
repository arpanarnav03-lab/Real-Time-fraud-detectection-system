"""Shared pytest fixtures for the backend test suite.

Tests run against the real app — and the real Neon Postgres configured via
DATABASE_URL — through FastAPI's TestClient. There's no separate test
database for this prototype, so any test that needs a user signs up with a
freshly generated, unique email rather than relying on fixed test data.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def make_email():
    def _make(prefix="pytest"):
        return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
    return _make


@pytest.fixture
def test_password():
    return "pytest-password-123"


@pytest.fixture
def auth_headers(client, make_email, test_password):
    """Signs up a fresh user and returns ready-to-use auth headers."""
    res = client.post("/auth/signup", json={"email": make_email(), "password": test_password})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
