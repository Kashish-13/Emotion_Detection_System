"""Dashboard: the latest expression front and centre, then today's status, a suggestion and recent activity."""
from datetime import datetime
from html import escape

import streamlit as st

from src.analytics import detections, history_stats, local_time, mood_reports
from src.ui import components as ui
from src.ui import state
from src.wellbeing import ACTIVITIES, DISCLAIMER, MOOD_SUGGESTIONS, MOODS, suggestions_for

KIND_TEXT = {"detection": "Expression saved", "checkin": "Daily check-in", "journal": "Journal entry",
             "reset": "Wellbeing activity"}
MOOD_COLOR = "#8b7cf6"


def render() -> None:
    entries, notice = state.load_history()
    stats = history_stats(entries)

    ui.page_header(f"Good to see you, {state.display_name()} 👋", "How are you feeling today?", eyebrow="Dashboard")
    if notice:
        ui.soft_notice(notice)
    if state.is_guest():
        st.caption(":material/info: Guest mode — your check-ins are kept only until you close this tab.")

    current = _current(entries)
    main, side = st.columns([1.45, 1], gap="large")
    with main:
        if current:
            ui.emotion_card(current["emotion"], current["confidence"], "Current emotion",
                            meta=current["meta"])
        else:
            st.html("""<div class="es-glass es-emotion-card" style="--c:#8b7cf6">
                <div class="es-eyebrow">Current emotion</div>
                <div class="es-emotion-main"><div class="es-emoji-orb" aria-hidden="true">✨</div>
                <div><div class="es-emotion-name" style="font-size:1.7rem;letter-spacing:0">Nothing analysed yet</div>
                <div class="es-muted" style="margin-top:.4rem">Analyse a photo or a webcam frame to see the
                expression the model detects, with its confidence.</div></div></div></div>""")
        b1, b2, _ = st.columns([1, 1, 0.6])
        if b1.button("Analyze again" if current else "Analyze my emotion", type="primary",
                     icon=":material/center_focus_strong:", width="stretch", key="dash_analyze"):
            state.go("detect")
        if b2.button("Live webcam", icon=":material/videocam:", width="stretch", key="dash_webcam"):
            state.go("webcam")
    with side:
        if current and current["probabilities"]:
            ui.emotion_bars(current["probabilities"], "Emotion probabilities")
        elif current:
            ui.emotion_bars(dict(current["top3"]), "Top 3 predictions")
        else:
            ui.empty_state("Probabilities appear here", "All seven expressions, ranked by the model.", icon="📊")

    st.write("")
    cols = st.columns(4)
    with cols[0]:
        done = _checked_in_today(entries)
        ui.stat_card("Today's check-in", "Done" if done else "Not yet",
                     "Thanks for checking in" if done else "Takes about a minute", icon="✅" if done else "📝")
    with cols[1]:
        dom = stats["dominant_expression"]
        ui.stat_card("Most common expression", dom or "—", "Model signal · saved detections", emotion=dom,
                     icon="🧭")
    with cols[2]:
        avg = stats["average_confidence"]
        ui.stat_card("Average confidence", f"{avg:.0%}" if avg is not None else "—", "Of saved detections",
                     icon="🎯")
    with cols[3]:
        ui.stat_card("Current streak", f"{stats['streak']} day{'s' if stats['streak'] != 1 else ''}",
                     "Consecutive days with a check-in", icon="🔥")

    rec, recent = st.columns([1, 1.2], gap="large")
    with rec:
        ui.section("Recommended for you", "A small, optional next step.")
        with st.container(key="glass_recommend"):
            _recommended(entries)
    with recent:
        ui.section("Recent activity", "Your latest saved moments.")
        if not entries:
            ui.empty_state("Your journey starts here.", "Complete your first check-in to see your insights.",
                           icon="🌱")
        else:
            _timeline(entries[:6])

    ui.section("Quick actions")
    q = st.columns(4)
    actions = [("Detect emotion", ":material/photo_camera:", "detect"), ("Daily check-in", ":material/edit_note:", "checkin"),
               ("Breathing reset", ":material/air:", "wellbeing"), ("View insights", ":material/insights:", "history")]
    for col, (label, icon, page) in zip(q, actions):
        if col.button(label, icon=icon, width="stretch", key=f"quick_{page}"):
            if page == "wellbeing":
                ui.open_activity("breathing")  # opens the Wellbeing page with the breathing guide
            else:
                state.go(page)
    ui.note(DISCLAIMER)


def _current(entries: list[dict]) -> dict | None:
    """Latest expression: this session's last analysis, else the latest saved detection."""
    last = st.session_state.get("last_face")
    if last:
        return {**last, "meta": f"From your latest {last['source']} analysis this session."}
    det = next(iter(detections(entries)), None)
    if not det:
        return None
    top3 = [(p["emotion"], p["probability"]) for p in det.get("topPredictions", [])] or \
           [(det["detectedEmotion"], det["confidence"])]
    return {"emotion": det["detectedEmotion"], "confidence": det["confidence"], "probabilities": None,
            "top3": top3, "meta": f"Latest saved detection · {local_time(det):%d %b, %H:%M}"}


def _checked_in_today(entries: list[dict]) -> bool:
    today = datetime.now().astimezone().date()
    return any(local_time(e).date() == today for e in mood_reports(entries))


def _recommended(entries: list[dict]) -> None:
    latest_det = next(iter(detections(entries)), None)
    latest_mood = next(iter(mood_reports(entries)), None)
    if latest_mood and (not latest_det or latest_mood["timestamp"] > latest_det["timestamp"]):
        mood = latest_mood["selfReportedMood"]
        text, activity = MOOD_SUGGESTIONS[mood]
        st.caption(f"Based on your latest check-in: {MOODS[mood]} {mood}")
        ui.suggestion_list([(text, activity)], key_prefix="dash_mood", compact=True)
        return
    emotion = latest_det["detectedEmotion"] if latest_det else "Neutral"
    s = suggestions_for(emotion)
    st.caption(f"Based on your latest detected expression: {ui.emoji(emotion)} {emotion}" if latest_det
               else "A good place to start")
    st.markdown(f"**{s['headline']}**")
    ui.suggestion_list(s["items"][:2], key_prefix="dash_emotion", compact=True)
    st.caption("General wellbeing ideas, not medical advice.")


def _timeline(entries: list[dict]) -> None:
    items = []
    for e in entries:
        kind = e.get("kind")
        c, main = MOOD_COLOR, KIND_TEXT.get(kind, "Entry")
        if kind == "detection":
            c, main = ui.color(e["detectedEmotion"]), f"{ui.emotion_pill(e['detectedEmotion'])} &nbsp;{e['confidence']:.0%} confidence"
        elif kind == "checkin":
            mood = e["selfReportedMood"]
            main = f"Check-in · {MOODS.get(mood, '')} {escape(mood)}"
        elif kind == "journal":
            main = f"Journal · {escape(e.get('prompt', 'Reflection'))}"
        elif kind == "reset":
            act = ACTIVITIES.get(e.get("activity"), {})
            main = f"{act.get('emoji', '🌿')} {escape(act.get('title', 'Activity'))} → {escape(e.get('feelingAfter', ''))}"
        items.append(f"""<div class="es-tl-item" style="--c:{c}"><div class="es-tl-time">
            {local_time(e):%a %d %b · %H:%M}</div><div class="es-tl-main">{main}</div></div>""")
    st.html(f'<div class="es-glass"><div class="es-timeline">{"".join(items)}</div></div>')
