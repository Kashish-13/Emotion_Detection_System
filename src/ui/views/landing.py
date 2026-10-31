"""Landing screen: hero, scanner illustration, and login / sign-up / password reset."""
import re

import streamlit as st

from src import config
from src.firebase_client import FirebaseError
from src.ui import state

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

STEPS = [
    ("Analyze", "Upload a photo, take a snapshot or use your webcam. The model finds each face and estimates "
                "its expression, with confidence and the top-3 alternatives."),
    ("Reflect", "Turn a result into a moment for yourself: a daily check-in in your own words, a journal "
                "prompt, or a one-minute breathing reset."),
    ("Notice patterns", "See your saved history over time, with the model's signal and your self-reported mood "
                        "kept clearly apart."),
]

# Labels floating around the scanner illustration: (emotion, left %, top %, animation delay s).
# They name the seven classes the model knows; they are not results.
ORBIT = [("Happy", 4, 10, 0), ("Surprise", 70, 6, 1.2), ("Neutral", -2, 46, 2.4), ("Sad", 76, 40, .6),
         ("Angry", 6, 80, 1.8), ("Fear", 70, 76, 3), ("Disgust", 40, -1, 3.6)]

FACE_SVG = """<svg width="170" height="210" viewBox="0 0 170 210" fill="none" aria-hidden="true">
  <defs><linearGradient id="fg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a99ffb"/>
  <stop offset="1" stop-color="#38c6d9"/></linearGradient></defs>
  <path d="M85 12c-38 0-62 30-62 72 0 50 30 104 62 104s62-54 62-104c0-42-24-72-62-72z" stroke="url(#fg)"
        stroke-width="2.4" opacity=".9"/>
  <path d="M48 78c8-6 20-7 28-2M94 76c8-5 20-4 28 2" stroke="url(#fg)" stroke-width="2.4" stroke-linecap="round"/>
  <ellipse cx="62" cy="96" rx="9" ry="5.5" stroke="url(#fg)" stroke-width="2.2"/>
  <ellipse cx="108" cy="96" rx="9" ry="5.5" stroke="url(#fg)" stroke-width="2.2"/>
  <path d="M85 100v26l-8 6" stroke="url(#fg)" stroke-width="2" stroke-linecap="round" opacity=".8"/>
  <path d="M64 152c12 10 30 10 42 0" stroke="url(#fg)" stroke-width="2.6" stroke-linecap="round"/>
  <g fill="#38c6d9" opacity=".75"><circle cx="40" cy="60" r="1.6"/><circle cx="130" cy="60" r="1.6"/>
  <circle cx="34" cy="110" r="1.6"/><circle cx="136" cy="110" r="1.6"/><circle cx="56" cy="170" r="1.6"/>
  <circle cx="114" cy="170" r="1.6"/><circle cx="85" cy="40" r="1.6"/><circle cx="85" cy="190" r="1.6"/></g>
  <g stroke="#38c6d9" stroke-width=".8" opacity=".35"><path d="M40 60L62 96L85 40L108 96L130 60"/>
  <path d="M34 110L62 96L85 126L108 96L136 110"/><path d="M56 170L85 126L114 170"/></g>
</svg>"""


def _scanner() -> str:
    chips = "".join(
        f'<div class="es-orbit" style="--c:{config.EMOTION_COLORS[e]};left:{x}%;top:{y}%;'
        f'animation-delay:-{d}s">{config.EMOTION_EMOJI[e]} {e}</div>' for e, x, y, d in ORBIT)
    return f"""<div class="es-scan">
        <div class="es-scan-frame">{FACE_SVG}<div class="es-scan-line"></div>
          <i class="es-corner tl"></i><i class="es-corner tr"></i><i class="es-corner bl"></i><i class="es-corner br"></i>
        </div>{chips}
        <div class="es-scan-caption es-chip">✦ AI-powered facial expression analysis</div></div>"""


def render() -> None:
    client = state.get_firebase_client()
    st.html('<div style="height:1.2rem"></div><div class="es-brand"><i>◉</i>EmotionSense</div>')
    left, right = st.columns([1.1, 1], gap="large", vertical_alignment="center")

    with left:
        st.html("""<div class="es-eyebrow" style="margin-top:1.6rem">Facial expression AI · Wellbeing reflection</div>
          <div class="es-landing-title">Understand your emotions.<br>
          <span class="es-grad-text">Understand yourself.</span></div>
          <p class="es-lead">EmotionSense analyses the facial expression in a photo or webcam frame with a CNN trained
          on FER-2013, then offers general wellbeing reflections: check-ins, journaling and short resets.</p>""")
        a, b, _ = st.columns([1.25, 1.15, 0.4])
        if a.button("Analyze My Emotion", type="primary", icon=":material/center_focus_strong:", width="stretch",
                    key="cta_detect"):
            _start_guest("detect")
        if b.button("Explore Wellbeing", icon=":material/spa:", width="stretch", key="cta_wellbeing"):
            _start_guest("wellbeing")
        st.html("""<div class="es-chips" style="margin-top:.9rem">
            <span class="es-chip">🔒 Images never stored</span><span class="es-chip">🧠 7 expressions</span>
            <span class="es-chip">🌿 Not a diagnostic tool</span></div>""")
    with right:
        st.html(_scanner())

    st.html('<div style="height:2.2rem"></div>')
    how, auth = st.columns([1.1, 1], gap="large")
    with how:
        st.html('<div class="es-section" style="margin-top:0"><h3>How it works</h3>'
                '<p>Three small steps, from a photo to a moment of reflection.</p></div>')
        steps = "".join(f"""<div class="es-glass lift"><div class="es-step"><div class="es-step-n">{n}</div>
            <div><div style="font-weight:700">{title}</div><div class="es-muted es-small" style="margin-top:.25rem">
            {text}</div></div></div></div>""" for n, (title, text) in enumerate(STEPS, 1))
        st.html(steps)
        st.html('<p class="es-muted es-small" style="margin-top:1rem">EmotionSense reads facial expressions only. '
                'It is not a medical or diagnostic tool and cannot tell how you actually feel.</p>')

    with auth:
        with st.container(key="glass_auth"):
            st.markdown("#### Welcome to EmotionSense")
            if client is None:
                st.info("Accounts are disabled because Firebase isn't configured. You can still try every "
                        "feature in guest mode — nothing is saved after you close the tab. "
                        "See the README section *Firebase setup* to enable accounts.", icon=":material/info:")
            else:
                st.caption("Sign in to keep your check-ins and insights across sessions.")
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


def _start_guest(page: str) -> None:
    """Call-to-action: start a guest session and open ``page`` (sign-in stays available on this screen)."""
    state.login_guest()
    st.session_state.start_page = page
    st.rerun()


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
