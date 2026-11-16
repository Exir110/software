import os

import pytest

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SEED_DEMO"] = "true"
os.environ["AI_PROVIDER"] = "local"
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes!"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def demo_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"username": "demo", "password": "demo1234"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
