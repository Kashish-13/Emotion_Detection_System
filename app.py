"""Emotion Detection System: Streamlit application.

Run from the project root:
    streamlit run app.py
"""
import json
import os
import time

import altair as alt
import cv2
import numpy as np
import pandas as pd
import streamlit as st

from src import config
from src.analytics import summarize_session
from src.predict import (AnalysisResult, EmotionPredictor, InvalidImageError, ModelLoadError,
                         ModelNotFoundError, annotate_image, decode_image)

st.set_page_config(page_title="Emotion Detection System", page_icon="🙂", layout="wide")

BAR_COLOR = "#2a78d6"
LEVEL_NOTE = {
    "High": f"High confidence (≥ {config.HIGH_CONFIDENCE:.0%})",
    "Moderate": f"Moderate confidence ({config.MODERATE_CONFIDENCE:.0%}–{config.HIGH_CONFIDENCE:.0%})",
    "Low": f"Low confidence (< {config.MODERATE_CONFIDENCE:.0%})",
}
DISCLAIMER = ("This tool predicts **facial expressions** from images. It does not measure what a person "
              "actually feels and is not a medical or psychological assessment.")


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading model…")
def get_predictor():
    """Returns (predictor, error_message). The model is loaded once per server process."""
    try:
        return EmotionPredictor(), None
    except (ModelNotFoundError, ModelLoadError, RuntimeError) as err:
        return None, str(err)


@st.cache_resource(show_spinner=False)
def get_gradcam(_model):
    from src.gradcam import GradCAM
    return GradCAM(_model)


@st.cache_data
def load_json(name: str):
    path = config.RESULTS_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def result_image(name: str, caption: str | None = None):
    path = config.RESULTS_DIR / name
    if path.is_file():
        st.image(str(path), caption=caption, width="stretch")
    else:
        st.info(f"`results/{name}` not found. Run training/evaluation to generate it.")


def init_session():
    st.session_state.setdefault("history", [])           # one dict per logged face prediction
    st.session_state.setdefault("faces_detected", 0)
    st.session_state.setdefault("logged_uploads", set())  # avoid double-counting on reruns


def log_predictions(faces, source: str):
    for f in faces:
        st.session_state.history.append({"emotion": f.emotion, "confidence": f.confidence, "source": source})
    st.session_state.faces_detected += len(faces)
    del st.session_state.history[:-config.SESSION_HISTORY_SIZE]


# ---------------------------------------------------------------------------
# Reusable UI pieces
# ---------------------------------------------------------------------------
def probability_chart(probabilities: dict):
    df = pd.DataFrame({"Emotion": list(probabilities), "Probability": list(probabilities.values())})
    df["Label"] = df["Probability"].map(lambda p: "<1%" if p < 0.01 else f"{p:.0%}")
    base = alt.Chart(df).encode(
        y=alt.Y("Emotion:N", sort="-x", title=None),
        x=alt.X("Probability:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%"), title=None),
        tooltip=["Emotion", alt.Tooltip("Probability:Q", format=".1%")],
    )
    bars = base.mark_bar(color=BAR_COLOR, cornerRadiusEnd=4, height=16)
    text = base.mark_text(align="left", dx=4, fontSize=12).encode(text="Label:N")
    st.altair_chart((bars + text).properties(height=230), width="stretch")


def show_face_result(i: int, face, predictor):
    from src.gradcam import overlay_heatmap

    st.markdown(f"#### Face #{i}")
    left, right = st.columns([1, 1.4], gap="large")
    with left:
        face_u8 = (face.face_input[..., 0] * 255).astype(np.uint8)
        heat, _, _ = get_gradcam(predictor.model).heatmap(face.face_input)
        c1, c2 = st.columns(2)
        c1.image(cv2.resize(face_u8, (192, 192), interpolation=cv2.INTER_CUBIC),
                 caption="Model input (48×48 grayscale)", width="stretch")
        c2.image(overlay_heatmap(face_u8, heat), caption="Model Attention / Grad-CAM", width="stretch")
        st.caption("Orange marks the regions that most increased the score of the predicted class. "
                   "It shows where the model looked, not proof that its reasoning is correct.")
    with right:
        st.metric("Predicted facial expression", f"{face.emotion} — {face.confidence:.0%}")
        if face.level == "High":
            st.success(LEVEL_NOTE["High"])
        elif face.level == "Moderate":
            st.info(LEVEL_NOTE["Moderate"])
        else:
            st.warning(LEVEL_NOTE["Low"])
        if face.warning:
            st.warning(face.warning)
        alts = " · ".join(f"{e} — {p:.0%}" for e, p in face.top3[1:])
        st.markdown(f"**Alternative predictions:** {alts}")
        probability_chart(face.probabilities)


