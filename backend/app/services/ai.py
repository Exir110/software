import json
from datetime import datetime

import httpx

from ..core.config import settings
from ..core.clock import now_local
from ..models import WrongQuestion


def effective_provider() -> str:
    return "openai" if settings.ai_provider == "openai" and settings.openai_api_key else "local"

async def _chat(system: str, user: str, max_tokens: int = 500) -> str | None:
    if effective_provider() != "openai":
        return None
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.4,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return None


async def explain_plan(weak_points: list[str], minutes: int) -> tuple[str, str]:
    local = (
        f"今天建议优先复习{'、'.join(weak_points[:2]) or '薄弱知识点'}。"
        f"按掌握度、知识点重要度和剩余备考时间排序，预计投入 {minutes} 分钟。"
    )
    text = await _chat(
        "你是考研学习规划助手。请用中文给出两句话以内的计划说明，指出优先复习原因，不要编造数据。",
        f"薄弱知识点：{weak_points}；计划学习时长：{minutes} 分钟。",
        180,
    )
    return (text or local, "openai" if text else "local")


async def analyze_wrong_question(
    question: WrongQuestion,
    knowledge_name: str,
    mastery: float | None,
) -> tuple[str, list[str], str]:
    error = question.error_type or "未标注错误类型"
    mastery_text = f"当前掌握度约 {mastery:.0f}%" if mastery is not None else "尚未建立掌握度记录"
    local_analysis = (
        f"这道题被标记为「{error}」，关联知识点为「{knowledge_name}」，{mastery_text}。"
        "建议先复述解题入口，再对照标准答案定位第一处偏离，避免只记住最终结论。"
    )
    suggestions = [
        "回到知识点定义和一道基础例题，确认概念边界",
        "把本题拆成已知条件、目标、关键步骤三部分重做一遍",
        "三天后做一道同类型变式题，检查是否真正掌握",
    ]
    text = await _chat(
        "你是考研错题分析助手。输出 JSON：{\"analysis\":\"两句话分析\",\"suggestions\":[\"建议1\",\"建议2\",\"建议3\"]}。只输出 JSON。",
        f"题目：{question.title}\n知识点：{knowledge_name}\n错误类型：{error}\n掌握情况：{mastery_text}",
        500,
    )
    if text:
        try:
            parsed = json.loads(text)
            analysis = str(parsed.get("analysis", local_analysis))
            items = [str(item) for item in parsed.get("suggestions", [])][:3]
            if items:
                return analysis, items, "openai"
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
    return local_analysis, suggestions, "local"


async def daily_summary(
    completed: int,
    total: int,
    minutes: int,
    weak_points: list[str],
) -> tuple[str, str]:
    local = (
        f"今天完成 {completed}/{total} 个任务，学习 {minutes} 分钟。"
        f"下一步优先复习{'、'.join(weak_points[:2]) or '薄弱知识点'}，并安排一次短时回顾。"
    )
    text = await _chat(
        "你是考研学习总结助手。用中文写三句话以内的总结，必须基于给定数据，不要虚构。",
        f"完成任务 {completed}/{total}，学习 {minutes} 分钟，薄弱知识点：{weak_points}。",
        220,
    )
    return (text or local, "openai" if text else "local")


def now_iso() -> datetime:
    return now_local()

