"""Daily Check-In (self-reported mood) and Reflection Journal."""
import streamlit as st

from src.analytics import local_time
from src.storage import new_entry
from src.ui import components as ui
from src.ui import state
from src.wellbeing import DISTRESS_NOTE, JOURNAL_PROMPTS, MOOD_FACTORS, MOOD_SUGGESTIONS, MOODS


def render() -> None:
    ui.page_header("How are you feeling", "A minute to notice how you're doing, in your own words.",
                   eyebrow="Reflect · Daily check-in", accent="right now?")
    checkin_tab, journal_tab = st.tabs(["Daily check-in", "Reflection journal"])
    with checkin_tab:
        _checkin()
    with journal_tab:
        _journal()


def _checkin() -> None:
    form_col, side_col = st.columns([1.6, 1], gap="large")
    with form_col:
        with st.form("daily_checkin", clear_on_submit=True, border=False):
            st.markdown("##### Pick the card that fits best")
            # Rendered as five large mood cards by the CSS for .st-key-ci_mood (src/ui/theme.py).
            # The line break puts the emoji above the word.
            mood = st.pills("Mood", list(MOODS), format_func=lambda m: f"{MOODS[m]}\n{m}",
                            label_visibility="collapsed", key="ci_mood")
            st.markdown("##### What has been affecting you today?")
            factors = st.pills("Factors", MOOD_FACTORS, selection_mode="multi", label_visibility="collapsed",
                               key="ci_factors")
            st.markdown("##### Want to put it into words?")
            text = st.text_area("Note", height=180, label_visibility="collapsed", key="ci_note",
                                placeholder="Optional — what's on your mind today?")
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
                saved_to_cloud = state.save_entry(entry)
                st.session_state.last_checkin_mood = mood
                ui.save_message(saved_to_cloud,
                                "**Check-in saved ✨**  \nTaking a minute to reflect is already a good step.")

    with side_col:
        mood = st.session_state.get("last_checkin_mood")
        if mood:
            text, activity = MOOD_SUGGESTIONS[mood]
            ui.section("A small next step", f"You checked in as {MOODS[mood]} {mood}.")
            with st.container(key="glass_ci_next"):
                ui.suggestion_list([(text, activity)], key_prefix="ci_next", compact=True)
            if mood in ("Low", "Difficult"):
                st.info(DISTRESS_NOTE, icon=":material/favorite:")
        else:
            st.html("""<div class="es-glass es-empty" style="padding:2rem 1rem"><div class="icon">🌤️</div>
                <div class="t" style="font-size:1.1rem">No right or wrong answer</div>
                <div class="d es-small">Your check-in is about how you see your day — the model isn't involved.</div>
                </div>""")
        st.html("""<div class="es-glass" style="margin-top:.8rem"><div class="es-stat-label">🔒 Your data</div>
            <div class="es-small es-muted" style="margin-top:.3rem">Only your mood, the factors you pick, and (if you
            choose) your note are saved — privately, in your own account. This is self-reported and is never
            combined into a diagnosis.</div></div>""")


def _journal() -> None:
    write_col, past_col = st.columns([1.6, 1], gap="large")
    with write_col:
        st.markdown("##### Want to put it into words?")
        prompt = st.selectbox("Choose a prompt", JOURNAL_PROMPTS, key="j_prompt")
        text = st.text_area(prompt, height=260, key="j_text", placeholder="Write freely — no rules, no audience…",
                            label_visibility="collapsed")
        ui.journal_save_button(prompt, text, key="j_save")
        st.caption("Journal entries are private to your account.")
    with past_col:
        st.markdown("##### Recent reflections")
        entries, notice = state.load_history()
        if notice:
            ui.soft_notice(notice)
        journal = [e for e in entries if e.get("kind") == "journal"][:5]
        if not journal:
            ui.empty_state("Nothing here yet", "Your saved reflections will appear here.", icon="📓")
        for e in journal:
            with st.expander(f"{local_time(e):%d %b, %H:%M} · {e.get('prompt', 'Reflection')}"):
                st.text(e.get("journalText", ""))
