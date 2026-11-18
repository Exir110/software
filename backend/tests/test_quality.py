from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.clock import today_local
from app.db.session import SessionLocal
from app.models import StudyTask, User


def _goal_payload(exam_date: str = "2026-12-19", daily_minutes: int = 180) -> dict:
    return {
        "exam_date": exam_date,
        "target_school": "目标院校",
        "target_major": "计算机相关专业",
        "target_score": 390,
        "daily_minutes": daily_minutes,
    }


def test_goal_rejects_past_date(client: TestClient, demo_headers: dict[str, str]):
    response = client.put(
        "/api/goals/current",
        headers=demo_headers,
        json=_goal_payload("2020-01-01"),
    )
    assert response.status_code == 400, response.text


def test_task_schedule_validation(client: TestClient, demo_headers: dict[str, str]):
    subjects = client.get("/api/subjects", headers=demo_headers).json()
    math = next(item for item in subjects if item["name"] == "数学")

    past = client.post(
        "/api/tasks",
        headers=demo_headers,
        json={
            "title": "过去日期任务",
            "subject_id": math["id"],
            "scheduled_date": "2020-01-01",
            "start_time": "09:00",
            "duration_minutes": 30,
        },
    )
    assert past.status_code == 400

    overlap = client.post(
        "/api/tasks",
        headers=demo_headers,
        json={
            "title": "冲突任务",
            "subject_id": math["id"],
            "start_time": "08:40",
            "duration_minutes": 10,
        },
    )
    assert overlap.status_code == 409

    midnight = client.post(
        "/api/tasks",
        headers=demo_headers,
        json={
            "title": "跨天任务",
            "subject_id": math["id"],
            "start_time": "23:50",
            "duration_minutes": 30,
        },
    )
    assert midnight.status_code == 400


