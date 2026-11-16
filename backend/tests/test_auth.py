from uuid import uuid4

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_login_and_me(client: TestClient, demo_headers: dict[str, str]):
    response = client.get("/api/auth/me", headers=demo_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "demo"


def test_invalid_login(client: TestClient):
    response = client.post(
        "/api/auth/login", json={"username": "demo", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_register_creates_goal_and_knowledge_state(client: TestClient):
    username = f"user_{uuid4().hex[:8]}"
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "pass1234", "display_name": "测试同学"},
    )
    assert response.status_code == 201, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    goal = client.get("/api/goals/current", headers=headers)
    assert goal.status_code == 200
    assert goal.json()["days_remaining"] >= 0

    knowledge = client.get("/api/knowledge", headers=headers)
    assert knowledge.status_code == 200
    assert len(knowledge.json()) >= 6
