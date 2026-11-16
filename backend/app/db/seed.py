from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import hash_password
from ..models import (
    ExamGoal,
    KnowledgePoint,
    StudyRecord,
    StudyTask,
    Subject,
    User,
    UserKnowledge,
    WrongQuestion,
)


def next_exam_date(today: date) -> date:
    candidate = date(today.year, 12, 19)
    if candidate <= today:
        candidate = date(today.year + 1, 12, 19)
    return candidate


def seed_demo(db: Session) -> bool:
    if db.scalar(select(User).where(User.username == "demo")) is not None:
        return False

    today = date.today()
    user = User(
        username="demo",
        display_name="林同学",
        password_hash=hash_password("demo1234"),
    )
    db.add(user)
    db.flush()

    db.add(
        ExamGoal(
            user_id=user.id,
            exam_date=next_exam_date(today),
            target_school="目标院校",
            target_major="计算机相关专业",
            target_score=390,
            daily_minutes=180,
        )
    )

    subject_names = [("数学", "MATH"), ("英语", "ENG"), ("政治", "POL"), ("408", "408")]
    subjects: dict[str, Subject] = {}
    for name, code in subject_names:
        subject = Subject(name=name, code=code)
        db.add(subject)
        db.flush()
        subjects[name] = subject

    knowledge_specs = [
        ("数学", "高等数学", "定积分", 5, 4, 41, 46, 18, 10),
        ("数学", "线性代数", "矩阵秩", 5, 4, 36, 32, 15, 7),
        ("数学", "线性代数", "线性方程组", 4, 3, 52, 52, 24, 14),
        ("英语", "阅读理解", "长难句分析", 4, 3, 68, 64, 32, 22),
        ("408", "操作系统", "进程同步", 5, 4, 56, 52, 21, 12),
        ("政治", "马原", "唯物辩证法", 3, 2, 77, 75, 46, 36),
    ]
    points: dict[str, KnowledgePoint] = {}
    for subject_name, chapter, name, importance, difficulty, mastery, previous, practice, correct in knowledge_specs:
        point = KnowledgePoint(
            subject_id=subjects[subject_name].id,
            name=name,
            chapter=chapter,
            importance=importance,
            difficulty=difficulty,
        )
        db.add(point)
        db.flush()
        points[name] = point
        db.add(
            UserKnowledge(
                user_id=user.id,
                knowledge_point_id=point.id,
                mastery=mastery,
                previous_mastery=previous,
                practice_count=practice,
                correct_count=correct,
                last_practiced_at=datetime.combine(today - timedelta(days=1), time(20, 0)),
            )
        )

    task_specs = [
        ("定积分的几何意义", "数学", "定积分", "08:30", 45, "已完成", "高", "完成例题 1-8，整理换元积分步骤"),
        ("英语长难句精读", "英语", "长难句分析", "10:00", 35, "已完成", "中", "精读真题 2019 Text 2"),
        ("操作系统进程同步", "408", "进程同步", "14:00", 50, "进行中", "高", "完成信号量与管程对比"),
        ("线性代数错题回炉", "数学", "矩阵秩", "16:00", 40, "待开始", "高", "回顾秩与线性方程组判定"),
        ("政治选择题训练", "政治", "唯物辩证法", "19:30", 30, "待开始", "低", "完成肖 1000 第 4 章"),
    ]
    tasks: list[StudyTask] = []
    for title, subject_name, point_name, start_time, duration, status, priority, note in task_specs:
        point = points[point_name]
        task = StudyTask(
            user_id=user.id,
            subject_id=subjects[subject_name].id,
            knowledge_point_id=point.id,
            title=title,
            scheduled_date=today,
            start_time=start_time,
            duration_minutes=duration,
            status=status,
            priority=priority,
            note=note,
            completed_at=datetime.combine(today, time(9, 15)) if status == "已完成" else None,
        )
        db.add(task)
        tasks.append(task)
    db.flush()

    db.add_all(
        [
            StudyRecord(
                user_id=user.id,
                task_id=tasks[0].id,
                knowledge_point_id=tasks[0].knowledge_point_id,
                minutes=45,
                correct_count=12,
                total_count=15,
                self_rating=4,
                note="定积分例题练习",
                created_at=datetime.combine(today, time(9, 15)),
            ),
            StudyRecord(
                user_id=user.id,
                task_id=tasks[1].id,
                knowledge_point_id=tasks[1].knowledge_point_id,
                minutes=35,
                correct_count=8,
                total_count=10,
                self_rating=4,
                note="长难句精读",
                created_at=datetime.combine(today, time(10, 40)),
            ),
        ]
    )

    historical = [
        (1, 95, "线性方程组", 10, 15, 3),
        (2, 80, "进程同步", 12, 16, 4),
        (3, 60, "长难句分析", 6, 8, 3),
        (4, 120, "定积分", 9, 16, 3),
        (5, 45, "唯物辩证法", 10, 12, 4),
        (6, 30, "矩阵秩", 3, 10, 2),
    ]
    for days_ago, minutes, point_name, correct, total, rating in historical:
        db.add(
            StudyRecord(
                user_id=user.id,
                knowledge_point_id=points[point_name].id,
                minutes=minutes,
                correct_count=correct,
                total_count=total,
                self_rating=rating,
                note="历史学习记录",
                created_at=datetime.combine(today - timedelta(days=days_ago), time(20, 0)),
            )
        )

    wrong_specs = [
        ("二重积分换元后的积分区域判断", "数学", "定积分", "2019 真题", "区域边界识别错误"),
        ("PV 操作系统中的信号量取值", "408", "进程同步", "王道习题", "同步关系理解不完整"),
        ("考研英语真题 Text 3 第 27 题", "英语", "长难句分析", "2018 真题", "定位句与干扰项混淆"),
    ]
    for title, subject_name, point_name, source, error_type in wrong_specs:
        db.add(
            WrongQuestion(
                user_id=user.id,
                subject_id=subjects[subject_name].id,
                knowledge_point_id=points[point_name].id,
                title=title,
                source=source,
                error_type=error_type,
                next_review_at=datetime.combine(today + timedelta(days=2), time(19, 0)),
            )
        )

    db.commit()
    return True
