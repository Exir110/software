from fastapi.testclient import TestClient


def test_complete_task_updates_record_and_mastery(
    client: TestClient, demo_headers: dict[str, str]
):
    knowledge_before = client.get("/api/knowledge", headers=demo_headers).json()
    target = next(item for item in knowledge_before if item["name"] == "矩阵秩")

    task = client.post(
        "/api/tasks",
        headers=demo_headers,
        json={
            "title": "矩阵秩专项练习",
            "subject_id": target["subject_id"],
            "knowledge_point_id": target["id"],
            "start_time": "20:00",
            "duration_minutes": 30,
        },
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]

    completed = client.post(
        f"/api/tasks/{task_id}/complete",
        headers=demo_headers,
        json={
            "minutes": 30,
            "correct_count": 9,
            "total_count": 10,
            "self_rating": 4,
        },
    )
    assert completed.status_code == 200, completed.text
    result = completed.json()
    assert result["task"]["status"] == "已完成"
    assert result["record_id"] > 0
    assert result["knowledge"]["mastery"] > target["mastery"]
    assert result["delta"] > 0

    duplicate = client.post(
        f"/api/tasks/{task_id}/complete", headers=demo_headers, json={}
    )
    assert duplicate.status_code == 409


def test_practice_endpoint(client: TestClient, demo_headers: dict[str, str]):
    knowledge = client.get("/api/knowledge", headers=demo_headers).json()
    point = next(item for item in knowledge if item["name"] == "定积分")
    response = client.post(
        f"/api/knowledge/{point['id']}/practice",
        headers=demo_headers,
        json={
            "minutes": 20,
            "correct_count": 8,
            "total_count": 10,
            "self_rating": 4,
            "note": "接口测试练习",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["delta"] != 0


def test_task_patch_and_start(client: TestClient, demo_headers: dict[str, str]):
    knowledge = client.get("/api/knowledge", headers=demo_headers).json()
    point = knowledge[0]
    created = client.post(
        "/api/tasks",
        headers=demo_headers,
        json={
            "title": "待修改任务",
            "subject_id": point["subject_id"],
            "knowledge_point_id": point["id"],
            "start_time": "11:00",
        },
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    updated = client.patch(
        f"/api/tasks/{task_id}",
        headers=demo_headers,
        json={"title": "已修改任务", "start_time": "7:05", "duration_minutes": 25},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "已修改任务"
    assert updated.json()["start_time"] == "07:05"

    started = client.post(f"/api/tasks/{task_id}/start", headers=demo_headers)
    assert started.status_code == 200
    assert started.json()["status"] == "进行中"


def test_ai_plan_and_wrong_analysis(client: TestClient, demo_headers: dict[str, str]):
    plan = client.post("/api/ai/plan", headers=demo_headers)
    assert plan.status_code == 200, plan.text
    data = plan.json()
    assert data["provider"] in {"local", "openai"}
    assert data["applied"] is True
    assert isinstance(data["recommendations"], list)

    questions = client.get("/api/wrong-questions", headers=demo_headers)
    assert questions.status_code == 200
    question = questions.json()[0]
    analysis = client.post(
        f"/api/wrong-questions/{question['id']}/analyze", headers=demo_headers
    )
    assert analysis.status_code == 200, analysis.text
    assert analysis.json()["suggestions"]
    assert analysis.json()["provider"] in {"local", "openai"}

