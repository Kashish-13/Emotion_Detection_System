import os
import sys
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402


@pytest.fixture(scope="session")
def tiny_model():
    """A very small, untrained CNN with the real architecture; enough to test plumbing."""
    from src.model import build_cnn

    return build_cnn(filters=(4, 4, 4, 4))


@pytest.fixture(scope="session")
def predictor(tiny_model):
    from src.predict import EmotionPredictor

    return EmotionPredictor(model=tiny_model)


@pytest.fixture(scope="session")
def fer_test_split():
    """Real FER-2013 test images (skips the test if the dataset is not available locally)."""
    from src.data_loader import DatasetNotFoundError, load_fer2013

    try:
        return load_fer2013()["test"]
    except DatasetNotFoundError:
        pytest.skip("FER-2013 not available locally")


@pytest.fixture
def blank_image():
    return np.full((240, 320, 3), 127, dtype=np.uint8)


def pytest_report_header():
    return f"model path: {config.MODEL_PATH}"