def test_mastery_rating_cannot_override_low_accuracy(
    client: TestClient, demo_headers: dict[str, str]
):
    knowledge = client.get("/api/knowledge", headers=demo_headers).json()
    point = next(item for item in knowledge if item["name"] == "定积分")
    response = client.post(
        f"/api/knowledge/{point['id']}/practice",
        headers=demo_headers,
        json={
            "minutes": 10,
            "correct_count": 5,
            "total_count": 10,
            "self_rating": 5,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["delta"] <= -0.4


def test_ai_plan_preview_and_apply(client: TestClient, demo_headers: dict[str, str]):
    tasks = client.get("/api/tasks", headers=demo_headers).json()
    pending = next(item for item in tasks if item["status"] != "已完成")

    moved = client.patch(
        f"/api/tasks/{pending['id']}",
        headers=demo_headers,
        json={"start_time": "22:00"},
    )
    assert moved.status_code == 200, moved.text

    preview = client.post("/api/ai/plan?apply=false", headers=demo_headers)
    assert preview.status_code == 200, preview.text
    assert preview.json()["applied"] is False

    after_preview = client.get("/api/tasks", headers=demo_headers).json()
    unchanged = next(item for item in after_preview if item["id"] == pending["id"])
    assert unchanged["start_time"] == "22:00"

    applied = client.post("/api/ai/plan?apply=true", headers=demo_headers)
    assert applied.status_code == 200, applied.text
    assert applied.json()["applied"] is True

    after_apply = client.get("/api/tasks", headers=demo_headers).json()
    changed = next(item for item in after_apply if item["id"] == pending["id"])
    assert changed["start_time"] != "22:00"


def test_ai_plan_respects_daily_limit(client: TestClient, demo_headers: dict[str, str]):
    goal = client.put(
        "/api/goals/current",
        headers=demo_headers,
        json=_goal_payload(daily_minutes=30),
    )
    assert goal.status_code == 200, goal.text
    try:
        plan = client.post("/api/ai/plan?apply=false", headers=demo_headers)
        assert plan.status_code == 200, plan.text
        data = plan.json()
        scheduled = sum(item["duration_minutes"] for item in data["recommendations"])
        assert scheduled <= 30
        assert data["deferred"]
    finally:
        client.put(
            "/api/goals/current",
            headers=demo_headers,
            json=_goal_payload(daily_minutes=180),
        )


def test_weekly_goal_auto_progress_and_no_regeneration(
    client: TestClient, demo_headers: dict[str, str]
):
    knowledge = client.get("/api/knowledge", headers=demo_headers).json()
    point = next(item for item in knowledge if item["name"] == "定积分")
    created = client.post(
        "/api/plan/goals",
        headers=demo_headers,
        json={"title": f"完成「{point['name']}」专项练习", "target_minutes": 10},
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    practice = client.post(
        f"/api/knowledge/{point['id']}/practice",
        headers=demo_headers,
        json={
            "minutes": 10,
            "correct_count": 8,
            "total_count": 10,
            "self_rating": 4,
        },
    )
    assert practice.status_code == 200, practice.text

    plan = client.get("/api/plan", headers=demo_headers).json()
    goal = next(item for item in plan["week"]["goals"] if item["id"] == goal_id)
    assert goal["status"] == "已完成"
    assert goal["auto"] is True
    assert goal["progress"] >= 100

    for item in plan["week"]["goals"]:
        client.delete(f"/api/plan/goals/{item['id']}", headers=demo_headers)
    plan = client.get("/api/plan", headers=demo_headers).json()
    assert plan["week"]["goals"] == []


def test_overdue_list_and_carry_over(client: TestClient, demo_headers: dict[str, str]):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "demo"))
        task = StudyTask(
            user_id=user.id,
            subject_id=1,
            title="逾期测试任务",
            scheduled_date=today_local() - timedelta(days=2),
            start_time="09:00",
            duration_minutes=20,
            status="待开始",
            priority="中",
        )
        db.add(task)
        db.commit()
        task_id = task.id

    overdue = client.get("/api/tasks/overdue", headers=demo_headers)
    assert overdue.status_code == 200, overdue.text
    assert any(item["id"] == task_id for item in overdue.json())

    moved = client.post("/api/tasks/carry-over", headers=demo_headers)
    assert moved.status_code == 200, moved.text
    assert any(item["id"] == task_id for item in moved.json())
    assert all(item["scheduled_date"] == today_local().isoformat() for item in moved.json())

    client.delete(f"/api/tasks/{task_id}", headers=demo_headers)


def test_wrong_question_analyze_is_not_review(
    client: TestClient, demo_headers: dict[str, str]
):
    subjects = client.get("/api/subjects", headers=demo_headers).json()
    math = next(item for item in subjects if item["name"] == "数学")
    created = client.post(
        "/api/wrong-questions",
        headers=demo_headers,
        json={"title": "复习流程测试题", "subject_id": math["id"], "error_type": "概念混淆"},
    )
    question_id = created.json()["id"]

    analyzed = client.post(
        f"/api/wrong-questions/{question_id}/analyze", headers=demo_headers
    )
    assert analyzed.status_code == 200
    question = next(
        item
        for item in client.get("/api/wrong-questions", headers=demo_headers).json()
        if item["id"] == question_id
    )
    assert question["review_count"] == 0

    first = client.post(
        f"/api/wrong-questions/{question_id}/review", headers=demo_headers
    )
    assert first.status_code == 200, first.text
    assert first.json()["review_count"] == 1
    first_due = first.json()["next_review_at"]

    second = client.post(
        f"/api/wrong-questions/{question_id}/review", headers=demo_headers
    )
    assert second.status_code == 200
    assert second.json()["review_count"] == 2
    assert second.json()["next_review_at"] > first_due

    client.delete(f"/api/wrong-questions/{question_id}", headers=demo_headers)


def test_records_list_and_delete_rolls_back_mastery(
    client: TestClient, demo_headers: dict[str, str]
):
    knowledge = client.get("/api/knowledge", headers=demo_headers).json()
    point = next(item for item in knowledge if item["name"] == "唯物辩证法")
    before = point["mastery"]

    practice = client.post(
        f"/api/knowledge/{point['id']}/practice",
        headers=demo_headers,
        json={
            "minutes": 15,
            "correct_count": 0,
            "total_count": 10,
            "self_rating": 3,
        },
    )
    assert practice.status_code == 200, practice.text

    records = client.get("/api/records?limit=20", headers=demo_headers)
    assert records.status_code == 200, records.text
    record = next(
        item
        for item in records.json()
        if item["knowledge_point"] == "唯物辩证法" and item["minutes"] == 15
    )
    assert record["mastery_delta"] is not None

    deleted = client.delete(f"/api/records/{record['id']}", headers=demo_headers)
    assert deleted.status_code == 204

    after = next(
        item
        for item in client.get("/api/knowledge", headers=demo_headers).json()
        if item["name"] == "唯物辩证法"
    )
    assert abs(after["mastery"] - before) <= 0.2


def test_create_custom_knowledge_point(client: TestClient, demo_headers: dict[str, str]):
    subjects = client.get("/api/subjects", headers=demo_headers).json()
    math = next(item for item in subjects if item["name"] == "数学")
    created = client.post(
        "/api/knowledge",
        headers=demo_headers,
        json={
            "subject_id": math["id"],
            "name": "自定义知识点测试",
            "chapter": "测试章节",
            "importance": 4,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["mastery"] == 50.0
    names = [item["name"] for item in client.get("/api/knowledge", headers=demo_headers).json()]
    assert "自定义知识点测试" in names
