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
    ui.page_header("Detect emotion", "Upload a photo or take a snapshot. The model finds each face and "
                   "predicts its facial expression.", eyebrow="Detection")
    predictor, error = get_predictor()
    if error:
        model_missing(error)
        return

    source = st.segmented_control("Image source", ["Upload image", "Camera"], default="Upload image",
                                  key="detect_source", label_visibility="collapsed")
    data = None
    if source == "Camera":
        snap = st.camera_input("Take a snapshot", key="detect_snapshot",
                               help="Your photo is analysed in memory and never stored.")
        data = snap.getvalue() if snap else None
    else:
        upload = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png", "bmp", "webp"],
                                  key="detect_upload")
        data = upload.getvalue() if upload else None
    whole = st.toggle("If no face is found, treat the whole image as one face", key="detect_whole",
                      help="Useful for images that are already a tight crop of a single face.")

    if not data:
        st.html("""<div class="es-card" style="margin-top:.8rem"><div class="es-stat-label">Tips for a clearer
            result</div><div class="es-small" style="margin-top:.3rem">Face the camera · even, bright lighting ·
            face at least ~50px wide · no heavy shadows or obstructions</div></div>""")
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
        return
    if result.message:
        st.info(result.message, icon=":material/info:")
    _log_session(result.faces, image_key, source)

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.image(annotate_image(image, result.faces)[:, :, ::-1], width="stretch",
                 caption=f"{len(result.faces)} face{'s' if len(result.faces) > 1 else ''} detected")
        if len(result.faces) > 1:
            cards = "".join(
                f"""<div class="es-card" style="padding:.7rem .9rem"><div class="es-stat-label">Face {i}</div>
                    <div style="font-weight:700;margin-top:.15rem">{ui.emotion_pill(f.emotion)}
                    &nbsp;{f.confidence:.0%}</div></div>""" for i, f in enumerate(result.faces, 1))
            st.html(f'<div class="es-grid" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr))">{cards}</div>')
    with right:
        index = 0
        if len(result.faces) > 1:
            choice = st.segmented_control("Face", [f"Face {i}" for i in range(1, len(result.faces) + 1)],
                                          default="Face 1", key=f"face_pick_{image_key}")
            index = int((choice or "Face 1").split()[1]) - 1
        face = result.faces[index]
        ui.result_card(face, "Detected expression" + (f" · Face {index + 1}" if len(result.faces) > 1 else ""))
        if face.level == "Low":
            ui.low_confidence_warning()
        if face.small_face:
            st.caption(f":material/zoom_in: {face.warning}")
        ui.top_bars(face.top3)

    st.write("")
    chart_col, cam_col = st.columns([1.15, 1], gap="large")
    with chart_col:
        st.markdown("##### Probability distribution")
        ui.probability_chart(face.probabilities)
    with cam_col:
        st.markdown("##### Model attention (Grad-CAM)")
        face_u8 = (face.face_input[..., 0] * 255).astype(np.uint8)
        heat, _, _ = get_gradcam(predictor.model).heatmap(face.face_input)
        c1, c2 = st.columns(2)
        c1.image(cv2.resize(face_u8, (192, 192), interpolation=cv2.INTER_CUBIC), caption="Model input (48×48)",
                 width="stretch")
        c2.image(overlay_heatmap(face_u8, heat), caption="Grad-CAM", width="stretch")
        st.caption("Orange marks regions that most increased the predicted score. It shows where the model "
                   "looked, not proof that it is right.")

    st.divider()
    _next_steps(face, image_key, index, source)


def _analyze(predictor, data: bytes, image_key: str, whole: bool):
    """Analyse once per image; reruns (e.g. picking another face) reuse the cached result."""
    cached = st.session_state.get("detect_cache")
    if cached and cached[0] == image_key:
        return cached[1], cached[2]
    image = decode_image(data)
    with st.spinner("Detecting faces…"):
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
        st.markdown("#### What you can do next")
        st.caption(SELF_CHECK_PROMPT)
        st.markdown(f"**{s['headline']}**")
        ui.suggestion_list(s["items"], key_prefix=f"det_{image_key}_{index}")
        st.caption("General wellbeing ideas, not medical advice. A detected expression doesn't tell us how you feel.")
    with save:
        saved = st.session_state.setdefault("saved_detections", set())
        save_key = f"{image_key}:{index}"
        with st.container(border=True):
            st.markdown("**Save check-in**")
            st.caption("Saves the expression, confidence and top predictions — never the image.")
            mood = st.pills("How do you actually feel? (optional)", list(MOODS), key=f"mood_{save_key}",
                            format_func=lambda m: f"{MOODS[m]} {m}")
            if save_key in saved:
                st.success("Saved to your history.", icon=":material/check_circle:")
            elif st.button("Save check-in", type="primary", icon=":material/bookmark_add:", width="stretch",
                           key=f"save_{save_key}"):
                error = state.save_entry(detection_entry(face, "camera" if source == "Camera" else "image", mood))
                if error:
                    st.error(error)
                else:
                    saved.add(save_key)
                    st.rerun()
            if state.is_guest():
                st.caption("Guest mode: saved only for this session.")
