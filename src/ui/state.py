"""Session state: who is signed in, where their history lives, and page routing.

Two modes:
* ``firebase``: a signed-in Firebase user; history is saved to Firestore.
* ``guest``: no account; history lives only in this browser session.

If Firestore can't be reached, new entries are kept in a session-only fallback list
(``offline_history``) and shown alongside the cloud history, and the UI says so.
"""
import streamlit as st

from src.firebase_client import FirebaseClient, FirebaseError, FirebaseUser, load_firebase_config
from src.storage import FirestoreHistoryStore, SessionHistoryStore

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
        "offline_history": [],      # signed-in entries kept locally while Firestore is unreachable
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
    """The signed-in user, refreshing the 1-hour ID token when needed."""
    user: FirebaseUser = st.session_state.user
    if user.expired:
        try:
            user = get_firebase_client().refresh(user)
            st.session_state.user = user
        except FirebaseError:
            logout()
            st.rerun()
    return user


def history_store():
    if is_guest():
        return SessionHistoryStore(st.session_state.guest_history)
    return FirestoreHistoryStore(get_firebase_client(), _fresh_user)


def load_history() -> tuple[list[dict], str | None]:
    """(entries newest first, notice or None). Never raises into the UI.

    If Firestore is unavailable, returns the entries kept locally this session plus a notice.
    """
    offline = SessionHistoryStore(st.session_state.offline_history)
    try:
        entries = history_store().list()
    except FirebaseError as err:
        return offline.list(), f"Couldn't reach your cloud history ({err}). Showing entries from this session only."
    if offline.list():
        entries = sorted(entries + offline.list(), key=lambda e: e.get("timestamp", ""), reverse=True)
    return entries, None


def save_entry(entry: dict) -> str | None:
    """Save an entry; returns an error message, or None on success.

    An entry that can't reach Firestore is kept for this session instead (and the user is told).
    """
    try:
        history_store().add(entry)
        return None
    except FirebaseError:
        SessionHistoryStore(st.session_state.offline_history).add(entry)
        st.toast("Cloud sync unavailable — saved for this session only.", icon=":material/cloud_off:")
        return None


def delete_entry(entry_id: str) -> None:
    offline = SessionHistoryStore(st.session_state.offline_history)
    if any(e["id"] == entry_id for e in offline.list()):
        offline.delete(entry_id)
    else:
        history_store().delete(entry_id)


def clear_history() -> None:
    st.session_state.offline_history.clear()
    history_store().clear()


def remember_face(face, source: str) -> None:
    """Keep the latest analysed face for the dashboard's 'Current emotion' card (this session only)."""
    st.session_state.last_face = {"emotion": face.emotion, "confidence": face.confidence,
                                  "probabilities": dict(face.probabilities), "top3": list(face.top3),
                                  "source": source}


def go(page_key: str) -> None:
    st.switch_page(PAGES[page_key])
