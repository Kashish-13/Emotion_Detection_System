import cv2
import numpy as np
import pytest

from src import config
from src.analytics import summarize_session
from src.face_detector import FaceDetector, crop_face
from src.gradcam import GradCAM, find_last_conv_layer, overlay_heatmap
from src.model import GRADCAM_LAYER
from src.predict import (InvalidImageError, ModelLoadError, ModelNotFoundError, annotate_image,
                         confidence_level, decode_image, load_emotion_model, make_prediction)


# --- prediction output format ------------------------------------------------
def test_make_prediction_format_top3_and_probabilities():
    probs = np.array([0.05, 0.01, 0.02, 0.70, 0.04, 0.10, 0.08], dtype=np.float32)
    p = make_prediction(probs)
    assert p.emotion == "Happy" and p.confidence == pytest.approx(0.70)
    assert list(p.probabilities) == config.EMOTIONS
    assert sum(p.probabilities.values()) == pytest.approx(1.0, abs=1e-5)
    assert [e for e, _ in p.top3] == ["Happy", "Surprise", "Neutral"]
    assert [v for _, v in p.top3] == sorted([v for _, v in p.top3], reverse=True)


@pytest.mark.parametrize("conf,level", [(0.95, "High"), (config.HIGH_CONFIDENCE, "High"), (0.55, "Moderate"),
                                        (config.MODERATE_CONFIDENCE, "Moderate"), (0.39, "Low"), (0.15, "Low")])
def test_confidence_levels(conf, level):
    assert confidence_level(conf) == level


def test_low_confidence_prediction_carries_warning():
    probs = np.array([0.30, 0.05, 0.25, 0.10, 0.10, 0.10, 0.10])
    p = make_prediction(probs)
    assert p.level == "Low" and "Low-confidence" in p.warning
    assert make_prediction(np.array([0.9, 0, 0, 0.1, 0, 0, 0])).warning is None


def test_model_probabilities_sum_to_one(predictor):
    faces = np.random.default_rng(0).random((3, 48, 48, 1), dtype=np.float32)
    probs = predictor.predict_probabilities(faces)
    assert probs.shape == (3, 7)
    np.testing.assert_allclose(probs.sum(axis=1), 1.0, atol=1e-5)
    assert predictor.predict_probabilities(np.empty((0, 48, 48, 1), np.float32)).shape == (0, 7)


# --- error handling ----------------------------------------------------------
def test_no_face_returns_friendly_message(predictor, blank_image):
    result = predictor.analyze(blank_image)
    assert result.faces == [] and "No face detected" in result.message


def test_whole_image_fallback_returns_one_prediction(predictor, blank_image):
    result = predictor.analyze(blank_image, whole_image_if_no_face=True)
    assert len(result.faces) == 1 and result.faces[0].box is None
    assert result.faces[0].face_input.shape == config.INPUT_SHAPE


@pytest.mark.parametrize("data", [b"", b"not an image at all"])
def test_invalid_image_bytes_raise_clear_error(data):
    with pytest.raises(InvalidImageError):
        decode_image(data)


def test_decode_image_roundtrip():
    ok, buf = cv2.imencode(".png", np.full((20, 30, 3), 200, np.uint8))
    assert decode_image(buf.tobytes()).shape == (20, 30, 3)


def test_missing_model_raises_model_not_found(tmp_path):
    with pytest.raises(ModelNotFoundError):
        load_emotion_model(tmp_path / "missing.keras")


def test_corrupt_model_raises_model_load_error(tmp_path):
    bad = tmp_path / "corrupt.keras"
    bad.write_bytes(b"definitely not a keras archive")
    with pytest.raises(ModelLoadError):
        load_emotion_model(bad)


