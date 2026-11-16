from datetime import datetime

from ..models import UserKnowledge


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def trend_from_delta(delta: float) -> str:
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
    """Update mastery with an accuracy-weighted exponential moving average."""
    old = state.mastery
    accuracy = correct_count / total_count if total_count else 0.0
    target = accuracy * 100
    delta = (target - old) * 0.35 + (self_rating - 3) * 2.0
    if total_count >= 5 and accuracy >= 0.8:
        delta += 1.5

    state.previous_mastery = old
    state.mastery = clamp(old + delta)
    state.practice_count += 1
    state.correct_count += correct_count
    state.last_practiced_at = datetime.now()
    return round(state.mastery - old, 2)


def apply_task_completion(state: UserKnowledge, self_rating: int) -> float:
    """A completed study task gives a smaller gain than a scored exercise."""
    old = state.mastery
    delta = 1.5 + (self_rating - 3) * 1.5
    state.previous_mastery = old
    state.mastery = clamp(old + delta)
    state.last_practiced_at = datetime.now()
    return round(state.mastery - old, 2)
