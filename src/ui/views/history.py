"""History & Insights: the user's own saved data, model signal and self-report kept apart."""
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
EMOTION_SCALE = alt.Scale(domain=list(config.EMOTION_COLORS), range=list(config.EMOTION_COLORS.values()))


def render() -> None:
    ui.page_header("History & insights", "Patterns in your own saved check-ins.", eyebrow="Insights")
    all_entries, error = state.load_history()
    if error:
        st.error(f"Couldn't load your history: {error}")
        return
    if not all_entries:
        ui.empty_state("No history yet", "Save a detection or complete a daily check-in to see insights here.")
        return

    span = st.segmented_control("Time range", list(RANGES), default="30 days", key="hist_range") or "30 days"
    entries = filter_since(all_entries, RANGES[span])
    stats = history_stats(entries)
    det, moods = detections(entries), mood_reports(entries)

    c = st.columns(4)
    with c[0]:
        ui.stat_card("Total check-ins", str(stats["total"]), f"In the last {span.lower()}" if RANGES[span] else "All time")
    with c[1]:
        dom = stats["dominant_expression"]
        ui.stat_card("Most common expression", dom or "—", "Model signal", emotion=dom)
    with c[2]:
        avg = stats["average_confidence"]
        ui.stat_card("Average confidence", f"{avg:.0%}" if avg is not None else "—", f"{len(det)} saved detections")
    with c[3]:
        ui.stat_card("Mood check-ins", str(len(moods)), "Self-reported")

    insights = generate_insights(entries)
    if insights:
        st.write("")
        st.markdown("#### Insights")
        cards = "".join(f"""<div class="es-card"><div class="es-tag">{escape(i['source'])}</div>
            <div style="margin-top:.25rem">{escape(i['text'])}</div></div>""" for i in insights)
        st.html(cards)
        st.caption("Simple patterns in your own data — not a diagnosis or an assessment of your wellbeing.")

    st.write("")
    model_col, mood_col = st.columns(2, gap="large")
    with model_col:
        st.markdown("#### Model signal")
        st.caption("Facial expressions the model detected in images you saved.")
        if det:
            _expression_distribution(stats["expression_counts"])
            _expression_timeline(det)
            _confidence_trend(det)
        else:
            st.info("No saved detections in this period.", icon=":material/info:")
    with mood_col:
        st.markdown("#### Self-reported mood")
        st.caption("How you said you felt, in your own words.")
        if moods:
            _mood_distribution(moods)
            _mood_trend(moods)
        else:
            st.info("No mood check-ins in this period.", icon=":material/info:")
        _per_day(entries)

    st.write("")
    st.markdown("#### Your recent activity")
    st.dataframe(_activity_table(entries[:50]), hide_index=True, width="stretch")
    _manage(all_entries)


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
                    width="stretch")


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
    st.altair_chart(chart, width="stretch")


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
    st.altair_chart((rules + line).properties(height=200), width="stretch")
    st.caption(f"Dashed lines: the app's confidence bands ({config.MODERATE_CONFIDENCE:.0%} and "
               f"{config.HIGH_CONFIDENCE:.0%}).")


def _mood_distribution(moods: list[dict]) -> None:
    order = list(MOODS)
    counts = pd.Series([e["selfReportedMood"] for e in moods]).value_counts().reindex(order, fill_value=0)
    df = pd.DataFrame({"Mood": [f"{MOODS[m]} {m}" for m in order], "Count": counts.values})
    base = alt.Chart(df).encode(y=alt.Y("Mood:N", sort=None, title=None),
                                x=alt.X("Count:Q", title=None, axis=alt.Axis(tickMinStep=1)), tooltip=["Mood", "Count"])
    st.markdown("**Mood distribution**")
    st.altair_chart((base.mark_bar(cornerRadiusEnd=4, height=14, color="#4f5bd5")
                     + base.mark_text(align="left", dx=4).encode(text="Count:Q")).properties(height=190),
                    width="stretch")


def _mood_trend(moods: list[dict]) -> None:
    df = pd.DataFrame({"Time": [local_time(e).replace(tzinfo=None) for e in moods],
                       "Score": [MOOD_SCORE[e["selfReportedMood"]] for e in moods],
                       "Mood": [e["selfReportedMood"] for e in moods]})
    chart = alt.Chart(df).mark_line(point=alt.OverlayMarkDef(size=60), strokeWidth=2, color="#4f5bd5").encode(
        x=alt.X("Time:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
        y=alt.Y("Score:Q", scale=alt.Scale(domain=[1, 5]), title=None,
                axis=alt.Axis(values=[1, 2, 3, 4, 5], labelExpr="['','Difficult','Low','Okay','Good','Great'][datum.value]")),
        tooltip=[alt.Tooltip("Time:T", format="%d %b %Y, %H:%M"), "Mood"]).properties(height=200)
    st.markdown("**Mood over time**")
    st.altair_chart(chart, width="stretch")


def _per_day(entries: list[dict]) -> None:
    days = pd.Series([local_time(e).date() for e in entries]).value_counts().sort_index()
    df = pd.DataFrame({"Day": pd.to_datetime(days.index), "Entries": days.values})
    chart = alt.Chart(df).mark_bar(cornerRadiusEnd=3, color="#4f5bd5", size=14).encode(
        x=alt.X("Day:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
        y=alt.Y("Entries:Q", title=None, axis=alt.Axis(tickMinStep=1)),
        tooltip=[alt.Tooltip("Day:T", format="%d %b %Y"), "Entries"]).properties(height=180)
    st.markdown("**Check-ins per day**")
    st.altair_chart(chart, width="stretch")


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
                _run(lambda: state.history_store().delete(target), "Entry deleted.")
        with many:
            sure = st.checkbox("I understand this deletes all my history", key="del_all_ok")
            if st.button("Delete all history", key="del_all_btn", type="primary", disabled=not sure):
                _run(lambda: state.history_store().clear(), "All history deleted.")


def _run(action, message: str) -> None:
    from src.firebase_client import FirebaseError

    try:
        action()
        st.toast(message, icon=":material/check:")
        st.rerun()
    except FirebaseError as err:
        st.error(str(err))
