from fastapi.testclient import TestClient


def test_dashboard_shape(client: TestClient, demo_headers: dict[str, str]):
    response = client.get("/api/dashboard", headers=demo_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["today_total"] >= 5
    assert data["today_completed"] >= 2
    assert data["today_minutes"] >= 80
    assert len(data["weekly"]) == 7
    assert len(data["weak_points"]) == 3
    assert data["days_to_exam"] >= 0
    assert data["tasks"][0]["category"]
