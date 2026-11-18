from fastapi.testclient import TestClient


def test_plan_shape_and_phases(client: TestClient, demo_headers: dict[str, str]):
    response = client.get("/api/plan", headers=demo_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["exam_date"]
    assert [phase["name"] for phase in data["phases"]] == [
        "基础阶段",
        "强化阶段",
        "冲刺阶段",
        "模考阶段",
    ]
    assert sum(1 for phase in data["phases"] if phase["status"] == "current") <= 1
    assert data["week"]["goals"]
    assert 0 <= data["week"]["completion_rate"] <= 100
    assert data["insight"]


def test_weekly_goal_crud(client: TestClient, demo_headers: dict[str, str]):
    created = client.post(
        "/api/plan/goals",
        headers=demo_headers,
        json={"title": "测试周目标", "target_minutes": 90},
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    updated = client.patch(
        f"/api/plan/goals/{goal_id}", headers=demo_headers, json={"status": "已完成"}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "已完成"

    plan = client.get("/api/plan", headers=demo_headers).json()
    assert any(goal["id"] == goal_id for goal in plan["week"]["goals"])

    deleted = client.delete(f"/api/plan/goals/{goal_id}", headers=demo_headers)
    assert deleted.status_code == 204
    plan = client.get("/api/plan", headers=demo_headers).json()
    assert all(goal["id"] != goal_id for goal in plan["week"]["goals"])


def test_task_can_change_subject_and_point(
    client: TestClient, demo_headers: dict[str, str]
):
    knowledge = client.get("/api/knowledge", headers=demo_headers).json()
    matrix = next(item for item in knowledge if item["name"] == "矩阵秩")
    english_point = next(item for item in knowledge if item["subject"] == "英语")
    assert matrix["subject_id"] != english_point["subject_id"]

    created = client.post(
        "/api/tasks",
        headers=demo_headers,
        json={
            "title": "换绑知识点任务",
            "subject_id": matrix["subject_id"],
            "knowledge_point_id": matrix["id"],
            "start_time": "21:30",
        },
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]

    patched = client.patch(
        f"/api/tasks/{task_id}",
        headers=demo_headers,
        json={
            "subject_id": english_point["subject_id"],
            "knowledge_point_id": english_point["id"],
            "priority": "高",
        },
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["subject"] == "英语"
    assert body["knowledge_point"] == english_point["name"]

    bad = client.patch(
        f"/api/tasks/{task_id}",
        headers=demo_headers,
        json={"knowledge_point_id": matrix["id"]},
    )
    assert bad.status_code == 400

    client.delete(f"/api/tasks/{task_id}", headers=demo_headers)


def test_wrong_question_create_and_delete(
    client: TestClient, demo_headers: dict[str, str]
):
    subjects = client.get("/api/subjects", headers=demo_headers).json()
    math = next(item for item in subjects if item["name"] == "数学")
    created = client.post(
        "/api/wrong-questions",
        headers=demo_headers,
        json={
            "title": "临时错题：极限存在性判断",
            "subject_id": math["id"],
            "error_type": "概念混淆",
        },
    )
    assert created.status_code == 201, created.text
    question_id = created.json()["id"]

    deleted = client.delete(f"/api/wrong-questions/{question_id}", headers=demo_headers)
    assert deleted.status_code == 204
    remaining = client.get("/api/wrong-questions", headers=demo_headers).json()
    assert all(item["id"] != question_id for item in remaining)


