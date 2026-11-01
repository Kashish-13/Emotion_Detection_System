# EmotionSense inference API

A small FastAPI service around the project's **existing, unchanged** prediction pipeline (`src/predict.py`,
`src/gradcam.py`, `models/emotion_model.keras`). It serves the Vercel web app (`../web`).

Why a separate service: TensorFlow (over 1 GB installed) does not fit Vercel's ~250 MB Python function limit,
and Grad-CAM needs TensorFlow gradients. Hugging Face Spaces (Docker, free CPU tier, 16 GB RAM) runs it as-is.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | `{status, modelLoaded, labels, inputShape}` |
| POST | `/api/predict` | multipart `file` (JPG/PNG/WebP/BMP, ≤ 5 MB, ≤ 25 MP); form `whole_image`, `gradcam` (`true`/`false`); header `Authorization: Bearer <Firebase ID token>` |
| GET | `/docs` | interactive OpenAPI docs |

Response: `faces[]` (box, emotion, confidence, level, all 7 probabilities, top-3, warning, optional Grad-CAM
images), `message`, `image` size, `annotatedImage` (JPEG data URL), `labels`, `timingMs`.
Errors are JSON `{"error": {"code", "message"}}` with safe messages; internals are only logged.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `FIREBASE_PROJECT_ID` | — | Firebase project whose ID tokens are accepted (required when auth is on) |
| `REQUIRE_AUTH` | `true` | set `false` only for local development |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | comma-separated browser origins, e.g. your Vercel URL |
| `ALLOWED_ORIGIN_REGEX` | — | optional, for Vercel preview URLs, e.g. `^https://emotionsense-[a-z0-9-]+\.vercel\.app$` |
| `MAX_UPLOAD_MB` / `MAX_IMAGE_PIXELS` / `MAX_FACES` | `5` / `25000000` / `10` | limits |

Token verification uses Google's public certificates; no service-account key or other secret is needed.

## Run and test locally (repository root)

```bash
.venv\Scripts\activate
pip install -r inference_api/requirements.txt
set REQUIRE_AUTH=false
uvicorn inference_api.main:app --port 8000      # http://localhost:8000/docs
pytest inference_api/tests -q                   # 12 tests, real model
```

## Deploy to Hugging Face Spaces

```bash
pip install -U huggingface_hub
hf auth login                                   # token with "write" access (huggingface.co/settings/tokens)
python -m inference_api.build_space             # -> dist/hf-space (Dockerfile at its root)
hf repos create <hf-username>/emotionsense-api --repo-type space --space-sdk docker
hf upload <hf-username>/emotionsense-api dist/hf-space . --repo-type space
```

Then in the Space: **Settings → Variables and secrets** → add `FIREBASE_PROJECT_ID` and `ALLOWED_ORIGINS`
(your Vercel URL). The build takes a few minutes; check `https://<hf-username>-emotionsense-api.hf.space/api/health`.
Free Spaces sleep after ~48 h without traffic; the first request afterwards takes longer.

The same Dockerfile works on any Docker host: `docker build -f inference_api/Dockerfile -t emotionsense-api .`
