"""Daily Check-In (self-reported mood) and Reflection Journal."""
import streamlit as st

from src.analytics import local_time
from src.storage import new_entry
from src.ui import components as ui
from src.ui import state
from src.wellbeing import DISTRESS_NOTE, JOURNAL_PROMPTS, MOOD_FACTORS, MOOD_SUGGESTIONS, MOODS


def render() -> None:
    ui.page_header("Daily check-in", "A minute to notice how you're doing, in your own words.", eyebrow="Reflect")
    checkin_tab, journal_tab = st.tabs(["Daily check-in", "Reflection journal"])
    with checkin_tab:
        _checkin()
    with journal_tab:
        _journal()


def _checkin() -> None:
    form_col, side_col = st.columns([1.5, 1], gap="large")
    with form_col:
        with st.form("daily_checkin", clear_on_submit=True, border=True):
            st.markdown("#### How are you feeling right now?")
            mood = st.pills("Mood", list(MOODS), format_func=lambda m: f"{MOODS[m]} {m}",
                            label_visibility="collapsed", key="ci_mood")
            st.markdown("#### What is affecting your mood today?")
            factors = st.pills("Factors", MOOD_FACTORS, selection_mode="multi", label_visibility="collapsed",
                               key="ci_factors")
            st.markdown("#### Anything you'd like to write?")
            text = st.text_area("Note", height=140, label_visibility="collapsed", key="ci_note",
                                placeholder="Optional — a few words about your day…")
            keep_note = st.toggle("Save my note with this check-in", value=True, key="ci_keep",
                                  help="Turn off to save only your mood and factors.")
            submitted = st.form_submit_button("Save check-in", type="primary", icon=":material/check:",
                                              width="stretch")
        if submitted:
            if not mood:
                st.warning("Pick how you're feeling to save a check-in.")
            else:
                entry = new_entry("checkin", selfReportedMood=mood, moodFactors=factors or [],
                                  journalText=text.strip() if keep_note else None)
                error = state.save_entry(entry)
                if error:
                    st.error(error)
                else:
                    st.session_state.last_checkin_mood = mood
                    st.success("Check-in saved. Thank you for taking a moment for yourself.",
                               icon=":material/check_circle:")

    with side_col:
        mood = st.session_state.get("last_checkin_mood")
        if mood:
            text, activity = MOOD_SUGGESTIONS[mood]
            st.markdown("##### A small next step")
            ui.suggestion_list([(text, activity)], key_prefix="ci_next", compact=True)
            if mood in ("Low", "Difficult"):
                st.info(DISTRESS_NOTE, icon=":material/favorite:")
        st.html("""<div class="es-card"><div class="es-stat-label">Your data</div><div class="es-small"
            style="margin-top:.3rem">Only your mood, the factors you pick, and (if you choose) your note are saved —
            privately, in your own account. This is self-reported and is never combined into a diagnosis.</div></div>""")


def _journal() -> None:
    write_col, past_col = st.columns([1.5, 1], gap="large")
    with write_col:
        with st.container(border=True):
            prompt = st.selectbox("Choose a prompt", JOURNAL_PROMPTS, key="j_prompt")
            text = st.text_area(prompt, height=200, key="j_text", placeholder="Write freely…",
                                label_visibility="collapsed")
            ui.journal_save_button(prompt, text, key="j_save")
            st.caption("Journal entries are private to your account.")
    with past_col:
        st.markdown("##### Recent reflections")
        entries, error = state.load_history()
        if error:
            st.error(error)
        journal = [e for e in entries if e.get("kind") == "journal"][:5]
        if not journal:
            st.caption("Your saved reflections will appear here.")
        for e in journal:
            with st.expander(f"{local_time(e):%d %b, %H:%M} · {e.get('prompt', 'Reflection')}"):
                st.text(e.get("journalText", ""))
