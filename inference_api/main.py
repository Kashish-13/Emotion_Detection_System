"""EmotionSense inference API: the existing ``src/`` prediction pipeline behind a small HTTP API.

The pipeline is reused unchanged (``src.predict.EmotionPredictor``): Haar face detection ->
padded crop -> grayscale -> 48x48 (INTER_AREA) -> /255 -> CNN -> softmax, plus Grad-CAM from
``src.gradcam``. This module only adds HTTP, validation, authentication and JSON.

Run locally (from the repository root):
    uvicorn inference_api.main:app --reload --port 8000
"""
import base64
import io
import logging
import threading
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from inference_api.auth import current_user
from inference_api.errors import ApiError
from inference_api.settings import Settings, get_settings
from src import config
from src.predict import (AnalysisResult, FacePrediction, InvalidImageError, ModelLoadError, ModelNotFoundError,
                         annotate_image, decode_image)

log = logging.getLogger("inference_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP"}
MAX_PREVIEW_SIDE = 1280  # annotated image returned to the browser is downscaled to this


class Model:
    """The predictor and Grad-CAM, loaded once per process. TensorFlow calls are serialised."""

    def __init__(self):
        self.predictor = None
        self.gradcam = None
        self.error: str | None = None
        self.lock = threading.Lock()

    def load(self) -> None:
        try:
            from src.gradcam import GradCAM
            from src.predict import EmotionPredictor

            self.predictor = EmotionPredictor()
            self.gradcam = GradCAM(self.predictor.model)
            log.info("Model loaded from %s", config.MODEL_PATH)
        except (ModelNotFoundError, ModelLoadError, RuntimeError) as err:
            self.error = str(err)
            log.exception("Model failed to load")

    @property
    def ready(self) -> bool:
        return self.predictor is not None


MODEL = Model()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    MODEL.load()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="EmotionSense inference API", version="1.0.0", lifespan=lifespan,
                  docs_url="/docs", redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=settings.allowed_origin_regex,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, err: ApiError):
        return JSONResponse(status_code=err.status, content={"error": {"code": err.code, "message": err.message}})

    @app.exception_handler(Exception)
    async def _unexpected(_request: Request, err: Exception):
        log.exception("Unexpected error: %s", err)
        return JSONResponse(status_code=500, content={"error": {
            "code": "internal", "message": "Something went wrong while analysing the image. Please try again."}})

    @app.get("/")
    def root():
        return {"service": "EmotionSense inference API", "docs": "/docs", "health": "/api/health"}

    @app.get("/api/health")
    def health():
        return {"status": "ok" if MODEL.ready else "unavailable", "modelLoaded": MODEL.ready,
                "labels": config.EMOTIONS, "inputShape": list(config.INPUT_SHAPE)}

    @app.post("/api/predict")
    def predict(file: UploadFile = File(...), whole_image: bool = Form(False), gradcam: bool = Form(False),
                settings: Settings = Depends(get_settings), _uid: str | None = Depends(current_user)):
        if not MODEL.ready:
            raise ApiError(503, "model_unavailable", "The emotion model is not available right now. Please try later.")
        started = time.perf_counter()
        image = _read_image(file, settings)
        with MODEL.lock:
            result = MODEL.predictor.analyze(image, whole_image_if_no_face=whole_image)
            faces = result.faces[:settings.max_faces]
            cams = [_gradcam(face) for face in faces] if gradcam else [None] * len(faces)
        return _response(image, result, faces, cams, started, truncated=len(result.faces) > len(faces))

    return app


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _read_image(file: UploadFile, settings: Settings) -> np.ndarray:
    data = file.file.read(settings.max_upload_bytes + 1)
    if not data:
        raise ApiError(400, "empty_file", "The uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise ApiError(413, "file_too_large", f"Images must be smaller than {settings.max_upload_mb:g} MB.")

    # Check the real format and size from the header before decoding (guards against
    # mislabelled files and "decompression bombs" that expand to huge images).
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as header:
            fmt, (width, height) = header.format, header.size
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ApiError(400, "invalid_image", "The file could not be read as an image. Please upload a JPG or PNG photo.")
    if fmt not in ALLOWED_FORMATS:
        raise ApiError(415, "unsupported_type", "Please upload a JPG, PNG, WebP or BMP image.")
    if width * height > settings.max_image_pixels:
        raise ApiError(413, "image_too_large", "This image's dimensions are too large. Please use a smaller photo.")

    try:
        return decode_image(data)  # the same decoder the Streamlit app uses
    except InvalidImageError as err:
        raise ApiError(400, "invalid_image", str(err)) from err


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------
def _data_url(image_bgr: np.ndarray, fmt: str = ".png", quality: int = 85) -> str:
    params = [cv2.IMWRITE_JPEG_QUALITY, quality] if fmt == ".jpg" else []
    ok, buf = cv2.imencode(fmt, image_bgr, params)
    if not ok:
        raise RuntimeError("image encoding failed")
    mime = "image/jpeg" if fmt == ".jpg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(buf.tobytes()).decode()}"


def _gradcam(face: FacePrediction) -> dict:
    from src.gradcam import overlay_heatmap

    heat, _, _ = MODEL.gradcam.heatmap(face.face_input)
    face_u8 = (face.face_input[..., 0] * 255).astype(np.uint8)
    model_input = cv2.resize(face_u8, (192, 192), interpolation=cv2.INTER_CUBIC)
    overlay_rgb = overlay_heatmap(face_u8, heat)
    return {"heatmap": _data_url(overlay_rgb[:, :, ::-1]), "modelInput": _data_url(model_input)}


def _response(image: np.ndarray, result: AnalysisResult, faces: list[FacePrediction], cams: list,
              started: float, truncated: bool) -> dict:
    annotated = annotate_image(image, faces)
    h, w = annotated.shape[:2]
    scale = min(1.0, MAX_PREVIEW_SIDE / max(h, w))
    if scale < 1.0:
        annotated = cv2.resize(annotated, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    message = result.message
    if truncated:
        message = f"Showing the first {len(faces)} of {len(result.faces)} faces."
    return {
        "faces": [{
            "index": i,
            "box": dict(zip(("x", "y", "width", "height"), map(int, face.box))) if face.box else None,
            "emotion": face.emotion,
            "confidence": round(face.confidence, 6),
            "level": face.level,
            "probabilities": {e: round(p, 6) for e, p in face.probabilities.items()},
            "top3": [{"emotion": e, "probability": round(p, 6)} for e, p in face.top3],
            "smallFace": face.small_face,
            "warning": face.warning,
            "gradcam": cam,
        } for i, (face, cam) in enumerate(zip(faces, cams), start=1)],
        "message": message,
        "image": {"width": int(image.shape[1]), "height": int(image.shape[0])},
        "annotatedImage": _data_url(annotated, ".jpg"),
        "labels": config.EMOTIONS,
        "timingMs": round((time.perf_counter() - started) * 1000, 1),
    }


app = create_app()
