"""Inference API tests (run: pytest inference_api/tests). Uses the real trained model.

The Streamlit test suite (tests/) is separate and unaffected.
"""
import io

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from inference_api import auth, main
from inference_api.settings import Settings, get_settings
from src import config
from src.predict import EmotionPredictor, decode_image

ROOT = config.ROOT_DIR
DEMO = ROOT / "results" / "demo_multi_face.png"  # four FER-2013 test faces; three are detectable

pytestmark = pytest.mark.skipif(not config.MODEL_PATH.is_file(), reason="trained model not available")


def settings(**overrides) -> Settings:
    base = dict(allowed_origins=["http://localhost:3000"], allowed_origin_regex=None, require_auth=False,
                firebase_project_id="demo-project", max_upload_mb=5, max_image_pixels=25_000_000, max_faces=10)
    return Settings(**{**base, **overrides})


@pytest.fixture(scope="module")
def client():
    app = main.create_app(settings())
    app.dependency_overrides[get_settings] = lambda: settings()
    with TestClient(app) as c:  # runs the lifespan: loads the real model once
        yield c


def png_bytes(image: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", image)
    assert ok
    return buf.tobytes()


def post(client, data: bytes, name="photo.png", ctype="image/png", **form):
    return client.post("/api/predict", files={"file": (name, data, ctype)},
                       data={k: str(v).lower() for k, v in form.items()})


# --- health ---------------------------------------------------------------------------
def test_health_reports_model_and_labels(client):
    body = client.get("/api/health").json()
    assert body["modelLoaded"] is True and body["status"] == "ok"
    assert body["labels"] == config.EMOTIONS and body["inputShape"] == [48, 48, 1]


# --- prediction -------------------------------------------------------------------------
def test_predict_matches_the_existing_pipeline_exactly(client):
    data = DEMO.read_bytes()
    body = post(client, data).json()
    expected = EmotionPredictor(model=main.MODEL.predictor.model).analyze(decode_image(data))
    assert len(body["faces"]) == len(expected.faces) == 3
    for got, want in zip(body["faces"], expected.faces):
        assert got["emotion"] == want.emotion and got["level"] == want.level
        assert got["confidence"] == pytest.approx(want.confidence, abs=1e-5)
        assert [p["emotion"] for p in got["top3"]] == [e for e, _ in want.top3]
        assert list(got["probabilities"]) == config.EMOTIONS
        assert sum(got["probabilities"].values()) == pytest.approx(1.0, abs=1e-4)
        assert got["box"] == dict(zip(("x", "y", "width", "height"), want.box))
    assert body["annotatedImage"].startswith("data:image/jpeg;base64,")
    h, w = decode_image(data).shape[:2]
    assert body["image"] == {"width": w, "height": h}


def test_gradcam_is_returned_only_when_requested(client):
    data = DEMO.read_bytes()
    assert all(f["gradcam"] is None for f in post(client, data).json()["faces"])
    face = post(client, data, gradcam=True).json()["faces"][0]
    assert face["gradcam"]["heatmap"].startswith("data:image/png;base64,")
    assert face["gradcam"]["modelInput"].startswith("data:image/png;base64,")


def test_no_face_gives_friendly_message_and_whole_image_option(client):
    blank = np.full((200, 200, 3), 127, np.uint8)
    body = post(client, png_bytes(blank)).json()
    assert body["faces"] == [] and "No face detected" in body["message"]
    body = post(client, png_bytes(blank), whole_image=True).json()
    assert len(body["faces"]) == 1 and body["faces"][0]["box"] is None


def test_jpeg_and_webp_are_accepted(client):
    rgb = cv2.cvtColor(decode_image(DEMO.read_bytes()), cv2.COLOR_BGR2RGB)
    for fmt, ctype in (("JPEG", "image/jpeg"), ("WEBP", "image/webp")):
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, format=fmt)
        assert post(client, buf.getvalue(), ctype=ctype).status_code == 200


# --- validation ---------------------------------------------------------------------------
def test_rejects_non_images_and_corrupt_files(client):
    for data in (b"not an image at all", b"\x89PNG\r\n\x1a\n" + b"\x00" * 50):
        r = post(client, data)
        assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_image"
    assert post(client, b"").status_code in (400, 422)


def test_rejects_unsupported_formats(client):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64)).save(buf, format="GIF")
    r = post(client, buf.getvalue(), name="x.gif", ctype="image/gif")
    assert r.status_code == 415 and r.json()["error"]["code"] == "unsupported_type"


def test_rejects_files_and_images_that_are_too_large(client):
    app = client.app
    app.dependency_overrides[get_settings] = lambda: settings(max_upload_mb=0.001, max_image_pixels=100)
    try:
        r = post(client, DEMO.read_bytes())
        assert r.status_code == 413 and r.json()["error"]["code"] == "file_too_large"
        app.dependency_overrides[get_settings] = lambda: settings(max_image_pixels=100)
        r = post(client, DEMO.read_bytes())
        assert r.status_code == 413 and r.json()["error"]["code"] == "image_too_large"
    finally:
        app.dependency_overrides[get_settings] = lambda: settings()


def test_errors_never_leak_internals(client, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(main.MODEL.predictor, "analyze", boom)
    r = TestClient(client.app, raise_server_exceptions=False).post(
        "/api/predict", files={"file": ("a.png", DEMO.read_bytes(), "image/png")})
    assert r.status_code == 500 and "secret" not in r.text and r.json()["error"]["code"] == "internal"


# --- authentication -----------------------------------------------------------------------
def test_auth_required_when_enabled(client, monkeypatch):
    app = client.app
    app.dependency_overrides[get_settings] = lambda: settings(require_auth=True)
    seen = {}

    def fake_verify(token, project_id):
        seen["args"] = (token, project_id)
        if token != "good-token":
            raise auth.ApiError(401, "unauthorized", "Your session has expired. Please sign in again.")
        return "uid-123"

    monkeypatch.setattr(auth, "verify_firebase_token", fake_verify)
    try:
        assert post(client, DEMO.read_bytes()).status_code == 401  # no header
        r = client.post("/api/predict", files={"file": ("a.png", DEMO.read_bytes(), "image/png")},
                        headers={"Authorization": "Bearer bad"})
        assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"
        r = client.post("/api/predict", files={"file": ("a.png", DEMO.read_bytes(), "image/png")},
                        headers={"Authorization": "Bearer good-token"})
        assert r.status_code == 200 and seen["args"] == ("good-token", "demo-project")
    finally:
        app.dependency_overrides[get_settings] = lambda: settings()


def test_real_verifier_rejects_garbage_tokens():
    with pytest.raises(auth.ApiError) as err:
        auth.verify_firebase_token("not-a-jwt", "demo-project")
    assert err.value.status == 401


# --- CORS -----------------------------------------------------------------------------------
def test_cors_allows_only_configured_origins(client):
    ok = client.options("/api/predict", headers={"Origin": "http://localhost:3000",
                                                 "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options("/api/predict", headers={"Origin": "https://evil.example",
                                                  "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers
