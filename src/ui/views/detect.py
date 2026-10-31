"""Detect Emotion: upload a photo or take a camera snapshot, then explore the result."""
import hashlib

import cv2
import numpy as np
import streamlit as st

from src.gradcam import overlay_heatmap
from src.predict import InvalidImageError, annotate_image, decode_image
from src.storage import detection_entry
from src.ui import components as ui
from src.ui import state
from src.ui.resources import get_gradcam, get_predictor, model_missing
from src.wellbeing import MOODS, SELF_CHECK_PROMPT, suggestions_for


def render() -> None:
    ui.page_header("Detect", "Upload a photo or take a snapshot. The model finds each face and estimates its "
                   "facial expression.", eyebrow="Analyze", accent="emotion")
    predictor, error = get_predictor()
    if error:
        model_missing(error)
        return

    st.session_state.setdefault("detect_source", "Upload image")  # the dashboard can preselect "Camera"
    source = st.segmented_control("Image source", ["Upload image", "Camera"], key="detect_source",
                                  label_visibility="collapsed")
    st.session_state.setdefault("upload_round", 0)  # bumped by "Try another image" to reset the uploader
    data = None
    if source == "Camera":
        snap = st.camera_input("Take a snapshot", key=f"detect_snapshot_{st.session_state.upload_round}",
                               help="Your photo is analysed in memory and never stored.")
        data = snap.getvalue() if snap else None
    else:
        if not st.session_state.get("detect_cache"):
            st.html("""<div style="display:flex;align-items:center;gap:1rem;margin:.6rem 0 .7rem 0">
                <div class="es-stat-icon" style="width:3.2rem;height:3.2rem;font-size:1.5rem">📷</div>
                <div><div style="font-weight:700;font-size:1.1rem">Drop an image or choose a photo</div>
                <div class="es-muted es-small">JPG, PNG, BMP or WebP · works with one or several faces ·
                analysed in memory, never stored</div></div></div>""")
        upload = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png", "bmp", "webp"],
                                  key=f"detect_upload_{st.session_state.upload_round}",
                                  label_visibility="collapsed")
        data = upload.getvalue() if upload else None
    whole = st.toggle("If no face is found, treat the whole image as one face", key="detect_whole",
                      help="Useful for images that are already a tight crop of a single face.")

    if not data:
        st.session_state.pop("detect_cache", None)
        ui.section("What the model looks for")
        st.html("""<div class="es-grid" style="grid-template-columns:repeat(auto-fit,minmax(210px,1fr))">
            <div class="es-glass lift"><div style="font-size:1.4rem">🙂</div><div style="font-weight:700;margin-top:.3rem">
              Face the camera</div><div class="es-muted es-small">Frontal faces work best; turned heads are often missed.</div></div>
            <div class="es-glass lift"><div style="font-size:1.4rem">💡</div><div style="font-weight:700;margin-top:.3rem">
              Even, bright light</div><div class="es-muted es-small">Heavy shadows and backlight lower confidence.</div></div>
            <div class="es-glass lift"><div style="font-size:1.4rem">🔍</div><div style="font-weight:700;margin-top:.3rem">
              Big enough</div><div class="es-muted es-small">Faces at least ~50 px wide; the model sees 48×48 grayscale.</div></div>
            <div class="es-glass lift"><div style="font-size:1.4rem">🧠</div><div style="font-weight:700;margin-top:.3rem">
              Seven expressions</div><div class="es-muted es-small">Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral.</div></div>
            </div>""")
        return

    image_key = hashlib.sha1(data).hexdigest()[:16] + ("-w" if whole else "")
    try:
        image, result = _analyze(predictor, data, image_key, whole)
    except InvalidImageError as err:
        st.error(str(err))
        return

    if not result.faces:
        st.warning(result.message or "No face detected.", icon=":material/face:")
        st.image(image[:, :, ::-1], caption="Your image", width=420)
        _try_another()
        return
    if result.message:
        st.info(result.message, icon=":material/info:")

    index = 0
    if len(result.faces) > 1:
        choice = st.segmented_control("Face", [f"Face {i}" for i in range(1, len(result.faces) + 1)],
                                      default="Face 1", key=f"face_pick_{image_key}")
        index = int((choice or "Face 1").split()[1]) - 1
    face = result.faces[index]
    _log_session(result.faces, image_key, source)
    state.remember_face(face, "camera" if source == "Camera" else "image")

    left, right = st.columns([1.05, 1], gap="large")
    with left:
        with st.container(key="scan_image"):
            st.image(annotate_image(image, result.faces)[:, :, ::-1], width="stretch")
        st.caption(f"{len(result.faces)} face{'s' if len(result.faces) > 1 else ''} detected · analysed in memory, "
                   "not stored")
        if len(result.faces) > 1:
            chips = "".join(f'<span class="es-chip">Face {i} · {ui.emoji(f.emotion)} {f.emotion} {f.confidence:.0%}</span>'
                            for i, f in enumerate(result.faces, 1))
            st.html(f'<div class="es-chips">{chips}</div>')
    with right:
        ui.result_card(face, "Model detected" + (f" · Face {index + 1}" if len(result.faces) > 1 else ""))
        if face.level == "Low":
            ui.low_confidence_warning()
        if face.small_face:
            st.caption(f":material/zoom_in: {face.warning}")
        _try_another()

    ui.section("Emotion distribution", "The model's probability for each of the seven expressions.")
    ui.emotion_bars(face.probabilities)

    ui.section("Top 3 predictions")
    ui.rank_cards(face.top3)

    ui.section("Model attention (Grad-CAM)", "Where the model looked when making this prediction.")
    face_u8 = (face.face_input[..., 0] * 255).astype(np.uint8)
    heat, _, _ = get_gradcam(predictor.model).heatmap(face.face_input)
    c1, c2, text = st.columns([1, 1, 1.6], gap="medium", vertical_alignment="center")
    c1.image(cv2.resize(face_u8, (192, 192), interpolation=cv2.INTER_CUBIC), caption="Model input (48×48)",
             width="stretch")
    c2.image(overlay_heatmap(face_u8, heat), caption="Grad-CAM", width="stretch")
    text.html("""<div class="es-glass"><div style="font-weight:700">Reading the heatmap</div>
        <div class="es-muted es-small" style="margin-top:.3rem">Warm regions most increased the score of the
        predicted expression. It shows where the model looked, not proof that it is right.</div></div>""")

    st.divider()
    _next_steps(face, image_key, index, source)


def _try_another() -> None:
    if st.button("Try another image", icon=":material/refresh:", key="detect_again"):
        st.session_state.upload_round += 1
        st.session_state.pop("detect_cache", None)
        st.rerun()


def _analyze(predictor, data: bytes, image_key: str, whole: bool):
    """Analyse once per image; reruns (e.g. picking another face) reuse the cached result."""
    cached = st.session_state.get("detect_cache")
    if cached and cached[0] == image_key:
        return cached[1], cached[2]
    image = decode_image(data)
    with st.spinner("Analyzing facial expression…"):
        result = predictor.analyze(image, whole_image_if_no_face=whole)
    st.session_state.detect_cache = (image_key, image, result)
    return image, result


def _log_session(faces, image_key: str, source: str) -> None:
    logged = st.session_state.setdefault("logged_images", set())
    if image_key not in logged:
        logged.add(image_key)
        st.session_state.faces_detected += len(faces)
        st.session_state.session_predictions.extend(
            {"emotion": f.emotion, "confidence": f.confidence, "source": source} for f in faces)


def _next_steps(face, image_key: str, index: int, source: str) -> None:
    tips, save = st.columns([1.3, 1], gap="large")
    with tips:
        s = suggestions_for(face.emotion)
        ui.section("What you can do next", SELF_CHECK_PROMPT)
        with st.container(key="glass_next"):
            st.markdown(f"**{s['headline']}**")
            ui.suggestion_list(s["items"], key_prefix=f"det_{image_key}_{index}")
        st.caption("General wellbeing ideas, not medical advice. A detected expression doesn't tell us how you feel.")
    with save:
        saved = st.session_state.setdefault("saved_detections", set())
        save_key = f"{image_key}:{index}"
        ui.section("Save check-in")
        with st.container(key="glass_save"):
            st.caption("Saves the expression, confidence and top predictions — never the image.")
            mood = st.pills("How do you actually feel? (optional)", list(MOODS), key=f"mood_{save_key}",
                            format_func=lambda m: f"{MOODS[m]} {m}")
            if save_key in saved:
                ui.save_message("✓ Saved to your history.")
            elif st.button("Save check-in", type="primary", icon=":material/bookmark_add:", width="stretch",
                           key=f"save_{save_key}"):
                state.save_entry(detection_entry(face, "camera" if source == "Camera" else "image", mood))
                saved.add(save_key)
                st.rerun()  # the button is replaced by the confirmation, so it can't be saved twice
            if state.is_guest():
                st.caption("Guest mode: saved only for this session.")
