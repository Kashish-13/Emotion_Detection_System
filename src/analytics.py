"""Summaries and simple rule-based insights.

Two kinds of signal are kept strictly apart:

* **Model signal**: facial expressions the model detected (``kind == "detection"``).
* **Self-reported mood**: what the user told us in a daily check-in.

Neither is a measurement of anyone's actual emotional or mental state, and no
insight here is a diagnosis. Insights only describe patterns in the user's own data.
"""
from collections import Counter
from datetime import date, datetime, timedelta

from src import config
from src.wellbeing import MOOD_SCORE


def summarize_session(history: list[dict]) -> dict:
    """Webcam/image session summary. history: [{"emotion", "confidence", "source"}, ...]"""
    counts = Counter(entry["emotion"] for entry in history)
    total = len(history)
    return {
        "predictions": total,
        "counts": {e: counts.get(e, 0) for e in config.EMOTIONS},
        "dominant": counts.most_common(1)[0][0] if total else None,
        "average_confidence": sum(e["confidence"] for e in history) / total if total else None,
        "low_confidence_share": sum(e["confidence"] < config.MODERATE_CONFIDENCE for e in history) / total
        if total else None,
    }


# ---------------------------------------------------------------------------
# Saved history (entries from src.storage)
# ---------------------------------------------------------------------------
def local_time(entry: dict) -> datetime:
    """Entry timestamp (stored in UTC) converted to the local timezone."""
    return datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")).astimezone()


def detections(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e.get("kind") == "detection" and e.get("detectedEmotion")]


def mood_reports(entries: list[dict]) -> list[dict]:
    """Every entry where the user reported a mood (a check-in, or a saved detection with a mood)."""
    return [e for e in entries if e.get("selfReportedMood") in MOOD_SCORE]


def streak_days(days: set[date], today: date) -> int:
    """Consecutive days with at least one entry, ending today (or yesterday, so a streak
    isn't 'lost' just because today's check-in hasn't happened yet)."""
    start = today if today in days else today - timedelta(days=1)
    streak = 0
    while start - timedelta(days=streak) in days:
        streak += 1
    return streak


def history_stats(entries: list[dict], today: date | None = None) -> dict:
    today = today or datetime.now().astimezone().date()
    days = {local_time(e).date() for e in entries}
    det = detections(entries)
    counts = Counter(e["detectedEmotion"] for e in det)
    return {
        "total": len(entries),
        "today": sum(local_time(e).date() == today for e in entries),
        "streak": streak_days(days, today),
        "detections": len(det),
        "mood_reports": len(mood_reports(entries)),
        "dominant_expression": counts.most_common(1)[0][0] if det else None,
        "average_confidence": sum(e["confidence"] for e in det) / len(det) if det else None,
        "expression_counts": {e: counts.get(e, 0) for e in config.EMOTIONS},
    }


def filter_since(entries: list[dict], days: int | None) -> list[dict]:
    if not days:
        return entries
    cutoff = datetime.now().astimezone() - timedelta(days=days)
    return [e for e in entries if local_time(e) >= cutoff]


def generate_insights(entries: list[dict], recent: int = 10) -> list[dict]:
    """Rule-based observations about the user's own history.

    Returns [{"source": "Model signal" | "Self-reported mood" | "Tip", "text": str}].
    Entries are expected newest first (as returned by the history stores).
    """
    insights = []
    det = detections(entries)[:recent]
    if len(det) >= 3:
        counts = Counter(e["detectedEmotion"] for e in det)
        top, n = counts.most_common(1)[0]
        if n / len(det) >= 0.5:
            insights.append({"source": "Model signal",
                             "text": f"{top} has appeared in {n} of your last {len(det)} saved detections."})
            if top == "Neutral":
                insights.append({"source": "Tip", "text": (
                    "Your recent predictions have mostly been Neutral. A facial expression often doesn't show "
                    "how you feel — the daily check-in lets you note that in your own words.")})
        low = sum(e["confidence"] < config.MODERATE_CONFIDENCE for e in det)
        if low / len(det) >= 0.4:
            insights.append({"source": "Tip", "text": (
                f"{low} of your last {len(det)} detections had low model confidence. Better lighting and a "
                "front-facing image usually give the model a clearer view.")})

    moods = mood_reports(entries)[:recent]
    if len(moods) >= 3:
        counts = Counter(e["selfReportedMood"] for e in moods)
        top, n = counts.most_common(1)[0]
        insights.append({"source": "Self-reported mood",
                         "text": f"You've most often described your mood as “{top}” ({n} of your last {len(moods)} check-ins)."})
        hard = sum(MOOD_SCORE[e["selfReportedMood"]] <= 2 for e in moods[:5])
        if hard >= 3:
            insights.append({"source": "Self-reported mood", "text": (
                "You've reported feeling low or finding things difficult several times recently. It may help to "
                "talk with someone you trust, or try one of the wellbeing activities.")})

    paired = [e for e in det if e.get("selfReportedMood")]
    if len(paired) >= 3:
        insights.append({"source": "Tip", "text": (
            "When you save a detection together with your own mood, compare them: the model reads expressions, "
            "and expressions and feelings often differ.")})
    return insights
