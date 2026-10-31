"""History & Insights: the user's own saved data, model signal and self-report kept apart."""
from collections import Counter
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from src import config
from src.analytics import (detections, filter_since, generate_insights, history_stats, local_time,
                           mood_reports)
from src.ui import components as ui
from src.ui import state
from src.wellbeing import ACTIVITIES, MOOD_SCORE, MOODS

RANGES = {"7 days": 7, "30 days": 30, "All time": None}
KIND_LABEL = {"detection": "Detection", "checkin": "Check-in", "journal": "Journal", "reset": "Wellbeing activity"}
# Self-reported mood uses one violet hue, lighter for brighter moods (it is not an emotion class).
MOOD_COLOR = {"Great": "#a5b4fc", "Good": "#818cf8", "Okay": "#6366f1", "Low": "#4f46e5", "Difficult": "#3730a3"}
EMOTION_SCALE = alt.Scale(domain=list(config.EMOTION_COLORS), range=list(config.EMOTION_COLORS.values()))


def render() -> None:
    ui.page_header("History &", "Patterns in your own saved check-ins.", eyebrow="Reflect · History", accent="insights")
    all_entries, _ = state.load_history()
    if not all_entries:
        ui.empty_state("No saved check-ins yet.", "Your story starts here — complete your first check-in to see "
                       "your personal patterns.", icon="🌱")
        a, b, _ = st.columns([1, 1, 2])
        if a.button("Daily check-in", type="primary", icon=":material/edit_note:", width="stretch", key="hist_ci"):
            state.go("checkin")
        if b.button("Detect emotion", icon=":material/photo_camera:", width="stretch", key="hist_det"):
            state.go("detect")
        return

    span = st.segmented_control("Time range", list(RANGES), default="30 days", key="hist_range") or "30 days"
    entries = filter_since(all_entries, RANGES[span])
    stats = history_stats(entries)
    det, moods = detections(entries), mood_reports(entries)

    c = st.columns(4)
    with c[0]:
        ui.stat_card("Total check-ins", str(stats["total"]),
                     f"In the last {span.lower()}" if RANGES[span] else "All time", icon="🗂️")
    with c[1]:
        common_mood = Counter(e["selfReportedMood"] for e in moods).most_common(1)
        mood = common_mood[0][0] if common_mood else None
        ui.stat_card("Most common mood", f"{MOODS[mood]} {mood}" if mood else "—", "Self-reported", icon="💬")
    with c[2]:
        factors = Counter(f for e in moods for f in e.get("moodFactors", [])).most_common(2)
        ui.stat_card("Top factors", " · ".join(f for f, _ in factors) or "—", "Selected most often", icon="🧩")
    with c[3]:
        ui.stat_card("Current streak", f"{stats['streak']} day{'s' if stats['streak'] != 1 else ''}",
                     "Days in a row", icon="🔥")

    insights = generate_insights(entries)
    if insights:
        ui.section("Insights", "Simple patterns in your own data — not a diagnosis or an assessment of your wellbeing.")
        icons = {"Model signal": "🧭", "Self-reported mood": "💬", "Tip": "💡"}
        cards = "".join(f"""<div class="es-glass lift"><div class="es-tag">{icons.get(i['source'], '')}
            {escape(i['source'])}</div><div style="margin-top:.3rem">{escape(i['text'])}</div></div>"""
                        for i in insights)
        st.html(f'<div class="es-grid" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">{cards}</div>')

    model_col, mood_col = st.columns(2, gap="large")
    with model_col:
        ui.section("🧭 Model signal", "Facial expressions the model detected in images you saved.")
        if det:
            dom, avg = stats["dominant_expression"], stats["average_confidence"]
            a, b = st.columns(2)
            with a:
                ui.stat_card("Top expression", dom or "—", "Model signal", emotion=dom)
            with b:
                ui.stat_card("Average confidence", f"{avg:.0%}", f"{len(det)} saved detections", icon="🎯")
            _expression_distribution(stats["expression_counts"])
            _expression_timeline(det)
            _confidence_trend(det)
        else:
            ui.empty_state("No saved detections", "Save a result on Detect Emotion to see expression patterns.",
                           icon="📷")
    with mood_col:
        ui.section("💬 Self-reported mood", "How you said you felt, in your own words.")
        if moods:
            _checkin_timeline(moods[:6])
            _mood_distribution(moods)
            _mood_trend(moods)
        else:
            ui.empty_state("No mood check-ins", "Complete a daily check-in to see your mood over time.", icon="📝")
        _per_day(entries)

    ui.section("Your recent activity")
    st.dataframe(_activity_table(entries[:50]), hide_index=True, width="stretch")
    _manage(all_entries)


