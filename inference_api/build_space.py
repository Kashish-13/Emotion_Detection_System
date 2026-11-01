"""Assemble the Hugging Face Space folder for the inference API.

    python -m inference_api.build_space            # -> dist/hf-space/

The folder has the Dockerfile at its root (as Spaces require) and the same layout as the
repository, so the one Dockerfile works for both. Upload it with:

    hf upload <your-username>/emotionsense-api dist/hf-space . --repo-type space
"""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    "src/__init__.py", "src/config.py", "src/face_detector.py", "src/preprocessing.py", "src/predict.py",
    "src/gradcam.py", "models/emotion_model.keras",
    "inference_api/__init__.py", "inference_api/main.py", "inference_api/auth.py", "inference_api/errors.py",
    "inference_api/settings.py", "inference_api/requirements.txt",
]

SPACE_README = """---
title: EmotionSense API
emoji: 🙂
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: Facial-expression recognition API (FER-2013 CNN)
---

# EmotionSense inference API

FastAPI service for the EmotionSense web app. It runs the project's existing pipeline unchanged
(Haar face detection, padded crop, grayscale, 48x48, /255, custom CNN) and returns the predicted
expression, confidence, top-3, all seven probabilities and optional Grad-CAM.

- `GET /api/health`: model status
- `POST /api/predict`: multipart `file` (JPG/PNG/WebP/BMP, max 5 MB); optional form fields
  `whole_image`, `gradcam`; header `Authorization: Bearer <Firebase ID token>`

Configure in **Settings -> Variables**: `FIREBASE_PROJECT_ID`, `ALLOWED_ORIGINS`
(and optionally `ALLOWED_ORIGIN_REGEX`). Facial expressions are not a measure of emotion;
this is not a diagnostic tool.
"""


def build(out: Path) -> Path:
    if out.exists():
        shutil.rmtree(out)
    for rel in FILES:
        src = ROOT / rel
        if not src.is_file():
            raise SystemExit(f"Missing {rel}. Is the trained model in models/?")
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    shutil.copy2(ROOT / "inference_api" / "Dockerfile", out / "Dockerfile")
    (out / "README.md").write_text(SPACE_README, encoding="utf-8")
    (out / ".gitattributes").write_text("*.keras filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "hf-space")
    print(f"Space folder ready: {build(parser.parse_args().out)}")
