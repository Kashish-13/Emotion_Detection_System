"""Model Insights: the technical ML story, every number read from results/ (never typed in)."""
import json

import pandas as pd
import streamlit as st

from src import config
from src.ui import components as ui


@st.cache_data
def _load(name: str):
    path = config.RESULTS_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _image(name: str, caption: str | None = None) -> None:
    path = config.RESULTS_DIR / name
    if path.is_file():
        st.image(str(path), caption=caption, width="stretch")
    else:
        st.info(f"`results/{name}` not found — run training/evaluation to generate it.")


def render() -> None:
    ui.page_header("Model insights", "How the facial-expression model was built and how well it performs.",
                   eyebrow="Machine learning")
    metrics, summary = _load("metrics.json"), _load("training_summary.json")
    if not metrics:
        st.info("No evaluation results yet. Run `python -m src.evaluate`.")
        return
    off, clean = metrics["official_test"], metrics["leakage_aware_test"]

    st.markdown("#### Leakage-aware test set — the headline numbers")
    st.caption(f"{clean['n']:,} test images that appear in neither the training nor the validation set.")
    c = st.columns(4)
    with c[0]:
        ui.stat_card("Accuracy", f"{clean['accuracy']:.1%}")
    with c[1]:
        ui.stat_card("Macro F1", f"{clean['macro_f1']:.3f}", "Every class weighted equally")
    with c[2]:
        ui.stat_card("Weighted F1", f"{clean['weighted_f1']:.3f}")
    with c[3]:
        base = metrics["baseline_always_happy_official_test"]
        ui.stat_card("Baseline accuracy", f"{base['accuracy']:.1%}", "Always predicting 'Happy'")

    st.markdown("#### Official FER-2013 test set")
    c = st.columns(4)
    with c[0]:
        ui.stat_card("Accuracy", f"{off['accuracy']:.1%}", f"{off['n']:,} images")
    with c[1]:
        ui.stat_card("Macro F1", f"{off['macro_f1']:.3f}")
    with c[2]:
        ui.stat_card("Weighted F1", f"{off['weighted_f1']:.3f}")
    with c[3]:
        ui.stat_card("Top-3 accuracy", f"{metrics['top3_accuracy_official_test']:.1%}", "True label in top 3")

    rows = {"Official test": off, "Leakage-aware test": clean,
            "Test images also seen in train/val": metrics["test_images_seen_in_train_or_val"],
            "Baseline: always 'Happy'": base}
    table = pd.DataFrame(rows).T[["n", "accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1"]]
    st.dataframe(table.style.format({"n": "{:,.0f}", **{k: "{:.3f}" for k in table.columns if k != "n"}}),
                 width="stretch")

    why, leak = st.columns(2, gap="large")
    with why:
        with st.container(border=True):
            st.markdown("##### Why accuracy isn't enough")
            st.markdown(
                "FER-2013 is imbalanced: **Disgust** has 16.5× fewer training images than **Happy**. A model that "
                f"always says *Happy* already scores **{base['accuracy']:.1%} accuracy**, yet its macro F1 is only "
                f"**{base['macro_f1']:.3f}**. **Macro F1** averages the F1 score of every class equally, so ignoring "
                "rare classes is penalised. Training used balanced class weights and selected the checkpoint by "
                "validation macro F1.")
    with leak:
        with st.container(border=True):
            st.markdown("##### Honest evaluation: data leakage")
            seen = metrics["test_images_seen_in_train_or_val"]
            st.markdown(
                "About 8% of FER-2013's official test images are exact pixel copies of training images. On those "
                f"{seen['n']} images the model scores **{seen['accuracy']:.1%}**, versus **{clean['accuracy']:.1%}** "
                "on unseen images — memorisation inflates the official score. Both evaluations are reported; the "
                "leakage-aware one is the headline.")

    st.markdown("#### Architecture")
    if summary:
        st.markdown(
            f"Custom VGG-style CNN · **{summary['parameters']:,} parameters** · {summary['model_size_mb']} MB · "
            f"trained on CPU in {summary['training_minutes']} min · best epoch **{summary['best_epoch']}** of "
            f"{summary['epochs_run']} · inference ≈ {metrics['inference_ms_per_face_cpu']:.0f} ms per face (CPU)")
    st.code("Input 48×48×1 (grayscale, /255)\n"
            "4 × [Conv3×3 → BN → ReLU] ×2  (24 → 48 → 96 → 192 filters), MaxPool + Dropout after blocks 1–3\n"
            "GlobalAveragePooling → Dense 256 → BN → ReLU → Dropout 0.5 → Dense 7 → Softmax", language=None)

    st.markdown("#### Training curves")
    _image("training_curves.png")
    st.markdown("#### Confusion matrices (official test set)")
    a, b = st.columns(2)
    with a:
        _image("confusion_matrix.png")
    with b:
        _image("confusion_matrix_normalized.png")

    st.markdown("#### Class-wise performance")
    _image("per_class_metrics.png")
    per_class = pd.DataFrame(metrics["per_class_official_test"]).T
    per_class["f1 (leakage-aware)"] = pd.DataFrame(metrics["per_class_leakage_aware_test"]).T["f1"]
    st.dataframe(per_class.style.format({"precision": "{:.3f}", "recall": "{:.3f}", "f1": "{:.3f}",
                                         "f1 (leakage-aware)": "{:.3f}"}), width="stretch")

    st.markdown("#### Grad-CAM examples")
    _image("gradcam/gradcam_correct.png")
    _image("gradcam/gradcam_misclassified.png")
    st.caption("Grad-CAM shows which regions increased the predicted class score — where the model looked, "
               "not proof that it is correct.")

    st.markdown("#### Are the confidence bands meaningful? (validation set)")
    rel = pd.DataFrame(metrics["confidence_reliability_validation"]).set_index("bin")
    st.dataframe(rel.style.format({"share_of_predictions": "{:.1%}", "accuracy": "{:.1%}"}), width="stretch")
    st.caption("The High / Moderate / Low bands are application heuristics, not calibrated certainty.")

    st.markdown("#### Dataset imbalance")
    _image("eda_class_distribution.png")
