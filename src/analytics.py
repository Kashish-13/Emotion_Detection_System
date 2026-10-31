"""Session-level summary of facial-expression predictions.

The summary describes what the *model predicted* for the faces it saw in this
session. It is not a measurement of anyone's actual emotional or mental state.
"""
from collections import Counter

from src import config


def summarize_session(history: list[dict]) -> dict:
    """history: [{"emotion": str, "confidence": float, "source": str}, ...]"""
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
