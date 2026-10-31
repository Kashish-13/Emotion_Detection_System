"""Firestore is optional: signed-in users keep working (locally) when it is unavailable.

Each test signs in a user against an in-memory fake Firebase (tests/fakes.py) whose
Authentication always works and whose Firestore is either up or down.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import config
from src.ui import state
from tests.fakes import FakeFirebaseClient

JOURNAL_TEXT = "Today I worked on my project and felt productive."

# Signs in once, then runs the page named by st.session_state.view (or the snippet in st.session_state.code).
SCRIPT = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
import streamlit as st
from src.storage import new_entry
from src.ui import state, theme
from src.ui.views import checkin, dashboard, history, toolkit

state.init(); theme.inject_css()
if not state.signed_in():
    client = state.get_firebase_client()
    state.login(client.sign_up("user@example.com", "secret12", "User"))
view = st.session_state.get("view")
if view:
    {"checkin": checkin, "dashboard": dashboard, "history": history, "toolkit": toolkit}[view].render()
for code in st.session_state.pop("code", []):
    exec(code)
"""


@pytest.fixture
def firebase(monkeypatch):
    """A fake Firebase project; set ``firebase.firestore_down`` to simulate an unavailable Firestore."""
    monkeypatch.delenv(config.FIREBASE_API_KEY_ENV, raising=False)
    monkeypatch.delenv(config.FIREBASE_PROJECT_ID_ENV, raising=False)
    fake = FakeFirebaseClient()
    monkeypatch.setattr(state, "get_firebase_client", lambda: fake)
    return fake


def app(view: str | None = None, *code: str) -> AppTest:
    at = AppTest.from_string(SCRIPT, default_timeout=180)
    if view:
        at.session_state["view"] = view
    if code:
        at.session_state["code"] = list(code)
    return at.run()


def cloud_entries(fake: FakeFirebaseClient) -> list[dict]:
    return [d for user in fake.data.values() for d in user.get(config.HISTORY_COLLECTION, {}).values()]


def run_code(at: AppTest, *code: str) -> AppTest:
    at.session_state["code"] = list(code)
    return at.run()


def assert_clean(at: AppTest) -> None:
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


# --- session state ------------------------------------------------------------
def test_fresh_session_initialises_offline_history(monkeypatch):
    monkeypatch.setattr(state, "load_firebase_config", lambda: None)
    state.get_firebase_client.clear()
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=180).run()
    assert not at.exception
    assert at.session_state["offline_history"] == []
    state.get_firebase_client.clear()


def test_missing_offline_history_key_is_recreated_not_an_attribute_error(firebase):
    firebase.firestore_down = True
    at = app(None, "del st.session_state['offline_history']",
             "st.session_state.loaded = state.load_history()")
    assert_clean(at)
    assert at.session_state["loaded"] == ([], state.LOCAL_HISTORY_NOTICE)
    assert at.session_state["offline_history"] == []


# --- save -----------------------------------------------------------------------
SAVE = "st.session_state.result = state.save_entry(new_entry('checkin', selfReportedMood='Good'))"


def test_save_goes_to_firestore_without_a_local_copy(firebase):
    at = app(None, SAVE)
    assert at.session_state["result"] is True
    assert len(cloud_entries(firebase)) == 1
    assert at.session_state["offline_history"] == []


def test_failed_firestore_save_is_kept_locally_exactly_once(firebase):
    firebase.firestore_down = True
    at = app(None, SAVE)
    assert at.session_state["result"] is False
    assert cloud_entries(firebase) == []
    assert [e["selfReportedMood"] for e in at.session_state["offline_history"]] == ["Good"]
    at.run()  # plain reruns must not save again
    assert len(at.session_state["offline_history"]) == 1


def test_after_a_failure_the_cloud_is_skipped_briefly_then_retried(firebase):
    firebase.firestore_down = True
    at = app(None, SAVE)
    run_code(at, SAVE, "st.session_state.loaded = state.load_history()")
    assert firebase.firestore_calls == 1  # no repeated timeouts while the cloud is known to be down
    assert len(at.session_state["offline_history"]) == 2

    firebase.firestore_down = False
    run_code(at, "st.session_state.cloud_retry_at = 0", SAVE)  # retry window over, cloud is back
    assert at.session_state["result"] is True and len(cloud_entries(firebase)) == 1
    assert len(at.session_state["offline_history"]) == 2  # nothing duplicated