def _checkin_timeline(moods: list[dict]) -> None:
    items = "".join(
        f"""<div class="es-tl-item" style="--c:{MOOD_COLOR[e['selfReportedMood']]}"><div class="es-tl-time">
            {local_time(e):%a %d %b · %H:%M}</div><div class="es-tl-main">{MOODS[e['selfReportedMood']]}
            {escape(e['selfReportedMood'])}{''.join(f' <span class="es-chip" style="padding:.1rem .5rem;font-size:.72rem">{escape(f)}</span>' for f in e.get('moodFactors', []))}
            </div></div>""" for e in moods)
    st.markdown("**Recent check-ins**")
    st.html(f'<div class="es-glass" style="margin-bottom:1rem"><div class="es-timeline">{items}</div></div>')


# ---------------------------------------------------------------------------
def _expression_distribution(counts: dict) -> None:
    df = pd.DataFrame({"Expression": list(counts), "Count": list(counts.values())})
    base = alt.Chart(df).encode(y=alt.Y("Expression:N", sort=config.EMOTIONS, title=None),
                                x=alt.X("Count:Q", title=None, axis=alt.Axis(tickMinStep=1)),
                                tooltip=["Expression", "Count"])
    chart = base.mark_bar(cornerRadiusEnd=4, height=14).encode(color=alt.Color("Expression:N", legend=None,
                                                                             scale=EMOTION_SCALE))
    st.markdown("**Expression distribution**")
    st.altair_chart((chart + base.mark_text(align="left", dx=4).encode(text="Count:Q")).properties(height=210),
                    width="stretch", theme=None)