def session_analytics(title: str = "Session analytics"):
    summary = summarize_session(st.session_state.history)
    st.subheader(title)
    st.caption("Counts of the model's facial-expression predictions in this browser session. "
               "They describe detected expressions, not anyone's emotional or mental state.")
    if not summary["predictions"]:
        st.info("No predictions yet in this session.")
        return
    c = st.columns(4)
    c[0].metric("Predictions logged", summary["predictions"])
    c[1].metric("Faces detected", st.session_state.faces_detected)
    c[2].metric("Most frequent expression", summary["dominant"])
    c[3].metric("Average confidence", f"{summary['average_confidence']:.0%}")
    df = pd.DataFrame({"Expression": list(summary["counts"]), "Count": list(summary["counts"].values())})
    chart = alt.Chart(df).mark_bar(color=BAR_COLOR, cornerRadiusEnd=4).encode(
        x=alt.X("Expression:N", sort=config.EMOTIONS, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Count:Q", title="Predictions"),
        tooltip=["Expression", "Count"],
    ).properties(height=240)
    st.altair_chart(chart, width="stretch")
    if st.button("Reset session analytics"):
        st.session_state.history, st.session_state.faces_detected = [], 0
        st.session_state.logged_uploads = set()
        st.rerun()


def model_missing(error: str):
    st.error("The emotion model could not be loaded.")
    st.code(error)
    st.markdown("Train it with `python -m src.train`, or place `emotion_model.keras` in `models/`. "
                "See the README for details.")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def home_page():
    st.title("Emotion Detection System")
    st.markdown("Facial-expression recognition with a custom **CNN** trained on **FER-2013**, "
                "**OpenCV** face detection, **Grad-CAM** explainability and real-time webcam inference.")

    metrics = load_json("metrics.json")
    if metrics:
        off, clean = metrics["official_test"], metrics["leakage_aware_test"]
        base = metrics["baseline_always_happy_official_test"]
        c = st.columns(4)
        c[0].metric("Test accuracy (official)", f"{off['accuracy']:.1%}",
                    f"{off['accuracy'] - base['accuracy']:+.1%} vs. always-'Happy'")
        c[1].metric("Macro F1 (official)", f"{off['macro_f1']:.3f}",
                    f"{off['macro_f1'] - base['macro_f1']:+.3f} vs. always-'Happy'")
        c[2].metric("Accuracy (leakage-aware)", f"{clean['accuracy']:.1%}", help=(
            "Test images that also appear, pixel for pixel, in train/validation are excluded."))
        c[3].metric("Macro F1 (leakage-aware)", f"{clean['macro_f1']:.3f}")

    st.subheader("How it works")
    steps = ["**1. Detect**: OpenCV Haar cascade finds each face.",
             "**2. Preprocess**: crop, grayscale, resize to 48×48, scale to [0, 1] (identical to training).",
             "**3. Classify**: the CNN outputs a probability for each of 7 expressions.",
             "**4. Explain**: Grad-CAM highlights the regions that drove the prediction."]
    for s, col in zip(steps, st.columns(4)):
        col.markdown(s)

    st.subheader("Supported expressions")
    st.markdown(" · ".join(f"**{e}**" for e in config.EMOTIONS))
    st.caption("These are the 7 FER-2013 labels. The model cannot output any other label.")

    summary = load_json("training_summary.json")
    if summary:
        st.subheader("Model summary")
        st.markdown(
            f"- Custom CNN, 4 convolutional blocks, **{summary['parameters']:,} parameters** "
            f"({summary['model_size_mb']} MB file)\n"
            f"- Trained on {summary['train_images']:,} images (CPU, {summary['training_minutes']} min); "
            f"best epoch {summary['best_epoch']} of {summary['epochs_run']}\n"
            "- Class-weighted loss to counter the imbalance (Disgust is 1.5% of training data)")
    st.info(DISCLAIMER)


def image_page():
    st.title("📷 Image Detection")
    predictor, error = get_predictor()
    if error:
        model_missing(error)
        return

    upload = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png", "bmp", "webp"])
    whole = st.checkbox("If no face is found, treat the whole image as one face (for already-cropped faces)")
    if upload is None:
        st.caption("Tip: front-facing, well-lit faces at least ~48 px wide give the most reliable results.")
        session_analytics()
        return

    try:
        image = decode_image(upload.getvalue())
    except InvalidImageError as err:
        st.error(str(err))
        return
    with st.spinner("Detecting faces…"):
        result: AnalysisResult = predictor.analyze(image, whole_image_if_no_face=whole)

    if result.message:
        (st.warning if not result.faces else st.info)(result.message)
    if not result.faces:
        st.image(image[:, :, ::-1], caption="Uploaded image", width="content")
        return

    upload_key = (upload.file_id, whole)
    if upload_key not in st.session_state.logged_uploads:
        st.session_state.logged_uploads.add(upload_key)
        log_predictions(result.faces, "image")

    st.success(f"{len(result.faces)} face(s) analysed.")
    st.image(annotate_image(image, result.faces)[:, :, ::-1], caption="Detected faces", width="stretch")
    for i, face in enumerate(result.faces, start=1):
        st.divider()
        show_face_result(i, face, predictor)
    st.divider()
    session_analytics()


def webcam_page():
    st.title("🎥 Live Webcam")
    predictor, error = get_predictor()
    if error:
        model_missing(error)
        return
    st.caption("The webcam is read by OpenCV on the machine running Streamlit, so this works when the app runs "
               f"locally. Emotion is predicted every {config.WEBCAM_PREDICT_EVERY_N_FRAMES} frames to save CPU.")

    running = st.toggle("Start webcam", key="webcam_on")
    frame_slot, live_slot = st.empty(), st.empty()
    if not running:
        frame_slot.info("Webcam is off. Switch on **Start webcam** to begin; switch it off to stop.")
        session_analytics()
        return

    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY  # DirectShow opens faster on Windows
    cap = cv2.VideoCapture(config.WEBCAM_INDEX, backend)
    if not cap.isOpened():
        cap.release()
        frame_slot.error("Webcam unavailable. Check that a camera is connected, not used by another app, "
                         "and that camera access is allowed in Windows privacy settings.")
        return

    frame_i, faces, last_log = 0, [], 0.0
    try:
        while True:  # Streamlit interrupts this loop when the toggle is switched off
            ok, frame = cap.read()
            if not ok:
                frame_slot.error("Lost the webcam stream.")
                break
            frame = cv2.flip(frame, 1)  # mirror view feels natural
            if frame_i % config.WEBCAM_PREDICT_EVERY_N_FRAMES == 0:
                faces = predictor.analyze(frame, detection_downscale=config.WEBCAM_DETECTION_DOWNSCALE).faces
                if faces and time.time() - last_log >= config.WEBCAM_LOG_INTERVAL_S:
                    log_predictions(faces, "webcam")
                    last_log = time.time()
            frame_slot.image(annotate_image(frame, faces)[:, :, ::-1], channels="RGB", width="stretch")
            if frame_i % config.WEBCAM_PREDICT_EVERY_N_FRAMES == 0:
                summary = summarize_session(st.session_state.history)
                live = " · ".join(f"{f.emotion} {f.confidence:.0%}" for f in faces) or "no face detected"
                live_slot.markdown(f"**Current:** {live}  \n**Session:** {summary['predictions']} predictions logged"
                                   + (f", most frequent: {summary['dominant']}" if summary["dominant"] else ""))
            frame_i += 1
    finally:
        cap.release()


def insights_page():
    st.title("📊 Model Insights")
    metrics = load_json("metrics.json")
    if not metrics:
        st.info("No evaluation results yet. Run `python -m src.evaluate`.")
        return

    st.subheader("Test-set performance")
    rows = {
        "Official test (3,589)": metrics["official_test"],
        f"Leakage-aware test ({metrics['leakage_aware_test']['n']:,})": metrics["leakage_aware_test"],
        "Baseline: always 'Happy'": metrics["baseline_always_happy_official_test"],
    }
    table = pd.DataFrame(rows).T[["accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1"]]
    st.dataframe(table.style.format("{:.3f}"), width="stretch")
    st.caption(
        "FER-2013 contains exact duplicate images across splits: about 8% of official test images also appear in "
        "training. The **leakage-aware** row excludes them and is the more honest estimate for unseen faces. "
        f"Top-3 accuracy (official test): {metrics['top3_accuracy_official_test']:.1%}.")

    st.subheader("Training curves")
    result_image("training_curves.png")
    st.subheader("Confusion matrices (official test set)")
    c1, c2 = st.columns(2)
    with c1:
        result_image("confusion_matrix.png")
    with c2:
        result_image("confusion_matrix_normalized.png")

    st.subheader("Per-class metrics")
    result_image("per_class_metrics.png")
    per_class = pd.DataFrame(metrics["per_class_official_test"]).T
    st.dataframe(per_class.style.format({"precision": "{:.3f}", "recall": "{:.3f}", "f1": "{:.3f}"}),
                 width="stretch")

    st.subheader("Model Attention / Grad-CAM examples")
    result_image("gradcam/gradcam_correct.png")
    result_image("gradcam/gradcam_misclassified.png")

    st.subheader("Confidence reliability (validation set)")
    st.caption("How often the model is right, grouped by its own confidence. The app's High / Moderate / Low "
               "bands are application heuristics, not validated measures of certainty.")
    st.dataframe(pd.DataFrame(metrics["confidence_reliability_validation"]).set_index("bin"), width="stretch")

    st.subheader("Dataset imbalance")
    result_image("eda_class_distribution.png")
    st.markdown("Disgust has 16.5× fewer training images than Happy. Training uses class weights, and the model is "
                "evaluated with macro F1, which weights every class equally.")

    st.subheader("Limitations")
    st.markdown(
        "- 48×48 grayscale images limit fine detail; labels are noisy (human accuracy on FER-2013 is ~65%).\n"
        "- Disgust and Fear remain the hardest classes; Disgust metrics rely on only ~55 test images.\n"
        "- Trained on mostly frontal web photos: performance drops with head pose, occlusion and poor lighting.\n"
        "- The demographic composition of FER-2013 is undocumented; performance across groups is not audited.")


def about_page():
    st.title("ℹ️ About")
    st.markdown(f"""
### Dataset
**FER-2013**: 35,887 grayscale 48×48 face images, 7 expression labels, with the official splits
Training (28,709) / PublicTest (3,589, used for validation) / PrivateTest (3,589, used for test).
13 near-blank images (no face) are excluded from training and validation.
Exact duplicate images across splits were detected; see *Evaluation methodology*.

### Architecture
A custom VGG-style CNN: four blocks of two 3×3 convolutions, each followed by BatchNorm and ReLU, with
max-pooling and dropout after the first three blocks. Global average pooling, a 256-unit dense layer
with dropout 0.5, then a 7-way softmax.

### Preprocessing
Face crop → grayscale → resize to 48×48 → divide by 255. The same function is used in training and
inference. Training-only augmentation: horizontal flip, ±10° rotation, 10% zoom and shift, and ±10%
brightness and contrast.

### Training
Adam (learning rate {config.LEARNING_RATE}), sparse categorical cross-entropy with **balanced class
weights** computed from the training labels, ReduceLROnPlateau, EarlyStopping and checkpoint selection
on **validation macro F1**.

### Evaluation methodology
Metrics are reported on the **official test set**, so they are comparable with published results, **and**
on a **leakage-aware subset** that excludes test images whose exact pixels also occur in train or
validation. Macro F1 is the headline metric because accuracy rewards ignoring rare classes.

### Ethical limitations
- Predicts *facial expressions*, not internal emotions. A smile is not proof of happiness.
- Not a diagnostic, medical, psychological or hiring tool. It must not be used to judge people.
- Expressions differ across cultures and individuals; the dataset's demographic balance is unknown.
- Webcam frames are processed locally in memory and are never stored by this app.

### Tech stack
Python · TensorFlow/Keras · OpenCV · NumPy · pandas · scikit-learn · Matplotlib · Streamlit
""")


# ---------------------------------------------------------------------------
def main():
    init_session()
    with st.sidebar:
        st.markdown("### Emotion Detection System")
        st.caption("Facial-expression classifier (FER-2013). Not a diagnostic tool.")
    pages = [
        st.Page(home_page, title="Home", icon="🏠", default=True, url_path="home"),
        st.Page(image_page, title="Image Detection", icon="📷", url_path="image"),
        st.Page(webcam_page, title="Live Webcam", icon="🎥", url_path="webcam"),
        st.Page(insights_page, title="Model Insights", icon="📊", url_path="insights"),
        st.Page(about_page, title="About", icon="ℹ️", url_path="about"),
    ]
    st.navigation(pages).run()


if __name__ == "__main__":  # `streamlit run app.py` executes this file as __main__
    main()
