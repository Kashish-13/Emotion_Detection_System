"""Evaluate a trained model on the FER-2013 test set.

Two test evaluations are reported side by side:

* **official**: all 3,589 PrivateTest images, comparable with published FER-2013 results;
* **leakage-aware**: test images whose exact pixels do NOT appear in train or
  validation (see src/data_quality.py). This is the more honest estimate for
  unseen faces.

Usage:
    python -m src.evaluate                       # evaluates models/emotion_model.keras
    python -m src.evaluate --model other.keras   # any compatible saved model
"""
import argparse
import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             precision_recall_fscore_support)

from src import config
from src.data_loader import load_fer2013
from src.data_quality import leakage_free_test_mask
from src.predict import load_emotion_model
from src.preprocessing import to_model_input
from src.utils import SERIES_COLORS, TEXT_PRIMARY, save_fig, set_plot_style

# Single-hue sequential ramp (light -> dark blue) for confusion matrices.
BLUES = LinearSegmentedColormap.from_list("blues", ["#f4f8fd", "#9ec5f4", "#3987e5", "#1c5cab", "#0d366b"])
CONFIDENCE_BINS = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]


def summary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Accuracy plus macro- and weighted-averaged precision / recall / F1."""
    out = {"n": int(len(y_true)), "accuracy": accuracy_score(y_true, y_pred)}
    for avg in ("macro", "weighted"):
        p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average=avg, zero_division=0)
        out.update({f"{avg}_precision": p, f"{avg}_recall": r, f"{avg}_f1": f})
    return {k: (round(float(v), 4) if k != "n" else v) for k, v in out.items()}


def per_class_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=range(config.NUM_CLASSES), zero_division=0)
    return {e: {"precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4),
                "f1": round(float(f[i]), 4), "support": int(s[i])} for i, e in enumerate(config.EMOTIONS)}


def confidence_reliability(y_true: np.ndarray, probs: np.ndarray) -> list[dict]:
    """Accuracy of predictions grouped by their top-class probability (validation set)."""
    conf, correct = probs.max(1), probs.argmax(1) == y_true
    rows = []
    for lo, hi in zip(CONFIDENCE_BINS[:-1], CONFIDENCE_BINS[1:]):
        m = (conf >= lo) & (conf < hi)
        rows.append({"bin": f"{lo:.1f}-{min(hi, 1):.1f}", "share_of_predictions": round(float(m.mean()), 4),
                     "accuracy": round(float(correct[m].mean()), 4) if m.any() else None})
    for name, lo, hi in [("High", config.HIGH_CONFIDENCE, 1.0001),
                         ("Moderate", config.MODERATE_CONFIDENCE, config.HIGH_CONFIDENCE),
                         ("Low", 0.0, config.MODERATE_CONFIDENCE)]:
        m = (conf >= lo) & (conf < hi)
        rows.append({"bin": f"app band: {name}", "share_of_predictions": round(float(m.mean()), 4),
                     "accuracy": round(float(correct[m].mean()), 4) if m.any() else None})
    return rows


def inference_speed_ms(model, n_runs: int = 50) -> float:
    """Median latency of one single-face forward pass, as in the app."""
    face = np.random.default_rng(0).random((1, *config.INPUT_SHAPE), dtype=np.float32)
    model(face, training=False)  # warm-up
    times = []
    for _ in range(n_runs):
        t = time.perf_counter()
        model(face, training=False)
        times.append((time.perf_counter() - t) * 1000)
    return round(float(np.median(times)), 2)


def plot_confusion(cm: np.ndarray, normalized: bool, title: str):
    set_plot_style()
    data = cm / cm.sum(axis=1, keepdims=True) if normalized else cm
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(data, cmap=BLUES, vmin=0, vmax=data.max())
    ax.grid(False)
    for i in range(len(cm)):
        for j in range(len(cm)):
            dark = data[i, j] > 0.55 * data.max()
            ax.text(j, i, f"{data[i, j]:.2f}" if normalized else f"{cm[i, j]}", ha="center", va="center",
                    fontsize=9, color="white" if dark else TEXT_PRIMARY)
    ax.set_xticks(range(len(cm)), config.EMOTIONS, rotation=35, ha="right")
    ax.set_yticks(range(len(cm)), config.EMOTIONS)
    ax.set(xlabel="Predicted label", ylabel="True label", title=title)
    fig.tight_layout()
    return fig


def plot_per_class(per_class: dict, title: str):
    set_plot_style()
    fig, ax = plt.subplots(figsize=(10, 4.2))
    xpos, width = np.arange(config.NUM_CLASSES), 0.26
    for k, (metric, color) in enumerate(zip(["precision", "recall", "f1"], SERIES_COLORS)):
        values = [per_class[e][metric] for e in config.EMOTIONS]
        ax.bar(xpos + (k - 1) * width, values, width=width - 0.03, color=color, label=metric)
    for i, e in enumerate(config.EMOTIONS):
        ax.text(i + width, per_class[e]["f1"] + 0.015, f"{per_class[e]['f1']:.2f}", ha="center", fontsize=8,
                color=TEXT_PRIMARY)
    labels = [f"{e}\n(n={per_class[e]['support']})" for e in config.EMOTIONS]
    ax.set_xticks(xpos, labels)
    ax.set(ylim=(0, 1), ylabel="Score", title=title)
    ax.grid(axis="x", visible=False)
    ax.legend(ncols=3, loc="upper left")
    fig.tight_layout()
    return fig


def evaluate(model_path: Path = config.MODEL_PATH) -> dict:
    model = load_emotion_model(model_path)
    splits = load_fer2013()
    x_test, y_test = splits["test"]
    x_val, y_val = splits["val"]

    test_probs = model.predict(to_model_input(x_test), batch_size=256, verbose=0)
    val_probs = model.predict(to_model_input(x_val), batch_size=256, verbose=0)
    y_pred = test_probs.argmax(1)
    clean = leakage_free_test_mask(splits)

    happy = config.EMOTIONS.index("Happy")
    results = {
        "model_path": Path(model_path).resolve().relative_to(config.ROOT_DIR).as_posix(),
        "model_size_mb": round(Path(model_path).stat().st_size / 1e6, 2),
        "parameters": int(model.count_params()),
        "inference_ms_per_face_cpu": inference_speed_ms(model),
        "official_test": summary_metrics(y_test, y_pred),
        "leakage_aware_test": summary_metrics(y_test[clean], y_pred[clean]),
        "test_images_seen_in_train_or_val": summary_metrics(y_test[~clean], y_pred[~clean]),
        "validation": summary_metrics(y_val, val_probs.argmax(1)),
        "baseline_always_happy_official_test": summary_metrics(y_test, np.full_like(y_test, happy)),
        "baseline_always_happy_leakage_aware_test": summary_metrics(y_test[clean], np.full_like(y_test[clean], happy)),
        "per_class_official_test": per_class_metrics(y_test, y_pred),
        "per_class_leakage_aware_test": per_class_metrics(y_test[clean], y_pred[clean]),
        "confidence_reliability_validation": confidence_reliability(y_val, val_probs),
        "top3_accuracy_official_test": round(float(np.mean(
            [y in row for y, row in zip(y_test, np.argsort(test_probs, axis=1)[:, -3:])])), 4),
    }

    config.RESULTS_DIR.mkdir(exist_ok=True)
    (config.RESULTS_DIR / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    report = (
        "OFFICIAL TEST SET (all 3,589 PrivateTest images)\n"
        + classification_report(y_test, y_pred, target_names=config.EMOTIONS, digits=4, zero_division=0)
        + f"\nLEAKAGE-AWARE TEST SUBSET ({int(clean.sum())} images not present in train/validation)\n"
        + classification_report(y_test[clean], y_pred[clean], target_names=config.EMOTIONS, digits=4, zero_division=0)
    )
    (config.RESULTS_DIR / "classification_report.txt").write_text(report, encoding="utf-8")

    cm = confusion_matrix(y_test, y_pred, labels=range(config.NUM_CLASSES))
    save_fig(plot_confusion(cm, False, "Confusion matrix: official test set"), "confusion_matrix")
    save_fig(plot_confusion(cm, True, "Normalized confusion matrix: official test set (rows sum to 1)"),
             "confusion_matrix_normalized")
    save_fig(plot_per_class(results["per_class_official_test"], "Per-class metrics: official test set"),
             "per_class_metrics")
    plt.close("all")

    print(report)
    print(json.dumps({k: results[k] for k in ("official_test", "leakage_aware_test",
                                              "baseline_always_happy_official_test",
                                              "confidence_reliability_validation",
                                              "inference_ms_per_face_cpu")}, indent=2))
    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate a trained emotion model on FER-2013.")
    parser.add_argument("--model", type=Path, default=config.MODEL_PATH)
    args = parser.parse_args()
    evaluate(args.model)


if __name__ == "__main__":
    main()