def _expression_timeline(det: list[dict]) -> None:
    df = pd.DataFrame({"Time": [local_time(e).replace(tzinfo=None) for e in det],
                       "Expression": [e["detectedEmotion"] for e in det],
                       "Confidence": [e["confidence"] for e in det]})
    chart = alt.Chart(df).mark_circle(size=120, opacity=0.9, stroke="white", strokeWidth=1.5).encode(
        x=alt.X("Time:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
        y=alt.Y("Expression:N", sort=config.EMOTIONS, scale=alt.Scale(domain=config.EMOTIONS), title=None),
        color=alt.Color("Expression:N", legend=None, scale=EMOTION_SCALE),
        tooltip=[alt.Tooltip("Time:T", format="%d %b %Y, %H:%M"), "Expression",
                 alt.Tooltip("Confidence:Q", format=".0%")]).properties(height=230)
    st.markdown("**Expression timeline**")
    st.altair_chart(chart, width="stretch", theme=None)


def _confidence_trend(det: list[dict]) -> None:
    df = pd.DataFrame({"Time": [local_time(e).replace(tzinfo=None) for e in det],
                       "Confidence": [e["confidence"] for e in det],
                       "Expression": [e["detectedEmotion"] for e in det]})
    line = alt.Chart(df).mark_line(point=alt.OverlayMarkDef(size=60), strokeWidth=2).encode(
        x=alt.X("Time:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
        y=alt.Y("Confidence:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%"), title=None),
        tooltip=[alt.Tooltip("Time:T", format="%d %b %Y, %H:%M"), "Expression",
                 alt.Tooltip("Confidence:Q", format=".0%")])
    bands = pd.DataFrame({"y": [config.MODERATE_CONFIDENCE, config.HIGH_CONFIDENCE],
                          "label": ["Low / moderate", "Moderate / high"]})
    rules = alt.Chart(bands).mark_rule(strokeDash=[4, 4], opacity=0.45).encode(y="y:Q", tooltip=["label"])
    st.markdown("**Confidence trend**")
    st.altair_chart((rules + line).properties(height=200), width="stretch", theme=None)
    st.caption(f"Dashed lines: the app's confidence bands ({config.MODERATE_CONFIDENCE:.0%} and "
               f"{config.HIGH_CONFIDENCE:.0%}).")


def _mood_distribution(moods: list[dict]) -> None:
    order = list(MOODS)
    counts = pd.Series([e["selfReportedMood"] for e in moods]).value_counts().reindex(order, fill_value=0)
    df = pd.DataFrame({"Mood": [f"{MOODS[m]} {m}" for m in order], "Count": counts.values})
    base = alt.Chart(df).encode(y=alt.Y("Mood:N", sort=None, title=None),
                                x=alt.X("Count:Q", title=None, axis=alt.Axis(tickMinStep=1)), tooltip=["Mood", "Count"])
    st.markdown("**Mood distribution**")
    st.altair_chart((base.mark_bar(cornerRadiusEnd=4, height=14, color="#6366f1")
                     + base.mark_text(align="left", dx=4).encode(text="Count:Q")).properties(height=190),
                    width="stretch", theme=None)


def _mood_trend(moods: list[dict]) -> None:
    df = pd.DataFrame({"Time": [local_time(e).replace(tzinfo=None) for e in moods],
                       "Score": [MOOD_SCORE[e["selfReportedMood"]] for e in moods],
                       "Mood": [e["selfReportedMood"] for e in moods]})
    chart = alt.Chart(df).mark_line(point=alt.OverlayMarkDef(size=60), strokeWidth=2, color="#6366f1").encode(
        x=alt.X("Time:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
        y=alt.Y("Score:Q", scale=alt.Scale(domain=[1, 5]), title=None,
                axis=alt.Axis(values=[1, 2, 3, 4, 5], labelExpr="['','Difficult','Low','Okay','Good','Great'][datum.value]")),
        tooltip=[alt.Tooltip("Time:T", format="%d %b %Y, %H:%M"), "Mood"]).properties(height=200)
    st.markdown("**Mood over time**")
    st.altair_chart(chart, width="stretch", theme=None)


def _per_day(entries: list[dict]) -> None:
    days = pd.Series([local_time(e).date() for e in entries]).value_counts().sort_index()
    df = pd.DataFrame({"Day": pd.to_datetime(days.index), "Entries": days.values})
    chart = alt.Chart(df).mark_bar(cornerRadiusEnd=3, color="#6366f1", size=14).encode(
        x=alt.X("Day:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
        y=alt.Y("Entries:Q", title=None, axis=alt.Axis(tickMinStep=1)),
        tooltip=[alt.Tooltip("Day:T", format="%d %b %Y"), "Entries"]).properties(height=180)
    st.markdown("**Check-ins per day**")
    st.altair_chart(chart, width="stretch", theme=None)


def _activity_table(entries: list[dict]) -> pd.DataFrame:
    rows = []
    for e in entries:
        detail = ""
        if e.get("kind") == "reset":
            detail = f"{ACTIVITIES.get(e.get('activity'), {}).get('title', 'Activity')} → {e.get('feelingAfter', '')}"
        elif e.get("kind") == "journal":
            detail = e.get("prompt", "")
        elif e.get("moodFactors"):
            detail = ", ".join(e["moodFactors"])
        rows.append({"Date": local_time(e).strftime("%d %b %Y, %H:%M"), "Type": KIND_LABEL.get(e.get("kind"), ""),
                     "Detected expression": e.get("detectedEmotion", ""),
                     "Confidence": f"{e['confidence']:.0%}" if "confidence" in e else "",
                     "Self-reported mood": e.get("selfReportedMood", ""), "Details": detail})
    return pd.DataFrame(rows)


def _manage(entries: list[dict]) -> None:
    with st.expander("Manage my data", icon=":material/delete:"):
        st.caption("You can delete any entry, or all of your history. Deletion is permanent.")
        labels = {e["id"]: f"{local_time(e):%d %b %Y, %H:%M} · {KIND_LABEL.get(e.get('kind'), '')}"
                  f"{' · ' + e['detectedEmotion'] if e.get('detectedEmotion') else ''}"
                  f"{' · ' + e['selfReportedMood'] if e.get('selfReportedMood') else ''}" for e in entries}
        one, many = st.columns(2, gap="large")
        with one:
            target = st.selectbox("Delete one entry", list(labels), format_func=labels.get, key="del_one")
            if st.button("Delete entry", key="del_one_btn", icon=":material/delete:"):
                _run(lambda: state.delete_entry(target), "Entry deleted.")
        with many:
            sure = st.checkbox("I understand this deletes all my history", key="del_all_ok")
            if st.button("Delete all history", key="del_all_btn", type="primary", disabled=not sure):
                _run(state.clear_history, "All history deleted.")


def _run(action, message: str) -> None:
    """Run a delete action from state (returns False if the cloud couldn't be reached)."""
    if action():
        st.toast(message, icon=":material/check:")
        st.rerun()
    else:
        st.warning("Some entries couldn't be deleted right now. Please try again in a minute.",
                   icon=":material/info:")
