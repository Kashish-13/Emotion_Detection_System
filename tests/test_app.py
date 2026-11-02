"""Headless tests of the Streamlit app (Streamlit's AppTest; no browser needed).

Firebase is replaced by an in-memory fake (tests/fakes.py). TensorFlow inference is
not run inside AppTest (it makes the pytest process stall at exit on Windows);
prediction itself is covered by tests/test_inference.py.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import config

PRELUDE = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
import streamlit as st
from src.ui import state, theme
"""

SEED_HISTORY = """
from datetime import datetime, timedelta, timezone
state.init(); theme.inject_css(); state.login_guest()
if not st.session_state.get("seeded"):
    st.session_state.seeded = True
    now = datetime.now(timezone.utc)
    for i, (emo, mood) in enumerate([("Happy", "Good"), ("Neutral", "Okay"), ("Sad", "Low"), ("Neutral", "Difficult")]):
        t = (now - timedelta(days=i)).isoformat()
        st.session_state.guest_history += [
            {"id": f"d{i}", "kind": "detection", "timestamp": t, "detectedEmotion": emo, "confidence": 0.35 + i / 10,
             "topPredictions": [{"emotion": emo, "probability": 0.35 + i / 10}], "source": "image"},
            {"id": f"c{i}", "kind": "checkin", "timestamp": t, "selfReportedMood": mood, "moodFactors": ["Sleep"]}]
    st.session_state.guest_history.append({"id": "j1", "kind": "journal", "timestamp": now.isoformat(),
                                           "prompt": "What went well today?", "journalText": "<b>escaped</b>"})
"""

FAKE_FIREBASE = """
sys.path.insert(0, str(Path.cwd() / "tests"))
from fakes import SHARED
state.get_firebase_client = lambda: SHARED
import app
app.main()
"""


@pytest.fixture(autouse=True)
def no_real_firebase(monkeypatch):
    """Never talk to a real Firebase project, even if a local .streamlit/secrets.toml exists."""
    from src.ui import state

    monkeypatch.delenv(config.FIREBASE_API_KEY_ENV, raising=False)
    monkeypatch.delenv(config.FIREBASE_PROJECT_ID_ENV, raising=False)
    monkeypatch.setattr(state, "load_firebase_config", lambda: None)
    real_client = state.get_firebase_client  # FAKE_FIREBASE replaces it; restored after each test
    monkeypatch.setattr(state, "get_firebase_client", real_client)
    real_client.clear()
    yield
    real_client.clear()


def run_page(view: str, seed: bool = True) -> AppTest:
    script = PRELUDE + (SEED_HISTORY if seed else "state.init(); state.login_guest()\n")
    script += f"from src.ui.views import {view}\n{view}.render()\n"
    return AppTest.from_string(script, default_timeout=180).run()


# --- landing / guest ---------------------------------------------------------
def test_landing_without_firebase_offers_guest_mode():
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=180).run()
    assert not at.exception
    assert any("Firebase isn't configured" in i.value for i in at.info)
    at.button(key="guest").click().run()
    assert not at.exception and at.session_state["mode"] == "guest"


def test_navigation_has_no_separate_webcam_page():
    from src.ui import state

    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=180).run()
    at.button(key="guest").click().run()
    assert not at.exception
    assert set(state.PAGES) == {"dashboard", "detect", "checkin", "wellbeing", "history", "support", "insights",
                                "about"}


@pytest.mark.parametrize("view", ["dashboard", "detect", "webcam", "checkin", "toolkit", "history",
                                  "support", "model_insights", "about"])
def test_every_page_renders_in_guest_mode(view):
    at = run_page(view)
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def test_professional_support_page():
    from src import support

    at = run_page("support", seed=False)
    assert not at.exception
    html = " ".join(h.proto.body for h in at.html)
    assert "Need immediate help?" in html and support.EMERGENCY_TEXT in html and "14416" in html
    assert any(support.MEDICAL_DISCLAIMER in i.value for i in at.info)
    assert any(support.EXTERNAL_NOTE in w.value for w in at.warning)
    assert at.selectbox(key="sp_type").options == ["All types", *support.PROFESSIONAL_TYPES]
    assert any("NIMHANS" in m.value for m in at.markdown)  # the verified directory entry
    at.text_input(key="sp_location").input("Mumbai").run()
    assert any("No verified listings match yet" in h.proto.body for h in at.html)
    at.text_input(key="sp_location").input("Bengaluru").run()
    at.selectbox(key="sp_type").select("Psychiatrist").run()
    assert not any("NIMHANS" in m.value for m in at.markdown)


