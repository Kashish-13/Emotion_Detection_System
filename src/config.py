"""Central configuration for the Emotion Detection System.

Every path, hyperparameter and application threshold lives here so the rest
of the code never hard-codes "magic numbers".
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
FER_CSV_PATH = DATA_DIR / "fer2013" / "fer2013.csv"  # canonical on-disk format
FER_FOLDER_DIR = DATA_DIR / "fer2013"                 # alt: Kaggle train/ test/ folders
HF_PARQUET_DIR = DATA_DIR / "raw_hf"                  # optional raw download location
MODELS_DIR = ROOT_DIR / "models"
RESULTS_DIR = ROOT_DIR / "results"

MODEL_PATH = MODELS_DIR / "emotion_model.keras"

# ---------------------------------------------------------------------------
# Labels (FER-2013 index order — do not reorder)
# ---------------------------------------------------------------------------
EMOTIONS = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]
NUM_CLASSES = len(EMOTIONS)

# ---------------------------------------------------------------------------
# Image / preprocessing
# ---------------------------------------------------------------------------
IMG_SIZE = 48          # FER-2013 native resolution
IMG_CHANNELS = 1       # grayscale
INPUT_SHAPE = (IMG_SIZE, IMG_SIZE, IMG_CHANNELS)

# Augmentation (training only). Kept mild so the expression is not altered.
AUG_ROTATION = 10 / 360   # RandomRotation uses fractions of a full turn (~10 degrees)
AUG_ZOOM = 0.10
AUG_TRANSLATE = 0.10
AUG_BRIGHTNESS = 0.10     # +/- 10% of the [0, 1] range
AUG_CONTRAST = 0.10

# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
SEED = 42
# Conv filters per block. CPU benchmark (Ryzen 5 5600H, batch 64):
#   (32,64,128,256) 1.24M params ~156 s/epoch | (24,48,96,192) 0.71M ~97 s/epoch | (16,32,64,128) 0.33M ~55 s/epoch
CNN_FILTERS = (24, 48, 96, 192)
BATCH_SIZE = 64
EPOCHS = 50
LEARNING_RATE = 1e-3
EARLY_STOPPING_PATIENCE = 8
REDUCE_LR_PATIENCE = 3
REDUCE_LR_FACTOR = 0.5
MIN_LR = 1e-6
VAL_SPLIT = 0.1  # only used when the dataset has no predefined validation split

# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------
BLANK_STD_THRESHOLD = 1.0  # images with pixel std below this contain no face (see EDA)

# ---------------------------------------------------------------------------
# Face detection (OpenCV Haar cascade)
# ---------------------------------------------------------------------------
HAAR_CASCADE_FILE = "haarcascade_frontalface_default.xml"  # bundled with opencv-python 4.x
FACE_SCALE_FACTOR = 1.1
FACE_MIN_NEIGHBORS = 5
MIN_DETECT_FACE_SIZE = 30  # px; smaller detections are ignored as likely false positives
SMALL_FACE_SIZE = 48       # px; faces below the model's native resolution get a warning
FACE_PADDING = 0.10        # extra margin around the detected box before cropping

# ---------------------------------------------------------------------------
# Application confidence heuristics (NOT scientifically validated thresholds)
# Chosen from the validation-set reliability analysis in results/metrics.json:
# accuracy of predictions inside each confidence band.
# ---------------------------------------------------------------------------
HIGH_CONFIDENCE = 0.70
MODERATE_CONFIDENCE = 0.40

# ---------------------------------------------------------------------------
# Webcam
# ---------------------------------------------------------------------------
WEBCAM_INDEX = 0
WEBCAM_DETECTION_DOWNSCALE = 0.5   # run face detection on a half-size frame
WEBCAM_PREDICT_EVERY_N_FRAMES = 3  # reuse the last prediction in between (saves CPU)
WEBCAM_LOG_INTERVAL_S = 1.0        # add at most one entry per face per second to session analytics
SESSION_HISTORY_SIZE = 500         # max predictions kept for session analytics

# ---------------------------------------------------------------------------
# EmotionSense application
# ---------------------------------------------------------------------------
APP_NAME = "EmotionSense"
APP_TAGLINE = "Understand your expression. Reflect. Take a mindful step."
ASSETS_DIR = ROOT_DIR / "assets"

# Accent colour per expression. Validated as an ordered categorical palette (light and
# dark) with the data-viz palette validator; charts always label emotions directly,
# so colour is never the only cue.
EMOTION_COLORS = {
    "Angry": "#e34948", "Disgust": "#008300", "Fear": "#6250d6", "Happy": "#eda100",
    "Sad": "#2a78d6", "Surprise": "#eb6834", "Neutral": "#1baf7a",
}

# Firebase (Authentication + Firestore). Values come from .streamlit/secrets.toml
# ([firebase] api_key / project_id) or the environment variables below — never from code.
FIREBASE_API_KEY_ENV = "FIREBASE_API_KEY"
FIREBASE_PROJECT_ID_ENV = "FIREBASE_PROJECT_ID"
FIREBASE_TIMEOUT_S = 10
HISTORY_COLLECTION = "checkins"    # stored at users/{uid}/checkins/{id}
HISTORY_FETCH_LIMIT = 500          # newest entries loaded for dashboards
