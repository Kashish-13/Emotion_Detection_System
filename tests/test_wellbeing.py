"""Wellbeing content, history analytics, storage and non-diagnostic wording."""
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from src import config
from src.analytics import generate_insights, history_stats, streak_days
from src.predict import make_prediction
from src.storage import SessionHistoryStore, detection_entry, new_entry
from src.wellbeing import (ACTIVITIES, EMOTION_SUGGESTIONS, MOOD_SUGGESTIONS, MOODS, QUICK_RESETS,
                           TOOLKIT_ORDER, suggestions_for)

ROOT = Path(__file__).resolve().parent.parent


# --- content ----------------------------------------------------------------
def test_every_emotion_has_suggestions_and_every_link_points_to_a_real_activity():
    assert set(EMOTION_SUGGESTIONS) == set(config.EMOTIONS)
    for s in EMOTION_SUGGESTIONS.values():
        assert s["headline"] and s["items"]
        assert all(a is None or a in ACTIVITIES for _, a in s["items"])
    assert all(MOOD_SUGGESTIONS[m][1] in ACTIVITIES for m in MOODS)
    assert all(a in ACTIVITIES for a, _ in QUICK_RESETS)
    assert len(TOOLKIT_ORDER) == 8 and all(a in ACTIVITIES for a in TOOLKIT_ORDER)
    assert suggestions_for("Unknown") == EMOTION_SUGGESTIONS["Neutral"]


DIAGNOSTIC = re.compile(r"\byou(?:'re| are)\s+(?:feeling\s+)?(?:stressed|anxious|depressed|sad|angry|happy|afraid|"
                        r"scared|unwell|mentally ill)\b|\byou have (?:anxiety|depression|stress)\b|"
                        r"\bdiagnos(?:e|es|is) (?:your|you)\b", re.IGNORECASE)


def test_user_facing_text_never_diagnoses():
    files = [ROOT / "src" / "wellbeing.py", ROOT / "src" / "analytics.py", ROOT / "app.py",
             *(ROOT / "src" / "ui").rglob("*.py")]
    hits = [(f.name, m.group(0)) for f in files for m in DIAGNOSTIC.finditer(f.read_text(encoding="utf-8"))]
    assert hits == []


# --- storage ----------------------------------------------------------------
def test_new_entry_drops_empty_fields_and_validates_kind():
    e = new_entry("checkin", selfReportedMood="Low", moodFactors=[], journalText="")
    assert e["kind"] == "checkin" and e["selfReportedMood"] == "Low"
    assert "moodFactors" not in e and "journalText" not in e
    datetime.fromisoformat(e["timestamp"])
    with pytest.raises(ValueError):
        new_entry("image")


def test_detection_entry_stores_prediction_but_never_image_data():
    face = make_prediction(np.array([0.1, 0.01, 0.08, 0.7, 0.05, 0.04, 0.02]), box=(1, 2, 3, 4),
                           face_input=np.zeros((48, 48, 1)))
    e = detection_entry(face, "image", mood="Good")
    assert e["detectedEmotion"] == "Happy" and e["confidence"] == pytest.approx(0.7)
    assert [p["emotion"] for p in e["topPredictions"]] == ["Happy", "Angry", "Fear"]
    assert e["selfReportedMood"] == "Good"
    assert not {"face_input", "image", "box"} & set(e)


def test_session_store_add_list_delete_clear():
    backing = []
    store = SessionHistoryStore(backing)
    old = {**new_entry("checkin", selfReportedMood="Okay"), "timestamp": "2026-01-01T00:00:00+00:00"}
    first = store.add(old)
    store.add(new_entry("journal", prompt="p", journalText="t"))
    assert [e["kind"] for e in store.list()] == ["journal", "checkin"]  # newest first
    store.delete(first)
    assert len(store.list()) == 1
    store.clear()
    assert store.list() == [] and backing == []


# --- analytics ----------------------------------------------------------------
def _at(days_ago: int, **fields) -> dict:
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return {"timestamp": ts, **fields}


def test_streak_counts_consecutive_days_ending_today_or_yesterday():
    today = date(2026, 10, 31)
    d = lambda n: today - timedelta(days=n)  # noqa: E731
    assert streak_days({d(0), d(1), d(2)}, today) == 3
    assert streak_days({d(1), d(2)}, today) == 2          # today not done yet
    assert streak_days({d(0), d(2)}, today) == 1
    assert streak_days({d(3)}, today) == 0
    assert streak_days(set(), today) == 0


def test_history_stats():
    entries = [_at(0, kind="detection", detectedEmotion="Happy", confidence=0.9),
               _at(0, kind="checkin", selfReportedMood="Good"),
               _at(1, kind="detection", detectedEmotion="Happy", confidence=0.5),
               _at(1, kind="detection", detectedEmotion="Sad", confidence=0.4)]
    s = history_stats(entries)
    assert (s["total"], s["today"], s["streak"], s["detections"], s["mood_reports"]) == (4, 2, 2, 3, 1)
    assert s["dominant_expression"] == "Happy"
    assert s["average_confidence"] == pytest.approx(0.6)
    assert list(s["expression_counts"]) == config.EMOTIONS


def test_insights_are_labelled_and_rule_based():
    det = [_at(i, kind="detection", detectedEmotion="Neutral", confidence=0.3) for i in range(4)]
    moods = [_at(i, kind="checkin", selfReportedMood="Difficult") for i in range(3)]
    insights = generate_insights(det + moods)
    sources = {i["source"] for i in insights}
    assert sources <= {"Model signal", "Self-reported mood", "Tip"}
    texts = " ".join(i["text"] for i in insights)
    assert "Neutral has appeared in 4 of your last 4" in texts
    assert "low model confidence" in texts
    assert "talk with someone you trust" in texts
    assert generate_insights([]) == []
