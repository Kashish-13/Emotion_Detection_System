"""Live Webcam ("EmotionSense Vision"): OpenCV capture on the machine running Streamlit, with live stats."""
import os
import time

import altair as alt
import cv2
import pandas as pd
import streamlit as st

from src import config
from src.analytics import summarize_session
from src.predict import annotate_image
from src.storage import detection_entry
from src.ui import components as ui
from src.ui import state
from src.ui.resources import get_predictor, model_missing
from src.wellbeing import MOODS


def _set_running(running: bool) -> None:
    st.session_state.webcam_running = running


def _status(label: str, on: bool) -> str:
    return f'<span class="es-live{" on" if on else ""}"><i></i>{label}</span>'


def render() -> None:
    st.session_state.setdefault("webcam_running", False)
    running = st.session_state.webcam_running
    head, badge = st.columns([4, 1], vertical_alignment="bottom")
    with head:
        ui.page_header("EmotionSense", "Real-time face detection and facial-expression analysis from your webcam.",
                       eyebrow="Analyze · Live", accent="Vision")
    with badge:
        st.html(f'<div style="text-align:right;margin-bottom:1.6rem">'
                f'{_status("LIVE", True) if running else _status("CAMERA OFF", False)}</div>')
    predictor, error = get_predictor()
    if error:
        model_missing(error)
        return

    cam_col, stat_col = st.columns([1.65, 1], gap="large")
    with cam_col:
        with st.container(key="vision_live" if running else "vision_frame"):
            frame_slot = st.empty()
        if running:
            st.button("Pause camera", icon=":material/pause:", on_click=_set_running, args=(False,), key="cam_pause")
        else:
            st.button("Start camera", type="primary", icon=":material/videocam:", on_click=_set_running,
                      args=(True,), key="cam_start")
    with stat_col:
        stats_slot = st.empty()

    if not running:
        last = st.session_state.get("webcam_last")
        if last:
            frame_slot.image(last["frame"], caption="Last frame — camera paused", width="stretch")
            with stats_slot.container():
                _stats(last["faces"], last["fps"])
            with stat_col:
                _save_last(last["faces"])
        else:
            frame_slot.html("""<div class="es-vision-off"><div>
                <div style="font-size:2.6rem">📷</div>
                <div style="font-weight:700;font-size:1.15rem;margin-top:.4rem">Camera is off</div>
                <div class="es-muted" style="margin-top:.3rem;max-width:22rem">Press <b>Start camera</b>. Frames are
                processed in memory and never recorded.</div></div></div>""")
            with stats_slot.container():
                _stats([], None)
        st.caption(f"The webcam is read by OpenCV on the computer running this app, so live mode works when the "
                   f"app runs locally. Expressions are predicted every {config.WEBCAM_PREDICT_EVERY_N_FRAMES} "
                   "frames to keep CPU usage low.")
        st.divider()
        _session_summary()
        return

    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY  # DirectShow opens faster on Windows
    cap = cv2.VideoCapture(config.WEBCAM_INDEX, backend)
    if not cap.isOpened():
        cap.release()
        st.session_state.webcam_running = False
        frame_slot.error("Webcam unavailable. Check that a camera is connected, not used by another app, and that "
                         "camera access is allowed in your system privacy settings.", icon=":material/videocam_off:")
        return

    frame_i, faces, fps, last_log, prev = 0, [], None, 0.0, time.perf_counter()
    try:
        while True:  # Streamlit stops this loop when the user presses Pause (a rerun)
            ok, frame = cap.read()
            if not ok:
                frame_slot.error("Lost the webcam stream.")
                break
            now = time.perf_counter()
            fps = (1 / max(now - prev, 1e-6)) if fps is None else 0.9 * fps + 0.1 / max(now - prev, 1e-6)
            prev = now
            frame = cv2.flip(frame, 1)  # mirror view feels natural
            predicted = frame_i % config.WEBCAM_PREDICT_EVERY_N_FRAMES == 0
            if predicted:
                faces = predictor.analyze(frame, detection_downscale=config.WEBCAM_DETECTION_DOWNSCALE).faces
                if faces and time.time() - last_log >= config.WEBCAM_LOG_INTERVAL_S:
                    st.session_state.session_predictions.extend(
                        {"emotion": f.emotion, "confidence": f.confidence, "source": "webcam"} for f in faces)
                    st.session_state.faces_detected += len(faces)
                    del st.session_state.session_predictions[:-config.SESSION_HISTORY_SIZE]
                    state.remember_face(_primary(faces), "webcam")
                    last_log = time.time()
            rgb = annotate_image(frame, faces)[:, :, ::-1]
            frame_slot.image(rgb, channels="RGB", width="stretch")
            if predicted:
                with stats_slot.container():
                    _stats(faces, fps)
                st.session_state.webcam_last = {"frame": rgb, "faces": faces, "fps": fps}
            frame_i += 1
    finally:
        cap.release()


