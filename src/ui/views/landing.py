"""Landing screen with login / sign-up / password reset (shown before sign-in)."""
import re

import streamlit as st

from src import config
from src.firebase_client import FirebaseError
from src.ui import state

FEATURES = ["AI facial-expression detection", "Live webcam analysis", "Personal insights",
            "Daily check-ins", "Wellbeing toolkit"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


STEPS = [
    ("1 · Detect", "Upload a photo, take a snapshot or use your webcam. The model finds each face and estimates "
                   "its expression, with confidence and top-3 alternatives."),
    ("2 · Reflect", "Turn a result into a moment for yourself: a daily check-in in your own words, a journal "
                    "prompt, or a one-minute breathing reset."),
    ("3 · Notice patterns", "See your saved history over time, with the model's signal and your self-reported mood "
                            "kept clearly apart."),
]


def render() -> None:
    client = state.get_firebase_client()
    st.html('<div style="height:2.2rem"></div>')  # clear Streamlit's top bar
    left, _, right = st.columns([1.15, 0.12, 1], vertical_alignment="center")

    with left:
        features = "".join(f'<div class="es-feature"><span class="es-check">✓</span>{f}</div>' for f in FEATURES)
        st.html(f"""
          <div class="es-brand">{config.APP_NAME}</div>
          <div class="es-landing-title">Understand your expressions.<br>Reflect on your wellbeing.</div>
          <p class="es-subtitle" style="max-width:34rem">A facial-expression recognition model (CNN trained on
          FER-2013) paired with daily check-ins, reflection and a small wellbeing toolkit, so a detected
          expression becomes a prompt to check in with yourself.</p>
          <div style="margin-top:1.2rem">{features}</div>
          <p class="es-muted es-small" style="margin-top:1.3rem;max-width:34rem">EmotionSense reads facial
          expressions only. It is not a medical or diagnostic tool and cannot tell how you actually feel.</p>""")

    with right:
        with st.container(border=True):
            if client is None:
                st.markdown("#### Welcome")
                st.info("Accounts are disabled because Firebase isn't configured. You can still try every "
                        "feature in guest mode — nothing is saved after you close the tab. "
                        "See the README section *Firebase setup* to enable accounts.", icon=":material/info:")
            else:
                mode = st.segmented_control("Account", ["Login", "Create account", "Forgot password"],
                                            default="Login", key="auth_mode", label_visibility="collapsed")
                if mode == "Create account":
                    _signup_form(client)
                elif mode == "Forgot password":
                    _reset_form(client)
                else:
                    _login_form(client)
                st.html('<div class="es-muted es-small" style="text-align:center;margin:.4rem 0">or</div>')
            if st.button("Continue as guest", icon=":material/person:", width="stretch", key="guest"):
                state.login_guest()
                st.rerun()
            st.caption("Guest mode keeps your history only for this browser session.")

    st.html('<div style="height:2.5rem"></div>')
    cards = "".join(f"""<div class="es-card"><div style="font-weight:750">{title}</div>
        <div class="es-muted es-small" style="margin-top:.35rem">{text}</div></div>""" for title, text in STEPS)
    st.html(f'<div class="es-grid" style="grid-template-columns:repeat(auto-fit,minmax(240px,1fr))">{cards}</div>')


def _valid(email: str, password: str | None = None) -> str | None:
    if not EMAIL_RE.match(email or ""):
        return "Please enter a valid email address."
    if password is not None and len(password) < 6:
        return "Passwords must be at least 6 characters."
    return None


def _login_form(client) -> None:
    with st.form("login", border=False):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", type="primary", width="stretch")
    if submitted:
        if problem := _valid(email.strip()):
            st.error(problem)
            return
        try:
            with st.spinner("Signing in…"):
                state.login(client.sign_in(email.strip(), password))
            st.rerun()
        except FirebaseError as err:
            st.error(str(err))


def _signup_form(client) -> None:
    with st.form("signup", border=False):
        name = st.text_input("Name", placeholder="What should we call you?", max_chars=40)
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", help="At least 6 characters.")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", type="primary", width="stretch")
    if submitted:
        if problem := _valid(email.strip(), password):
            st.error(problem)
            return
        if password != confirm:
            st.error("Passwords don't match.")
            return
        try:
            with st.spinner("Creating your account…"):
                state.login(client.sign_up(email.strip(), password, name.strip()))
            st.rerun()
        except FirebaseError as err:
            st.error(str(err))


def _reset_form(client) -> None:
    with st.form("reset", border=False):
        email = st.text_input("Email", placeholder="you@example.com")
        submitted = st.form_submit_button("Send reset link", type="primary", width="stretch")
    if submitted:
        if problem := _valid(email.strip()):
            st.error(problem)
            return
        try:
            client.send_password_reset(email.strip())
        except FirebaseError as err:
            if err.code not in ("EMAIL_NOT_FOUND",):  # don't reveal whether an account exists
                st.error(str(err))
                return
        st.success("If an account exists for that email, a password-reset link has been sent.")
