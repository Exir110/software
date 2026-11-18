from datetime import datetime

from ..core.clock import now_local
from ..models import UserKnowledge


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def trend_from_delta(delta: float, last_practiced_at: datetime | None = None) -> str:
    if last_practiced_at is not None and (now_local() - last_practiced_at).days > 14:
        return "steady"
    if delta > 1.5:
        return "up"
    if delta < -1.5:
        return "down"
    return "steady"


def apply_practice(
    state: UserKnowledge,
    correct_count: int,
    total_count: int,
    self_rating: int,
) -> float:
    """Accuracy- and sample-size-weighted update.

    自评只能小幅修正，不能抵消低正确率；题量越少，单次更新幅度越小。
    """
    old = state.mastery
    accuracy = correct_count / total_count if total_count else 0.0
    confidence = min(max(total_count, 1), 10) / 10.0
    rate = 0.08 + 0.22 * confidence
    delta = (accuracy * 100 - old) * rate + (self_rating - 3) * 0.8 * confidence

    if accuracy < 0.6:
        # 低于 60% 正确率不允许因自评而上涨
        delta = min(delta, -0.5)
    elif total_count >= 5 and accuracy >= 0.8:
        delta += 1.0

    delta = clamp(delta, -20.0, 20.0)
    state.previous_mastery = old
    state.mastery = clamp(old + delta)
    state.practice_count += 1
    state.correct_count += correct_count
    state.last_practiced_at = now_local()
    return round(state.mastery - old, 2)


def apply_task_completion(state: UserKnowledge, self_rating: int) -> float:
    """A completed task gives a small, capped gain; low self-rating can reduce it."""
    old = state.mastery
    if self_rating <= 2:
        delta = -1.0
    else:
        delta = clamp(0.5 + (self_rating - 3) * 0.7, -1.5, 1.5)

    state.previous_mastery = old
    state.mastery = clamp(old + delta)
    state.last_practiced_at = now_local()
    return round(state.mastery - old, 2)