# --- load -------------------------------------------------------------------------
LOAD = "st.session_state.loaded = state.load_history()"


def test_load_history_from_firestore(firebase):
    at = app(None, SAVE, LOAD)
    entries, notice = at.session_state["loaded"]
    assert notice is None and [e["selfReportedMood"] for e in entries] == ["Good"]


def test_load_history_falls_back_to_empty_local_history(firebase):
    firebase.firestore_down = True
    entries, notice = app(None, LOAD).session_state["loaded"]
    assert entries == [] and notice == state.LOCAL_HISTORY_NOTICE


def test_load_history_falls_back_to_populated_local_history(firebase):
    firebase.firestore_down = True
    entries, notice = app(None, SAVE, SAVE, LOAD).session_state["loaded"]
    assert len(entries) == 2 and notice == state.LOCAL_HISTORY_NOTICE


def test_deleting_works_locally_and_reports_unreachable_cloud(firebase):
    at = app(None, SAVE)  # one cloud entry
    firebase.firestore_down = True
    run_code(at, SAVE, "st.session_state.local_id = st.session_state.offline_history[0]['id']")
    run_code(at, "st.session_state.deleted = state.delete_entry(st.session_state.local_id)",
             "st.session_state.cleared = state.clear_history()")
    assert at.session_state["deleted"] is True and at.session_state["offline_history"] == []
    assert at.session_state["cleared"] is False  # the cloud entry couldn't be reached
    assert_clean(at)


# --- pages, end to end ------------------------------------------------------------
@pytest.mark.parametrize("down", [False, True])
def test_journal_saves_and_appears_in_history(firebase, down):
    firebase.firestore_down = down
    at = AppTest.from_string(SCRIPT, default_timeout=180)
    at.session_state["view"], at.session_state["activity"] = "toolkit", "journaling"
    at.run()
    at.text_area(key="act_text").input(JOURNAL_TEXT)
    at.button(key="act_journal_save").click().run()  # typing and clicking in one step, like a real user
    assert_clean(at)
    messages = " ".join(s.value for s in at.success)
    assert "Journal saved" in messages
    assert ("Saved locally — cloud sync unavailable" in messages) is down
    assert len(at.session_state["offline_history"]) == (1 if down else 0)
    assert len(cloud_entries(firebase)) == (0 if down else 1)

    at.session_state["view"] = "history"
    at.run()
    assert_clean(at)
    table = at.dataframe[0].value
    assert list(table["Type"]) == ["Journal"]
    assert any(state.LOCAL_HISTORY_NOTICE in h.proto.body for h in at.html) is down


def test_empty_journal_is_not_saved(firebase):
    at = AppTest.from_string(SCRIPT, default_timeout=180)
    at.session_state["view"], at.session_state["activity"] = "toolkit", "journaling"
    at.run()
    at.button(key="act_journal_save").click().run()
    assert_clean(at)
    assert any("Write something first" in w.value for w in at.warning)
    assert at.session_state["offline_history"] == [] and cloud_entries(firebase) == []


@pytest.mark.parametrize("down", [False, True])
def test_daily_checkin_saves_and_appears_in_history(firebase, down):
    firebase.firestore_down = down
    at = app("checkin")
    at.pills(key="ci_mood").set_value("Good")
    at.pills(key="ci_factors").set_value(["College / Work"])
    at.text_area(key="ci_note").input("Finished a big part of my project.")
    at.form_submit_button[0].click().run()
    assert_clean(at)
    messages = " ".join(s.value for s in at.success)
    assert "Check-in saved" in messages
    assert ("Saved locally — cloud sync unavailable" in messages) is down

    at.session_state["view"] = "history"
    at.run()
    assert_clean(at)
    table = at.dataframe[0].value
    assert list(table["Self-reported mood"]) == ["Good"]


def test_history_page_without_firestore_shows_empty_state_not_a_traceback(firebase):
    firebase.firestore_down = True
    at = app("history")
    assert_clean(at)
    bodies = " ".join(h.proto.body for h in at.html)
    assert "No saved check-ins yet." in bodies and state.LOCAL_HISTORY_NOTICE in bodies
    assert "FirebaseError" not in bodies


@pytest.mark.parametrize("view", ["dashboard", "checkin", "toolkit", "history"])
def test_pages_render_without_firestore(firebase, view):
    firebase.firestore_down = True
    assert_clean(app(view))
