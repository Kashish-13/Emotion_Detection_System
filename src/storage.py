"""History storage: one small interface, two backends.

* ``FirestoreHistoryStore``: signed-in users; entries live at users/{uid}/checkins.
* ``SessionHistoryStore``: guest mode; entries live only in this browser session
  (a plain list in st.session_state) and disappear when the tab is closed.

An entry is a flat dict. ``kind`` says what it is:
    detection  model prediction the user chose to save (no image is stored)
    checkin    self-reported mood (+ optional factors / note)
    journal    reflection-prompt answer
    reset      wellbeing activity + how the user felt afterwards
"""
import uuid
from datetime import datetime, timezone
from typing import Callable

from src import config
from src.firebase_client import FirebaseClient, FirebaseUser

KINDS = ("detection", "checkin", "journal", "reset")


def new_entry(kind: str, **fields) -> dict:
    """Build an entry with a UTC timestamp, dropping empty optional fields."""
    if kind not in KINDS:
        raise ValueError(f"Unknown entry kind: {kind}")
    entry = {"kind": kind, "timestamp": datetime.now(timezone.utc).isoformat()}
    entry.update({k: v for k, v in fields.items() if v not in (None, "", [], {})})
    return entry


def detection_entry(face, source: str, mood: str | None = None) -> dict:
    """Entry for a saved model prediction (FacePrediction from src.predict)."""
    return new_entry(
        "detection",
        source=source,
        detectedEmotion=face.emotion,
        confidence=round(float(face.confidence), 4),
        topPredictions=[{"emotion": e, "probability": round(float(p), 4)} for e, p in face.top3],
        selfReportedMood=mood,
    )


class SessionHistoryStore:
    """Guest mode: nothing leaves the browser session."""

    persistent = False

    def __init__(self, entries: list):
        self._entries = entries  # the caller owns the list (st.session_state)

    def add(self, entry: dict) -> str:
        entry = {**entry, "id": uuid.uuid4().hex}
        self._entries.append(entry)
        return entry["id"]

    def list(self) -> list[dict]:
        return sorted(self._entries, key=lambda e: e["timestamp"], reverse=True)

    def delete(self, entry_id: str) -> None:
        self._entries[:] = [e for e in self._entries if e["id"] != entry_id]

    def clear(self) -> None:
        self._entries.clear()


class FirestoreHistoryStore:
    """Signed-in users. ``get_user`` returns a fresh (non-expired) FirebaseUser."""

    persistent = True

    def __init__(self, client: FirebaseClient, get_user: Callable[[], FirebaseUser]):
        self.client = client
        self.get_user = get_user

    def add(self, entry: dict) -> str:
        user = self.get_user()
        return self.client.add_document(user, config.HISTORY_COLLECTION, {**entry, "userId": user.uid})

    def list(self) -> list[dict]:
        docs = self.client.list_documents(self.get_user(), config.HISTORY_COLLECTION)
        return sorted(docs, key=lambda e: e.get("timestamp", ""), reverse=True)

    def delete(self, entry_id: str) -> None:
        self.client.delete_document(self.get_user(), config.HISTORY_COLLECTION, entry_id)

    def clear(self) -> None:
        for entry in self.list():
            self.delete(entry["id"])
