"""Train an emotion classifier on the official FER-2013 training split.

Usage (from the project root):
    python -m src.train            # custom CNN -> models/emotion_model.keras
    python -m src.train --quick    # 2-epoch smoke test on a small subset

Model selection uses validation **macro F1** (every class counts equally), not
accuracy, because accuracy rewards ignoring the rare Disgust class.
"""
import argparse
import json
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from tensorflow import keras

from src import config
from src.data_loader import DatasetNotFoundError, class_distribution, load_fer2013
from src.data_quality import remove_blank_images
from src.model import build_cnn
from src.preprocessing import compute_class_weights, make_dataset, to_model_input
from src.utils import SERIES_COLORS, TEXT_SECONDARY, save_fig, set_plot_style

class ValidationMacroF1(keras.callbacks.Callback):
    """Adds ``val_macro_f1`` and the current learning rate to the epoch logs.

    It must come first in the callback list so that EarlyStopping and
    ModelCheckpoint, which run after it, can monitor ``val_macro_f1``.
    """

    def __init__(self, x_val: np.ndarray, y_val: np.ndarray):
        super().__init__()
        self.x_val = to_model_input(x_val)
        self.y_val = y_val

    def on_epoch_end(self, epoch, logs=None):
        probs = self.model.predict(self.x_val, batch_size=256, verbose=0)
        logs["val_macro_f1"] = f1_score(self.y_val, probs.argmax(axis=1), average="macro")
        logs["learning_rate"] = float(keras.ops.convert_to_numpy(self.model.optimizer.learning_rate))
        print(f" - val_macro_f1: {logs['val_macro_f1']:.4f} - lr: {logs['learning_rate']:.2e}")


def plot_training_curves(log: pd.DataFrame, best_epoch: int, title: str):
    """Accuracy, loss and learning-rate curves with the selected epoch marked."""
    set_plot_style()
    epochs = log["epoch"] + 1
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
    panels = [("accuracy", "Accuracy"), ("loss", "Loss (cross-entropy)")]
    for ax, (key, label) in zip(axes, panels):
        ax.plot(epochs, log[key], color=SERIES_COLORS[0], label=f"train {key}")
        ax.plot(epochs, log[f"val_{key}"], color=SERIES_COLORS[1], label=f"validation {key}")
        ax.set(title=label, xlabel="Epoch")
    axes[0].plot(epochs, log["val_macro_f1"], color=SERIES_COLORS[2], label="validation macro F1")
    axes[2].plot(epochs, log["learning_rate"], color=SERIES_COLORS[0], label="learning rate")
    axes[2].set(title="Learning rate (ReduceLROnPlateau)", xlabel="Epoch", yscale="log")
    for ax in axes:
        ax.axvline(best_epoch, color=TEXT_SECONDARY, linestyle="--", linewidth=1, label=f"selected epoch ({best_epoch})")
        ax.legend(fontsize=8)
    fig.suptitle(title, fontweight="bold")
    fig.tight_layout()
    return fig


def train(epochs: int = config.EPOCHS, quick: bool = False) -> dict:
    keras.utils.set_random_seed(config.SEED)
    splits = load_fer2013()

    # Near-blank images contain no face; drop them from train/val only (test has none).
    x_train, y_train, removed_train = remove_blank_images(*splits["train"])
    x_val, y_val, removed_val = remove_blank_images(*splits["val"])
    if quick:
        x_train, y_train, x_val, y_val = x_train[:2000], y_train[:2000], x_val[:500], y_val[:500]
        epochs = 2
    print(f"Train {len(y_train)} images ({removed_train} blank removed), "
          f"validation {len(y_val)} ({removed_val} blank removed)")

    class_weights = compute_class_weights(y_train)  # from TRAINING labels only
    weight_table = class_distribution(y_train).to_frame()
    weight_table["class_weight"] = [class_weights[i] for i in range(config.NUM_CLASSES)]
    print(weight_table.to_string(float_format="%.3f"))

    model = build_cnn()
    model.summary(line_length=90)

    model_path = config.MODELS_DIR / "smoke_test.keras" if quick else config.MODEL_PATH
    log_path = config.RESULTS_DIR / "training_log.csv"
    config.MODELS_DIR.mkdir(exist_ok=True)
    config.RESULTS_DIR.mkdir(exist_ok=True)

    callbacks = [
        ValidationMacroF1(x_val, y_val),  # must be first (see class docstring)
        keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=config.REDUCE_LR_FACTOR,
                                          patience=config.REDUCE_LR_PATIENCE, min_lr=config.MIN_LR, verbose=1),
        keras.callbacks.EarlyStopping(monitor="val_macro_f1", mode="max",
                                      patience=config.EARLY_STOPPING_PATIENCE, restore_best_weights=True, verbose=1),
        keras.callbacks.ModelCheckpoint(model_path, monitor="val_macro_f1", mode="max", save_best_only=True),
    ]
    if not quick:
        callbacks.append(keras.callbacks.CSVLogger(log_path))

    start = time.time()
    model.fit(
        make_dataset(x_train, y_train, training=True),
        validation_data=make_dataset(x_val, y_val, training=False),
        epochs=epochs,
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=2,
    )
    minutes = (time.time() - start) / 60

    if quick:
        print(f"Smoke test finished in {minutes:.1f} min; model saved to {model_path}")
        return {}

    log = pd.read_csv(log_path)
    best = int(log["val_macro_f1"].idxmax())
    summary = {
        "architecture": "custom CNN",
        "filters": list(config.CNN_FILTERS),
        "parameters": int(model.count_params()),
        "model_path": model_path.relative_to(config.ROOT_DIR).as_posix(),
        "model_size_mb": round(model_path.stat().st_size / 1e6, 2),
        "train_images": int(len(y_train)),
        "val_images": int(len(y_val)),
        "blank_images_removed": {"train": removed_train, "val": removed_val},
        "class_weights": {config.EMOTIONS[k]: round(v, 4) for k, v in class_weights.items()},
        "epochs_run": int(len(log)),
        "max_epochs": epochs,
        "best_epoch": best + 1,
        "best_val_macro_f1": round(float(log.loc[best, "val_macro_f1"]), 4),
        "best_val_accuracy": round(float(log.loc[best, "val_accuracy"]), 4),
        "best_val_loss": round(float(log.loc[best, "val_loss"]), 4),
        "final_learning_rate": float(log["learning_rate"].iloc[-1]),
        "early_stopped": bool(len(log) < epochs),
        "training_minutes": round(minutes, 1),
        "seconds_per_epoch": round(minutes * 60 / len(log), 1),
    }
    (config.RESULTS_DIR / "training_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fig = plot_training_curves(log, best + 1, "Training history: custom CNN")
    save_fig(fig, "training_curves")
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--epochs", type=int, default=config.EPOCHS)
    parser.add_argument("--quick", action="store_true", help="2-epoch smoke test on a subset")
    args = parser.parse_args()
    try:
        train(args.epochs, args.quick)
    except DatasetNotFoundError as err:
        print(err)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
