# EmotionSense inference API — Docker image (Hugging Face Spaces, or any Docker host).
#
# Build context = repository root (or the folder made by inference_api/build_space.py,
# which has the same layout):
#     docker build -f inference_api/Dockerfile -t emotionsense-api .
#     docker run -p 7860:7860 -e FIREBASE_PROJECT_ID=... -e ALLOWED_ORIGINS=... emotionsense-api
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    TF_ENABLE_ONEDNN_OPTS=0 \
    HOME=/home/user \
    KERAS_HOME=/home/user/.keras \
    PORT=7860

# Hugging Face Spaces runs containers as uid 1000.
RUN useradd --create-home --uid 1000 user
WORKDIR /app

COPY inference_api/requirements.txt inference_api/requirements.txt
RUN pip install --no-cache-dir -r inference_api/requirements.txt

# Only what inference needs: the unchanged pipeline modules and the trained model.
COPY src/__init__.py src/config.py src/face_detector.py src/preprocessing.py src/predict.py src/gradcam.py src/
COPY models/emotion_model.keras models/emotion_model.keras
COPY inference_api/__init__.py inference_api/main.py inference_api/auth.py inference_api/errors.py \
     inference_api/settings.py inference_api/

USER user
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"7860\")}/api/health')"
CMD ["sh", "-c", "uvicorn inference_api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