def test_empty_dashboard_shows_journey_message():
    at = run_page("dashboard", seed=False)
    assert any("Your journey starts here." in h.proto.body for h in at.html)


def test_webcam_does_not_open_camera_until_started():
    at = run_page("webcam")
    assert at.button(key="cam_start").label == "Start camera"
    assert any("Camera is off" in h.proto.body for h in at.html)


# --- check-in, wellbeing, history ----------------------------------------------
def test_daily_checkin_saves_self_reported_mood_only():
    at = run_page("checkin", seed=False)
    at.pills(key="ci_mood").set_value("Low")
    at.pills(key="ci_factors").set_value(["Sleep", "Exams"])
    at.text_area(key="ci_note").input("Long day.")
    at.toggle(key="ci_keep").set_value(False)  # user chooses not to store the note
    at.form_submit_button[0].click().run()
    assert not at.exception
    saved = at.session_state["guest_history"][-1]
    assert saved["kind"] == "checkin" and saved["selfReportedMood"] == "Low"
    assert saved["moodFactors"] == ["Sleep", "Exams"] and "journalText" not in saved
    assert any("Check-in saved" in s.value for s in at.success)


def test_wellbeing_activity_and_reflection():
    at = run_page("toolkit", seed=False)
    at.button(key="start_grounding").click().run()
    assert at.session_state["activity"] == "grounding"
    at.button(key="g_next").click().run()
    assert at.session_state["grounding_step"] == 1
    at.pills(key="feel_grounding").set_value("Still difficult").run()
    assert any("mental-health professional" in i.value for i in at.info)
    at.button(key="save_feel_grounding").click().run()
    entry = at.session_state["guest_history"][-1]
    assert (entry["kind"], entry["activity"], entry["feelingAfter"]) == ("reset", "grounding", "Still difficult")


def test_history_insights_and_deletion():
    at = run_page("history")
    assert not at.exception
    assert any("es-tag" in h.proto.body and "Model signal" in h.proto.body for h in at.html)
    assert "&lt;b&gt;escaped&lt;/b&gt;" not in str(at.dataframe[0].value)  # table shows plain text
    before = len(at.session_state["guest_history"])
    at.button(key="del_one_btn").click().run()
    assert len(at.session_state["guest_history"]) == before - 1
    at.checkbox(key="del_all_ok").check().run()
    at.button(key="del_all_btn").click().run()
    assert at.session_state["guest_history"] == []


# --- authentication (fake Firebase) --------------------------------------------
def _form_input(at: AppTest, label: str, value: str) -> None:
    next(t for t in at.text_input if t.label == label).input(value)


def test_signup_logout_login_and_password_reset():
    at = AppTest.from_string(PRELUDE + FAKE_FIREBASE, default_timeout=180).run()
    assert not at.exception

    at.segmented_control(key="auth_mode").set_value("Create account").run()
    _form_input(at, "Name", "Kashish")
    _form_input(at, "Email", "kashish@example.com")
    _form_input(at, "Password", "secret12")
    _form_input(at, "Confirm password", "secret12")
    at.form_submit_button[0].click().run()
    assert not at.exception and at.session_state["mode"] == "firebase"
    assert at.session_state["user"].display_name == "Kashish"
    assert any("Good to see you, Kashish" in h.proto.body for h in at.html)

    at.button(key="logout").click().run()
    assert at.session_state["mode"] is None

    at.segmented_control(key="auth_mode").set_value("Login").run()
    _form_input(at, "Email", "kashish@example.com")
    _form_input(at, "Password", "wrong-password")
    at.form_submit_button[0].click().run()
    assert any("Incorrect email or password" in e.value for e in at.error)
    assert at.session_state["mode"] is None

    _form_input(at, "Password", "secret12")
    at.form_submit_button[0].click().run()
    assert at.session_state["mode"] == "firebase"

    at.button(key="logout").click().run()
    at.segmented_control(key="auth_mode").set_value("Forgot password").run()
    _form_input(at, "Email", "nobody@example.com")
    at.form_submit_button[0].click().run()  # same message whether or not the account exists
    assert any("If an account exists" in s.value for s in at.success)


def test_signup_validation_messages():
    at = AppTest.from_string(PRELUDE + FAKE_FIREBASE, default_timeout=180).run()
    at.segmented_control(key="auth_mode").set_value("Create account").run()
    _form_input(at, "Email", "not-an-email")
    _form_input(at, "Password", "secret12")
    at.form_submit_button[0].click().run()
    assert any("valid email" in e.value for e in at.error)
    _form_input(at, "Email", "ok@example.com")
    _form_input(at, "Confirm password", "different")
    at.form_submit_button[0].click().run()
    assert any("don't match" in e.value for e in at.error)