def test_model_save_and_load_roundtrip(tiny_model, tmp_path):
    path = tmp_path / "m.keras"
    tiny_model.save(path)
    loaded = load_emotion_model(path)
    x = np.random.default_rng(1).random((2, 48, 48, 1), dtype=np.float32)
    np.testing.assert_allclose(loaded(x, training=False), tiny_model(x, training=False), atol=1e-6)


# --- face detection ----------------------------------------------------------
def test_detector_finds_no_face_in_blank_image(blank_image):
    assert FaceDetector().detect(blank_image) == []


def test_crop_face_is_clipped_to_image_bounds():
    img = np.zeros((100, 100, 3), np.uint8)
    # box 90..110 padded by 10 px -> 80..120, clipped at the 100 px border -> 20x20
    assert crop_face(img, (90, 90, 20, 20), padding=0.5).shape == (20, 20, 3)
    assert crop_face(img, (10, 10, 40, 40), padding=0.1).shape == (48, 48, 3)


SLOT_W, SLOT_H, FACE_PX = 220, 260, 160  # each face sits on a white tile with margins


def _tile(fer_test_split, index):
    x, _ = fer_test_split
    face = cv2.resize(x[index], (FACE_PX, FACE_PX), interpolation=cv2.INTER_CUBIC)
    tile = np.full((SLOT_H, SLOT_W, 3), 255, np.uint8)
    top, left = (SLOT_H - FACE_PX) // 2, (SLOT_W - FACE_PX) // 2
    tile[top:top + FACE_PX, left:left + FACE_PX] = cv2.cvtColor(face, cv2.COLOR_GRAY2BGR)
    return tile


def _detectable_indices(fer_test_split, n):
    """First n FER test faces on which the Haar cascade finds exactly one face (same tile layout)."""
    detector, found = FaceDetector(), []
    for i in range(300):
        if len(detector.detect(_tile(fer_test_split, i))) == 1:
            found.append(i)
        if len(found) == n:
            return found
    pytest.skip("not enough detectable FER faces")


def test_multiple_faces_are_detected_and_annotated(predictor, fer_test_split):
    canvas = np.hstack([_tile(fer_test_split, i) for i in _detectable_indices(fer_test_split, 3)])
    result = predictor.analyze(canvas)
    assert len(result.faces) == 3
    assert [f.box[0] for f in result.faces] == sorted(f.box[0] for f in result.faces)  # left to right
    for f in result.faces:
        assert f.face_input.shape == config.INPUT_SHAPE and len(f.top3) == 3
    annotated = annotate_image(canvas, result.faces)
    assert annotated.shape == canvas.shape and not np.array_equal(annotated, canvas)


# --- Grad-CAM and analytics -------------------------------------------------
def test_gradcam_layer_detection_and_heatmap(tiny_model):
    assert find_last_conv_layer(tiny_model) == GRADCAM_LAYER
    face = np.random.default_rng(2).random(config.INPUT_SHAPE, dtype=np.float32)
    heat, cls, probs = GradCAM(tiny_model).heatmap(face)
    assert heat.shape == (48, 48) and 0.0 <= heat.min() and heat.max() <= 1.0
    assert 0 <= cls < 7 and probs.shape == (7,)
    overlay = overlay_heatmap((face[..., 0] * 255).astype(np.uint8), heat, size=96)
    assert overlay.shape == (96, 96, 3) and overlay.dtype == np.uint8


def test_session_summary():
    history = [{"emotion": "Happy", "confidence": 0.9}, {"emotion": "Happy", "confidence": 0.7},
               {"emotion": "Sad", "confidence": 0.3}]
    s = summarize_session(history)
    assert s["predictions"] == 3 and s["dominant"] == "Happy"
    assert s["counts"]["Happy"] == 2 and s["counts"]["Disgust"] == 0 and list(s["counts"]) == config.EMOTIONS
    assert s["average_confidence"] == pytest.approx(0.6333, abs=1e-3)
    assert s["low_confidence_share"] == pytest.approx(1 / 3)
    assert summarize_session([])["dominant"] is None
