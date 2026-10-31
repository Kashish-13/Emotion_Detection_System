"""Inference pipeline: image -> faces -> emotion probabilities.

    image (BGR) -> Haar face detection -> crop (+padding) -> grayscale -> 48x48
    -> /255 -> CNN -> softmax probabilities -> top-3 + confidence level

The preprocessing is ``src.preprocessing.preprocess_face``, the same
``to_model_input`` function used during training.

Example:
    python -m src.predict path/to/photo.jpg
"""
import argparse
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from src import config
from src.face_detector import Box, FaceDetector, crop_face
from src.preprocessing import preprocess_face

# Box colours (BGR) by confidence level. The label text also states the level,
# so colour is never the only signal.
LEVEL_COLORS = {"High": (60, 160, 40), "Moderate": (0, 165, 235), "Low": (60, 60, 220)}


class ModelNotFoundError(FileNotFoundError):
    """The trained model file does not exist."""


class ModelLoadError(RuntimeError):
    """The model file exists but could not be loaded."""


class InvalidImageError(ValueError):
    """The input could not be decoded as an image."""


@dataclass
class FacePrediction:
    box: Box | None                 # None when the whole image was used as the face
    emotion: str
    confidence: float
    level: str                      # "High" / "Moderate" / "Low" (application heuristic)
    probabilities: dict[str, float]  # all 7 emotions, in config.EMOTIONS order
    top3: list[tuple[str, float]]
    small_face: bool = False
    face_input: np.ndarray | None = field(default=None, repr=False)  # the exact 48x48x1 model input

    @property
    def warning(self) -> str | None:
        notes = []
        if self.level == "Low":
            notes.append("Low-confidence prediction. Consider using a clearer, front-facing image.")
        if self.small_face:
            notes.append(f"Face is smaller than {config.SMALL_FACE_SIZE}px, so detail is limited.")
        return " ".join(notes) or None


@dataclass
class AnalysisResult:
    faces: list[FacePrediction] = field(default_factory=list)
    message: str | None = None      # user-facing note, e.g. when no face was found


def confidence_level(confidence: float) -> str:
    """Map a softmax probability to an application confidence band (heuristic)."""
    if confidence >= config.HIGH_CONFIDENCE:
        return "High"
    if confidence >= config.MODERATE_CONFIDENCE:
        return "Moderate"
    return "Low"


def load_emotion_model(path: Path = config.MODEL_PATH):
    """Load a saved Keras model with clear errors for the two common failures."""
    path = Path(path)
    if not path.is_file():
        raise ModelNotFoundError(
            f"Model file not found: {path}\n"
            "Fix: train it with `python -m src.train` (see README), or place emotion_model.keras in models/."
        )
    from tensorflow import keras  # imported lazily: TensorFlow import is slow

    try:
        return keras.models.load_model(path)
    except Exception as err:  # corrupted file, incompatible Keras version, ...
        raise ModelLoadError(f"Could not load model from {path}: {err}") from err


def decode_image(data: bytes) -> np.ndarray:
    """Decode uploaded bytes (JPG/PNG/...) into a BGR image."""
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR) if data else None
    if image is None:
        raise InvalidImageError("The file could not be read as an image. Please upload a JPG or PNG photo.")
    return image


def make_prediction(probs: np.ndarray, box: Box | None = None, small_face: bool = False,
                    face_input: np.ndarray | None = None) -> FacePrediction:
    """Turn one softmax vector into a FacePrediction."""
    order = np.argsort(probs)[::-1]
    best = int(order[0])
    return FacePrediction(
        box=box,
        emotion=config.EMOTIONS[best],
        confidence=float(probs[best]),
        level=confidence_level(float(probs[best])),
        probabilities={e: float(p) for e, p in zip(config.EMOTIONS, probs)},
        top3=[(config.EMOTIONS[i], float(probs[i])) for i in order[:3]],
        small_face=small_face,
        face_input=face_input,
    )


