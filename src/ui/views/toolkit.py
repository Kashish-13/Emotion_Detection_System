"""Wellbeing Toolkit: small resets and eight short activities (general wellbeing, not treatment)."""
from html import escape

import streamlit as st

from src.ui import components as ui
from src.wellbeing import ACTIVITIES, DISTRESS_NOTE, OVERWHELMED_RESETS, TOOLKIT_ORDER


def render() -> None:
    ui.page_header("Reset your", "Small actions can help you pause, reset and refocus.", eyebrow="Reflect · Wellbeing",
                   accent="mind.")

    active = st.session_state.get("activity")
    if active in ACTIVITIES:
        ui.render_activity(active)
        st.write("")

    with st.container(key="overwhelmed"):
        st.html("""<div class="es-eyebrow">Feeling overwhelmed?</div>
            <div class="es-title" style="font-size:1.55rem">If you're feeling overwhelmed, try one small reset.</div>
            <p class="es-subtitle" style="margin-bottom:.6rem">Pick whatever feels doable. This is something you
            choose — it is never triggered by the model.</p>""")
        cols = st.columns(3)
        for i, (icon, label, activity_id, hint) in enumerate(OVERWHELMED_RESETS):
            with cols[i % 3]:
                if activity_id:
                    if st.button(f"{icon}  {label}", key=f"reset_{i}", help=hint, width="stretch"):
                        _open(activity_id)
                else:
                    st.html(f"""<div class="es-glass" style="padding:.7rem 1rem;margin-bottom:.9rem;border-radius:16px">
                        <div style="font-weight:600">{icon}&nbsp; {escape(label)}</div>
                        <div class="es-muted es-small">{escape(hint)}</div></div>""")

    ui.section("Your toolkit", "Short guided activities. Each one ends with a quick “How do you feel after this?”.")
    for row in (TOOLKIT_ORDER[:4], TOOLKIT_ORDER[4:]):
        cols = st.columns(4)
        for col, activity_id in zip(cols, row):
            act = ACTIVITIES[activity_id]
            with col.container(key=f"act_{activity_id}"):
                st.html(f"""<div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div class="es-act-emoji">{act['emoji']}</div><span class="es-chip">⏱ {act['minutes']} min</span></div>
                    <div class="es-act-title">{escape(act['title'])}</div>
                    <div class="es-act-desc">{escape(act['summary'])}</div>""")
                if st.button("Start", key=f"start_{activity_id}", icon=":material/play_arrow:", width="stretch"):
                    _open(activity_id)

    st.write("")
    st.info(DISTRESS_NOTE, icon=":material/favorite:")
    st.caption("These activities are general wellbeing ideas, not medical or psychological advice.")


def _open(activity_id: str) -> None:
    st.session_state.activity = activity_id
    st.session_state.pop("grounding_step", None)
    st.rerun()
