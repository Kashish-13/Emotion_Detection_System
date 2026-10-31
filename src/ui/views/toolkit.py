"""Wellbeing Toolkit: quick resets and eight short activities (general wellbeing, not treatment)."""
import streamlit as st

from src.ui import components as ui
from src.wellbeing import ACTIVITIES, DISTRESS_NOTE, QUICK_RESETS, TOOLKIT_ORDER


def render() -> None:
    ui.page_header("Wellbeing toolkit", "Short, simple activities for a pause, a reset, or a moment of focus.",
                   eyebrow="Wellbeing")

    active = st.session_state.get("activity")
    if active in ACTIVITIES:
        ui.render_activity(active)
        st.write("")

    st.html("""<div class="es-hero"><div class="es-eyebrow">Feeling overwhelmed?</div>
        <div class="es-title" style="font-size:1.45rem">Would you like a quick reset?</div>
        <p class="es-subtitle">Pick one. This is something you choose — it isn't triggered by the model.</p></div>""")
    cols = st.columns(len(QUICK_RESETS))
    for col, (activity_id, label) in zip(cols, QUICK_RESETS):
        if col.button(label, key=f"reset_{activity_id}", icon=ACTIVITIES[activity_id]["icon"], width="stretch"):
            _open(activity_id)

    st.write("")
    st.markdown("#### Toolkit")
    for row in (TOOLKIT_ORDER[:4], TOOLKIT_ORDER[4:]):
        cols = st.columns(4)
        for col, activity_id in zip(cols, row):
            act = ACTIVITIES[activity_id]
            with col.container(border=True, height=205):
                st.markdown(f"**{act['title']}**")
                st.caption(f"{act['summary']}  \n{act['minutes']} min")
                if st.button("Start", key=f"start_{activity_id}", icon=act["icon"], width="stretch"):
                    _open(activity_id)

    st.write("")
    st.info(DISTRESS_NOTE, icon=":material/favorite:")
    st.caption("These activities are general wellbeing ideas, not medical or psychological advice.")


def _open(activity_id: str) -> None:
    st.session_state.activity = activity_id
    st.session_state.pop("grounding_step", None)
    st.rerun()
