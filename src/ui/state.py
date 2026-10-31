"""Session state: who is signed in, where their history lives, and page routing.

Two modes:
* ``firebase``: a signed-in Firebase user; history is saved to Firestore.
* ``guest``: no account; history lives only in this browser session.

Firebase Authentication is required for accounts; Firestore is optional cloud sync. If it
can't be reached, entries are saved to a session-only fallback list (``offline_history``)
and the UI says so instead of failing (see the persistence section below).
"""
import logging
import time

import streamlit as st

from src.firebase_client import CloudStorageError, FirebaseClient, FirebaseError, FirebaseUser, load_firebase_config
from src.storage import FirestoreHistoryStore, SessionHistoryStore

log = logging.getLogger(__name__)

PAGES: dict = {}  # key -> st.Page, filled by app.py so views can navigate


@st.cache_resource(show_spinner=False)
def get_firebase_client() -> FirebaseClient | None:
    cfg = load_firebase_config()
    return FirebaseClient(cfg["api_key"], cfg["project_id"]) if cfg else None


def init() -> None:
    defaults = {
        "user": None,               # FirebaseUser or a guest dict
        "mode": None,               # "firebase" | "guest"
        "guest_history": [],        # guest-mode saved entries
        "offline_history": [],      # signed-in entries saved locally while Firestore is unavailable
        "cloud_retry_at": 0.0,      # after a Firestore failure, skip the cloud until this time
        "cloud_status": "unknown",  # "synced" | "unavailable" | "unknown" (sidebar badge)
        "session_predictions": [],  # webcam/image predictions this session (not saved)
        "faces_detected": 0,
        "activity": None,           # open wellbeing activity id
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def signed_in() -> bool:
    return st.session_state.get("mode") in ("firebase", "guest")


def is_guest() -> bool:
    return st.session_state.get("mode") == "guest"


def display_name() -> str:
    if is_guest():
        return "Guest"
    user: FirebaseUser = st.session_state.user
    return user.display_name or user.email.split("@")[0]


def email() -> str:
    return "" if is_guest() else st.session_state.user.email


def login(user: FirebaseUser) -> None:
    st.session_state.user, st.session_state.mode = user, "firebase"


def login_guest() -> None:
    st.session_state.user, st.session_state.mode = {"name": "Guest"}, "guest"


def logout() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]  # forget tokens, guest history and all page state
    init()


def _fresh_user() -> FirebaseUser:
    """The signed-in user, refreshing the 1-hour ID token when needed.

    A network failure keeps the current token (Firestore calls then fail and fall back to local
    storage); a rejected refresh token means the session is over, so the user is logged out.
    """
    user: FirebaseUser = st.session_state.user
    if user.expired:
        try:
            user = get_firebase_client().refresh(user)
            st.session_state.user = user
        except FirebaseError as err:
            if err.code == "NETWORK":
                return user
            logout()
            st.rerun()
    return user


# ---------------------------------------------------------------------------
# Persistence: the only place the UI saves, loads or deletes history.
#
# guest     -> SessionHistoryStore(guest_history)
# signed in -> FirestoreHistoryStore (cloud sync); if Firestore fails, the entry goes to
#              SessionHistoryStore(offline_history) instead, exactly once. Loads show
#              cloud + local entries, or only local entries while the cloud is unavailable.
# After a failure the cloud is skipped for CLOUD_RETRY_S, so pages don't wait for
# a timeout on every rerun.
# ---------------------------------------------------------------------------
CLOUD_RETRY_S = 60
SAVED_LOCALLY = "Saved locally — cloud sync unavailable."
LOCAL_HISTORY_NOTICE = "Cloud history is unavailable. Showing your locally saved entries."


def offline_history() -> list:
    """Entries saved locally while Firestore is unavailable (always initialised)."""
    if "offline_history" not in st.session_state:
        st.session_state["offline_history"] = []
    return st.session_state["offline_history"]


def _guest_store() -> SessionHistoryStore:
    return SessionHistoryStore(st.session_state.setdefault("guest_history", []))


def _local_store() -> SessionHistoryStore:
    return SessionHistoryStore(offline_history())


def history_store():
    """The primary store: guest session store, or Firestore for signed-in users."""
    if is_guest():
        return _guest_store()
    client = get_firebase_client()
    if client is None:
        raise CloudStorageError("Cloud storage isn't configured.", "NOT_CONFIGURED")
    return FirestoreHistoryStore(client, _fresh_user)


def cloud_available() -> bool:
    return time.time() >= st.session_state.get("cloud_retry_at", 0.0)


def cloud_status() -> str:
    """For the sidebar: "synced" (last cloud call worked), "unavailable", or "unknown" (not tried yet)."""
    return st.session_state.get("cloud_status", "unknown")


def _cloud_ok() -> None:
    st.session_state["cloud_status"] = "synced"


def _cloud_failed(err: Exception) -> None:
    log.warning("Firestore unavailable (%s); using local history for %ss",
                getattr(err, "code", "") or type(err).__name__, CLOUD_RETRY_S)
    st.session_state["cloud_retry_at"] = time.time() + CLOUD_RETRY_S
    st.session_state["cloud_status"] = "unavailable"


def load_history() -> tuple[list[dict], str | None]:
    """(entries newest first, notice or None). Never raises into the UI."""
    local = _local_store().list()
    if is_guest():
        return _guest_store().list(), None
    if cloud_available():
        try:
            cloud = history_store().list()
        except CloudStorageError as err:
            _cloud_failed(err)
        else:
            _cloud_ok()
            return sorted(cloud + local, key=lambda e: e.get("timestamp", ""), reverse=True), None
    return local, LOCAL_HISTORY_NOTICE


def save_entry(entry: dict) -> bool:
    """Save an entry exactly once. True: saved to the primary store; False: saved locally instead."""
    if is_guest():
        _guest_store().add(entry)
        return True
    if cloud_available():
        try:
            history_store().add(entry)
            _cloud_ok()
            return True
        except CloudStorageError as err:
            _cloud_failed(err)
    _local_store().add(entry)
    return False


def delete_entry(entry_id: str) -> bool:
    """Delete one entry. False if it is a cloud entry and the cloud is unavailable."""
    local = _local_store()
    if any(e["id"] == entry_id for e in local.list()):
        local.delete(entry_id)
        return True
    try:
        history_store().delete(entry_id)
        return True
    except CloudStorageError as err:
        _cloud_failed(err)
        return False


def clear_history() -> bool:
    """Delete everything. False if local entries were cleared but the cloud couldn't be reached."""
    _local_store().clear()
    try:
        history_store().clear()
        return True
    except CloudStorageError as err:
        _cloud_failed(err)
        return False


def remember_face(face, source: str) -> None:
    """Keep the latest analysed face for the dashboard's 'Current emotion' card (this session only)."""
    st.session_state.last_face = {"emotion": face.emotion, "confidence": face.confidence,
                                  "probabilities": dict(face.probabilities), "top3": list(face.top3),
                                  "source": source}


def go(page_key: str) -> None:
    st.switch_page(PAGES[page_key])