class EmotionPredictor:
    """Loads the model and face detector once; reuse for many images or frames."""

    def __init__(self, model=None, model_path: Path = config.MODEL_PATH, detector: FaceDetector | None = None):
        self.model = model if model is not None else load_emotion_model(model_path)
        self.detector = detector or FaceDetector()

    def predict_probabilities(self, faces: np.ndarray) -> np.ndarray:
        """(N, 48, 48, 1) preprocessed faces -> (N, 7) probabilities."""
        if len(faces) == 0:
            return np.empty((0, config.NUM_CLASSES), dtype=np.float32)
        # Calling the model directly is much faster than model.predict() for small batches.
        return np.asarray(self.model(faces, training=False))

    def analyze(self, image: np.ndarray, whole_image_if_no_face: bool = False,
                detection_downscale: float = 1.0) -> AnalysisResult:
        """Detect every face in a BGR image and classify its expression."""
        if image is None or image.size == 0 or image.ndim not in (2, 3):
            raise InvalidImageError("Empty or invalid image.")

        boxes = self.detector.detect(image, downscale=detection_downscale)
        if not boxes:
            if not whole_image_if_no_face:
                return AnalysisResult(message=(
                    "No face detected. Try a well-lit, front-facing photo where the face is clearly visible, "
                    "or enable 'treat the whole image as one face' for an already-cropped face."))
            h, w = image.shape[:2]
            face = preprocess_face(image)
            probs = self.predict_probabilities(face[np.newaxis])[0]
            return AnalysisResult(
                faces=[make_prediction(probs, None, min(h, w) < config.SMALL_FACE_SIZE, face)],
                message="No face detected, so the whole image was treated as one face.")

        crops = np.stack([preprocess_face(crop_face(image, box)) for box in boxes])
        probs = self.predict_probabilities(crops)
        faces = [make_prediction(p, box, min(box[2:]) < config.SMALL_FACE_SIZE, crop)
                 for p, box, crop in zip(probs, boxes, crops)]
        return AnalysisResult(faces=faces)


def annotate_image(image: np.ndarray, faces: list[FacePrediction]) -> np.ndarray:
    """Draw a box and an 'EMOTION 91%' label above every detected face (returns a copy)."""
    out = image.copy() if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    scale = max(0.5, min(out.shape[:2]) / 900)
    thickness = max(1, int(round(2 * scale)))
    for i, face in enumerate(faces, start=1):
        if face.box is None:
            continue
        x, y, w, h = face.box
        color = LEVEL_COLORS[face.level]
        cv2.rectangle(out, (x, y), (x + w, y + h), color, thickness + 1)
        label = f"#{i} {face.emotion.upper()} {face.confidence:.0%}"
        if face.level == "Low":
            label += " (low conf.)"
        (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6 * scale, thickness)
        top = y - th - base - 6 if y - th - base - 6 > 0 else y + h  # keep label inside the image
        cv2.rectangle(out, (x, top), (x + tw + 8, top + th + base + 6), color, -1)
        cv2.putText(out, label, (x + 4, top + th + 3), cv2.FONT_HERSHEY_SIMPLEX, 0.6 * scale,
                    (255, 255, 255), thickness, cv2.LINE_AA)
    return out


def main():
    parser = argparse.ArgumentParser(description="Predict facial expressions in an image.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--whole-image", action="store_true", help="treat the image as one face if none is found")
    parser.add_argument("--save", type=Path, help="write the annotated image to this path")
    args = parser.parse_args()

    try:
        predictor = EmotionPredictor()
        result = predictor.analyze(decode_image(args.image.read_bytes()), args.whole_image)
    except (ModelNotFoundError, ModelLoadError, InvalidImageError, FileNotFoundError) as err:
        print(err)
        raise SystemExit(1)

    if result.message:
        print(result.message)
    for i, face in enumerate(result.faces, start=1):
        alts = ", ".join(f"{e} {p:.0%}" for e, p in face.top3[1:])
        print(f"Face #{i} {face.box}: {face.emotion} {face.confidence:.1%} ({face.level} confidence); "
              f"alternatives: {alts}")
        if face.warning:
            print(f"  Warning: {face.warning}")
    if args.save and result.faces:
        cv2.imwrite(str(args.save), annotate_image(decode_image(args.image.read_bytes()), result.faces))
        print(f"Saved {args.save}")


if __name__ == "__main__":
    main()
