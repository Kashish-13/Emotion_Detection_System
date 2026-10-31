"""Headless smoke tests of the Streamlit pages (Streamlit's AppTest; no browser needed).

Pages that need the trained model are skipped if models/emotion_model.keras is absent.
"""
import pytest
from streamlit.testing.v1 import AppTest

from src import config

needs_model = pytest.mark.skipif(not config.MODEL_PATH.is_file(), reason="trained model not available")


def _run(page: str) -> AppTest:
    """Render a single page function of app.py (tests run from the project root)."""
    script = (
        "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n"
        f"import app\napp.init_session()\napp.{page}()\n"
    )
    return AppTest.from_string(script, default_timeout=180).run()


@pytest.mark.parametrize("page", ["home_page", "about_page"])
def test_static_pages_render_without_errors(page):
    at = _run(page)
    assert not at.exception
    assert at.title


@needs_model
@pytest.mark.parametrize("page", ["image_page", "insights_page"])
def test_model_pages_render_without_errors(page):
    at = _run(page)
    assert not at.exception
    assert not at.error, [e.value for e in at.error]


@needs_model
def test_webcam_page_is_off_by_default_and_renders():
    at = _run("webcam_page")
    assert not at.exception
    assert at.toggle[0].value is False  # camera is only opened after the user switches it on


# Note: running TensorFlow inference *inside* AppTest makes the pytest process stall at
# interpreter shutdown on Windows (the test itself passes). Prediction, Grad-CAM and the
# result panel are therefore covered by tests/test_inference.py instead of here.