def _primary(faces):
    """The largest face is usually the person closest to the camera."""
    return max(faces, key=lambda f: f.box[2] * f.box[3] if f.box else 0)


def _stats(faces, fps) -> None:
    c1, c2 = st.columns(2)
    with c1:
        ui.stat_card("Faces", str(len(faces)), "In view", icon="👥")
    with c2:
        ui.stat_card("FPS", f"{fps:.1f}" if fps else "—", "Frames per second", icon="⚡")
    if not faces:
        if fps is not None:
            st.info("No face detected. Try adjusting your position or lighting.", icon=":material/face:")
        else:
            ui.empty_state("Waiting for a face", "Live results appear here once the camera is running.", icon="🎯")
        return
    main = _primary(faces)
    ui.emotion_card(main.emotion, main.confidence, "Current detected emotion" + (" · largest face" if len(faces) > 1 else ""))
    if main.level == "Low":
        st.caption(":material/info: Low confidence — lighting, pose or angle may be affecting the result.")
    ui.emotion_bars(dict(sorted(main.probabilities.items(), key=lambda kv: -kv[1])[:4]), "Emotion distribution · top 4")
    if len(faces) > 1:
        chips = "".join(f'<span class="es-chip">Face {i} · {ui.emoji(f.emotion)} {f.emotion} {f.confidence:.0%}</span>'
                        for i, f in enumerate(faces, 1))
        st.html(f'<div class="es-chips" style="margin-top:.7rem">{chips}</div>')


def _save_last(faces) -> None:
    if not faces:
        return
    with st.container(key="glass_cam_save"):
        st.markdown("**Save this moment**")
        options = [f"Face {i} · {f.emotion} {f.confidence:.0%}" for i, f in enumerate(faces, 1)]
        pick = st.selectbox("Face", options, key="cam_save_face", label_visibility="collapsed") if len(faces) > 1 \
            else options[0]
        face = faces[options.index(pick)]
        mood = st.pills("How do you actually feel? (optional)", list(MOODS), key="cam_mood",
                        format_func=lambda m: f"{MOODS[m]} {m}")
        if st.button("Save check-in", type="primary", icon=":material/bookmark_add:", width="stretch",
                     key="cam_save"):
            state.save_entry(detection_entry(face, "webcam", mood))
            ui.save_message("✓ Saved — the expression and confidence only, never the frame.")


def _session_summary() -> None:
    summary = summarize_session(st.session_state.session_predictions)
    ui.section("This session", "Live predictions from this browser session (not saved). They describe detected "
               "expressions, not how anyone feels.")
    if not summary["predictions"]:
        st.caption("No live predictions yet.")
        return
    c = st.columns(4)
    with c[0]:
        ui.stat_card("Predictions logged", str(summary["predictions"]), "At most one per second", icon="🧾")
    with c[1]:
        ui.stat_card("Faces detected", str(st.session_state.faces_detected), icon="👥")
    with c[2]:
        ui.stat_card("Most frequent", summary["dominant"], emotion=summary["dominant"])
    with c[3]:
        ui.stat_card("Average confidence", f"{summary['average_confidence']:.0%}", icon="🎯")
    df = pd.DataFrame({"Expression": list(summary["counts"]), "Count": list(summary["counts"].values())})
    chart = alt.Chart(df).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("Expression:N", sort=config.EMOTIONS, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Count:Q", title="Predictions", axis=alt.Axis(tickMinStep=1, format="d")),
        color=alt.Color("Expression:N", legend=None, scale=alt.Scale(
            domain=list(config.EMOTION_COLORS), range=list(config.EMOTION_COLORS.values()))),
        tooltip=["Expression", "Count"]).properties(height=220)
    st.altair_chart(chart, width="stretch", theme=None)
    if st.button("Reset session", icon=":material/restart_alt:", key="cam_reset"):
        st.session_state.session_predictions, st.session_state.faces_detected = [], 0
        st.rerun()
