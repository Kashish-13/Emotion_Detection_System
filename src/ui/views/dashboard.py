"""Dashboard: greeting, summary cards, quick actions, recent snapshots and suggestions."""
import altair as alt
import pandas as pd
import streamlit as st

from src import config
from src.analytics import detections, history_stats, local_time, mood_reports
from src.ui import components as ui
from src.ui import state
from src.wellbeing import DISCLAIMER, MOOD_SUGGESTIONS, MOODS, suggestions_for


def render() -> None:
    entries, error = state.load_history()
    if error:
        st.error(f"Couldn't load your history: {error}")
    stats = history_stats(entries)

    ui.page_header(f"Good to see you, {state.display_name()} 👋",
                   "Take a moment to understand how you're feeling.", eyebrow="Dashboard")
    if state.is_guest():
        st.caption(":material/info: Guest mode — your check-ins are kept only until you close this tab.")

    cols = st.columns(4)
    with cols[0]:
        ui.stat_card("Today's check-ins", str(stats["today"]), "Saved entries today")
    with cols[1]:
        dom = stats["dominant_expression"]
        ui.stat_card("Dominant expression", dom or "—", "Model signal, all saved detections", emotion=dom)
    with cols[2]:
        avg = stats["average_confidence"]
        ui.stat_card("Average confidence", f"{avg:.0%}" if avg is not None else "—", "Of saved detections")
    with cols[3]:
        ui.stat_card("Current streak", f"{stats['streak']} day{'s' if stats['streak'] != 1 else ''}",
                     "Consecutive days with a check-in")

    st.write("")
    hero, side = st.columns([1.6, 1], gap="large")
    with hero:
        st.html("""<div class="es-hero"><div class="es-eyebrow">Quick start</div>
            <div class="es-title" style="font-size:1.6rem">How are you feeling today?</div>
            <p class="es-subtitle">Detect your facial expression from a photo, or tell us in your own words with
            a quick check-in.</p></div>""")
        b1, b2, _ = st.columns([1, 1, 1.2])
        if b1.button("Detect emotion", type="primary", icon=":material/photo_camera:", width="stretch"):
            state.go("detect")
        if b2.button("Quick check-in", icon=":material/edit_note:", width="stretch"):
            state.go("checkin")
    with side:
        _recommended(entries)

    st.write("")
    st.markdown("#### Your recent emotional snapshots")
    det = detections(entries)
    if not entries:
        ui.empty_state("Your journey starts here.", "Complete your first check-in to see your insights.")
    elif not det:
        st.info("You have check-ins but no saved detections yet. Save a result on **Detect Emotion** to see "
                "your expression snapshots here.", icon=":material/info:")
    else:
        _snapshot_chart(det[:20])
        st.caption("Model signal: facial expressions the model detected in images you chose to save. "
                   "Expressions are not a measure of how you actually feel.")
    ui.note(DISCLAIMER)


def _recommended(entries: list[dict]) -> None:
    latest_det = next(iter(detections(entries)), None)
    latest_mood = next(iter(mood_reports(entries)), None)
    st.markdown("##### Recommended for you")
    if latest_mood and (not latest_det or latest_mood["timestamp"] > latest_det["timestamp"]):
        mood = latest_mood["selfReportedMood"]
        text, activity = MOOD_SUGGESTIONS[mood]
        st.caption(f"Based on your latest check-in: {MOODS[mood]} {mood}")
        ui.suggestion_list([(text, activity)], key_prefix="dash_mood", compact=True)
        return
    emotion = latest_det["detectedEmotion"] if latest_det else "Neutral"
    s = suggestions_for(emotion)
    st.caption(f"Based on your latest detected expression: {emotion}" if latest_det
               else "A good place to start")
    st.markdown(f"**{s['headline']}**")
    ui.suggestion_list(s["items"][:3], key_prefix="dash_emotion", compact=True)
    st.caption("General wellbeing ideas, not medical advice.")


def _snapshot_chart(det: list[dict]) -> None:
    df = pd.DataFrame({
        "Time": [local_time(e).replace(tzinfo=None) for e in det],
        "Expression": [e["detectedEmotion"] for e in det],
        "Confidence": [e["confidence"] for e in det],
    })
    chart = alt.Chart(df).mark_circle(size=170, opacity=0.9, stroke="white", strokeWidth=2).encode(
        x=alt.X("Time:T", title=None, axis=alt.Axis(format="%d %b %H:%M", labelAngle=0, tickCount=6)),
        y=alt.Y("Expression:N", sort=config.EMOTIONS, title=None, scale=alt.Scale(domain=config.EMOTIONS)),
        color=alt.Color("Expression:N", legend=None, scale=alt.Scale(
            domain=list(config.EMOTION_COLORS), range=list(config.EMOTION_COLORS.values()))),
        tooltip=[alt.Tooltip("Time:T", format="%d %b %Y, %H:%M"), "Expression",
                 alt.Tooltip("Confidence:Q", format=".0%")],
    ).properties(height=260)
    st.altair_chart(chart, width="stretch")
