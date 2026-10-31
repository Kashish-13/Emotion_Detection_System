"""Model resources, loaded once per server process."""
import streamlit as st

from src.predict import EmotionPredictor, ModelLoadError, ModelNotFoundError


@st.cache_resource(show_spinner="Loading the emotion model…")
def get_predictor():
    """Returns (predictor, error_message)."""
    try:
        return EmotionPredictor(), None
    except (ModelNotFoundError, ModelLoadError, RuntimeError) as err:
        return None, str(err)


@st.cache_resource(show_spinner=False)
def get_gradcam(_model):
    from src.gradcam import GradCAM

    return GradCAM(_model)


def model_missing(error: str) -> None:
    st.error("The emotion model could not be loaded.", icon=":material/error:")
    st.code(error)
    st.markdown("Train it with `python -m src.train`, or place `emotion_model.keras` in `models/` (see README).")
