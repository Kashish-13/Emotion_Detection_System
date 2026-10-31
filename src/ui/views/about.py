"""About & Privacy."""
import streamlit as st

from src import config
from src.ui import components as ui
from src.wellbeing import DISCLAIMER, DISTRESS_NOTE

FLOW = ["Image / webcam", "Face detection", "Preprocessing", "CNN", "Emotion probabilities", "Top prediction",
        "Optional wellbeing reflection"]


def render() -> None:
    ui.page_header(f"About {config.APP_NAME}", config.APP_TAGLINE, eyebrow="About")

    st.markdown("#### What is EmotionSense?")
    st.markdown(
        "EmotionSense combines a **facial-expression recognition model** with a small set of **reflection and "
        "wellbeing tools**. The model looks at a face and estimates which of seven expressions it shows. The rest "
        "of the app turns that into an invitation to check in with yourself — in your own words.")

    st.markdown("#### How it works")
    flow = '<span class="arrow">→</span>'.join(f'<span class="step">{s}</span>' for s in FLOW)
    st.html(f'<div class="es-flow">{flow}</div>')
    st.markdown(
        "1. **Face detection**: OpenCV's Haar cascade finds each face.\n"
        "2. **Preprocessing**: crop → grayscale → 48×48 → scale to [0, 1] — identical to training.\n"
        "3. **CNN**: a custom convolutional network trained on FER-2013 outputs a probability for each of 7 "
        "expressions: " + ", ".join(config.EMOTIONS) + ".\n"
        "4. **Result**: the top prediction, its confidence band and the top-3 alternatives, with a Grad-CAM view "
        "of where the model looked.\n"
        "5. **Reflection (optional)**: check-ins, journaling and short wellbeing activities.")

    st.markdown("#### Technology")
    st.markdown("Python · TensorFlow / Keras · OpenCV · Streamlit · Altair · Firebase Authentication & Firestore "
                "· FER-2013")

    lim, priv = st.columns(2, gap="large")
    with lim:
        with st.container(border=True):
            st.markdown("##### Limitations")
            st.markdown(
                "- **A facial expression is not an emotion.** People smile when sad and look neutral when happy.\n"
                "- Lighting, head pose, glasses and image quality change predictions.\n"
                "- FER-2013 is low-resolution, has noisy labels and an undocumented demographic mix; performance "
                "may differ across groups.\n"
                "- The model can be uncertain — low-confidence results are flagged, not hidden.\n"
                "- **Not a medical or diagnostic tool.** It cannot detect stress, anxiety, depression or any "
                "mental-health condition.")
    with priv:
        with st.container(border=True):
            st.markdown("##### Privacy")
            st.markdown(
                "- **Images and webcam frames are never stored.** They are analysed in memory and discarded.\n"
                "- When you choose **Save**, only the detected expression, confidence and top-3 predictions are "
                "stored — plus your mood and note if you add them.\n"
                "- Data is stored in **your own space** (`users/{your-id}/checkins`). Firestore security rules "
                "allow only you to read or write it.\n"
                "- **Guest mode** stores nothing beyond this browser session.\n"
                "- You can delete any entry, or all your history, on **History & Insights**.")

    st.info(DISCLAIMER, icon=":material/info:")
    st.caption(DISTRESS_NOTE)
