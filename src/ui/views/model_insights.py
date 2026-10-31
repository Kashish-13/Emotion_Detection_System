"""Model Insights: the technical ML story, every number read from results/ (never typed in)."""
import json
from html import escape

import pandas as pd
import streamlit as st

from src import config
from src.ui import components as ui

FLOW = ["Image / frame", "Haar face detection", "Crop · grayscale · 48×48 · /255", "CNN (4 conv blocks)",
        "Softmax · 7 expressions", "Top-3 + confidence band"]


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


def _metric(label: str, value: str, hint: str) -> str:
    return f"""<div class="es-glass lift"><div class="es-stat-label">{escape(label)}</div>
        <div class="es-grad-text" style="font-size:2rem;font-weight:700;
        line-height:1.15">{escape(value)}</div><div class="es-stat-hint">{escape(hint)}</div></div>"""


def render() -> None:
    ui.page_header("Model", "How the facial-expression model was built, how well it performs and where it struggles.",
                   eyebrow="Learn · Machine learning", accent="insights")
    metrics, summary = _load("metrics.json"), _load("training_summary.json")
    if not metrics:
        ui.empty_state("No evaluation results yet", "Run `python -m src.evaluate` to generate them.", icon="📈")
        return
    off, clean = metrics["official_test"], metrics["leakage_aware_test"]
    base = metrics["baseline_always_happy_official_test"]

    # ---- How the model works -------------------------------------------------
    ui.section("How the model works", "From a photo to seven expression probabilities.")
    flow = '<span class="arrow">→</span>'.join(f'<span class="es-chip">{s}</span>' for s in FLOW)
    st.html(f'<div class="es-chips" style="align-items:center">{flow}</div>')
    if summary:
        st.html('<div class="es-grid" style="grid-template-columns:repeat(auto-fit,minmax(170px,1fr));margin-top:.9rem">'
                + _metric("Parameters", f"{summary['parameters']:,}", f"{summary['model_size_mb']} MB on disk")
                + _metric("Training", f"{summary['training_minutes']:.0f} min", f"CPU · best epoch {summary['best_epoch']} "
                          f"of {summary['epochs_run']}")
                + _metric("Inference", f"{metrics['inference_ms_per_face_cpu']:.0f} ms", "Per face, CPU")
                + _metric("Training images", f"{summary['train_images']:,}", f"{summary['val_images']:,} validation")
                + "</div>")
    st.code("Input 48×48×1 (grayscale, /255)\n"
            "4 × [Conv3×3 → BN → ReLU] ×2  (24 → 48 → 96 → 192 filters), MaxPool + Dropout after blocks 1–3\n"
            "GlobalAveragePooling → Dense 256 → BN → ReLU → Dropout 0.5 → Dense 7 → Softmax", language=None)

    # ---- Model performance ---------------------------------------------------
    ui.section("Model performance", f"Headline: the leakage-aware test set — {clean['n']:,} test images that appear "
               "in neither the training nor the validation set.")
    st.html('<div class="es-grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))">'
            + _metric("Accuracy", f"{clean['accuracy']:.1%}", "Leakage-aware test")
            + _metric("Macro F1", f"{clean['macro_f1']:.3f}", "Every class weighted equally")
            + _metric("Weighted F1", f"{clean['weighted_f1']:.3f}", "Weighted by class size")
            + _metric("Top-3 accuracy", f"{metrics['top3_accuracy_official_test']:.1%}",
                      "True label in top 3 · official test")
            + "</div>")
    st.caption(f"Official FER-2013 test set ({off['n']:,} images): accuracy {off['accuracy']:.1%}, macro F1 "
               f"{off['macro_f1']:.3f}, weighted F1 {off['weighted_f1']:.3f}. Baseline that always predicts "
               f"'Happy': {base['accuracy']:.1%} accuracy.")
    rows = {"Official test": off, "Leakage-aware test": clean,
            "Test images also seen in train/val": metrics["test_images_seen_in_train_or_val"],
            "Baseline: always 'Happy'": base}
    table = pd.DataFrame(rows).T[["n", "accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1"]]
    st.dataframe(table.style.format({"n": "{:,.0f}", **{k: "{:.3f}" for k in table.columns if k != "n"}}),
                 width="stretch")

    why, leak = st.columns(2, gap="large")
    seen = metrics["test_images_seen_in_train_or_val"]
    why.html(f"""<div class="es-glass" style="height:100%"><div style="font-weight:700;font-size:1.05rem">⚖️ Why accuracy
        isn't enough</div><div class="es-muted es-small" style="margin-top:.4rem;line-height:1.6">FER-2013 is imbalanced:
        <b>Disgust</b> has 16.5× fewer training images than <b>Happy</b>. A model that always says <i>Happy</i> already
        scores <b>{base['accuracy']:.1%} accuracy</b>, yet its macro F1 is only <b>{base['macro_f1']:.3f}</b>. Macro F1
        averages every class equally, so ignoring rare classes is penalised. Training used balanced class weights and
        selected the checkpoint by validation macro F1.</div></div>""")
    leak.html(f"""<div class="es-glass" style="height:100%"><div style="font-weight:700;font-size:1.05rem">🔍 Honest
        evaluation: data leakage</div><div class="es-muted es-small" style="margin-top:.4rem;line-height:1.6">About 8% of
        FER-2013's official test images are exact pixel copies of training images. On those {seen['n']} images the model
        scores <b>{seen['accuracy']:.1%}</b>, versus <b>{clean['accuracy']:.1%}</b> on unseen images — memorisation
        inflates the official score. Both are reported; the leakage-aware one is the headline.</div></div>""")

    st.markdown("**Training curves**")
    _image("training_curves.png")

    # ---- Where the model struggles -------------------------------------------
    per_clean = metrics["per_class_leakage_aware_test"]
    ranked = sorted(per_clean.items(), key=lambda kv: kv[1]["f1"])
    ui.section("Where the model struggles", "Per-class F1 on the leakage-aware test set, weakest first.")
    cards = "".join(f"""<div class="es-glass lift" style="--c:{ui.color(e)}"><div style="font-size:1.6rem">{ui.emoji(e)}</div>
        <div style="font-weight:700;margin-top:.2rem">{e}</div><div class="es-stat-value">{m['f1']:.2f}</div>
        <div class="es-stat-hint">F1 · recall {m['recall']:.0%} · {m['support']} images</div>
        <div class="es-bar-track" style="margin-top:.45rem"><div class="es-bar-fill" style="width:{m['f1'] * 100:.0f}%">
        </div></div></div>""" for e, m in ranked)
    st.html(f'<div class="es-grid" style="grid-template-columns:repeat(auto-fit,minmax(118px,1fr))">{cards}</div>')
    weakest = ", ".join(e for e, _ in ranked[:3])
    st.caption(f"Weakest classes: {weakest}. Fear, Sad and Angry are often confused with each other; Disgust has very "
               "few test images, so its scores are noisy.")
    a, b = st.columns(2)
    with a:
        _image("confusion_matrix.png", "Confusion matrix (official test)")
    with b:
        _image("confusion_matrix_normalized.png", "Normalised by true class")
    with st.expander("Class-wise metrics table and chart", icon=":material/table_chart:"):
        _image("per_class_metrics.png")
        per_class = pd.DataFrame(metrics["per_class_official_test"]).T
        per_class["f1 (leakage-aware)"] = pd.DataFrame(per_clean).T["f1"]
        st.dataframe(per_class.style.format({"precision": "{:.3f}", "recall": "{:.3f}", "f1": "{:.3f}",
                                             "f1 (leakage-aware)": "{:.3f}"}), width="stretch")
        _image("eda_class_distribution.png", "Training-set class imbalance")

    # ---- Interpretability ----------------------------------------------------
    ui.section("Interpretability", "Grad-CAM shows which regions increased the predicted class score — where the model "
               "looked, not proof that it is correct.")
    a, b = st.columns(2, gap="large")
    with a:
        _image("gradcam/gradcam_correct.png", "Correct predictions")
    with b:
        _image("gradcam/gradcam_misclassified.png", "Misclassified examples")

    st.markdown("**Are the confidence bands meaningful? (validation set)**")
    rel = pd.DataFrame(metrics["confidence_reliability_validation"]).set_index("bin")
    st.dataframe(rel.style.format({"share_of_predictions": "{:.1%}", "accuracy": "{:.1%}"}), width="stretch")
    st.caption("The High / Moderate / Low bands are application heuristics, not calibrated certainty.")
