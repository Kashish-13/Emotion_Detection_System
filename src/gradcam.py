"""Grad-CAM: which image regions most influenced a prediction.

Grad-CAM (Selvaraju et al., 2017) takes the gradient of the predicted class
score with respect to the last convolutional feature map. Averaging that
gradient over each channel gives one importance weight per channel. The
weighted sum of the channels, passed through ReLU, is a coarse heatmap: the
regions that pushed the score *up*.

It shows where the model looked. It does not prove the model reasoned
correctly, and it says nothing about what the person actually feels.

    python -m src.gradcam    # saves example grids to results/gradcam/
"""
import cv2
import numpy as np
import tensorflow as tf
from tensorflow import keras

from src import config

OVERLAY_RGB = np.array([235, 104, 52], dtype=np.float32)  # orange: one hue, opacity = importance


def find_last_conv_layer(model: keras.Model) -> str:
    """Name of the last layer that outputs a 4D feature map (N, H, W, C)."""
    for layer in reversed(model.layers):
        if len(layer.output.shape) == 4:
            return layer.name
    raise ValueError("Model has no convolutional feature map; Grad-CAM is not applicable.")


class GradCAM:
    def __init__(self, model: keras.Model, layer_name: str | None = None):
        self.layer_name = layer_name or find_last_conv_layer(model)
        self.grad_model = keras.Model(model.inputs, [model.get_layer(self.layer_name).output, model.output])

    def heatmap(self, face: np.ndarray, class_index: int | None = None):
        """face: preprocessed (48, 48, 1). Returns (heatmap 48x48 in [0, 1], class_index, probabilities)."""
        x = tf.convert_to_tensor(face[np.newaxis], dtype=tf.float32)
        with tf.GradientTape() as tape:
            feature_maps, probs = self.grad_model(x, training=False)
            if class_index is None:
                class_index = int(tf.argmax(probs[0]))
            score = probs[:, class_index]
        grads = tape.gradient(score, feature_maps)
        weights = tf.reduce_mean(grads, axis=(0, 1, 2))            # one weight per channel
        cam = tf.nn.relu(tf.reduce_sum(feature_maps[0] * weights, axis=-1)).numpy()
        if cam.max() > 0:
            cam /= cam.max()
        cam = cv2.resize(cam, (face.shape[1], face.shape[0]), interpolation=cv2.INTER_CUBIC)
        return np.clip(cam, 0, 1), class_index, probs.numpy()[0]


def overlay_heatmap(face_gray: np.ndarray, heatmap: np.ndarray, size: int = 192, strength: float = 0.65) -> np.ndarray:
    """Blend a single-hue heatmap over the grayscale face. Returns an RGB uint8 image."""
    gray = cv2.resize(face_gray.astype(np.float32), (size, size), interpolation=cv2.INTER_CUBIC)
    heat = cv2.resize(heatmap.astype(np.float32), (size, size), interpolation=cv2.INTER_CUBIC)
    alpha = (np.clip(heat, 0, 1) * strength)[..., np.newaxis]
    rgb = np.repeat(gray[..., np.newaxis], 3, axis=-1)
    return np.clip(rgb * (1 - alpha) + OVERLAY_RGB * alpha, 0, 255).astype(np.uint8)


def _example_grid(cam: GradCAM, x: np.ndarray, y: np.ndarray, indices, title: str):
    import matplotlib.pyplot as plt

    from src.preprocessing import to_model_input
    from src.utils import TEXT_PRIMARY, set_plot_style

    set_plot_style()
    fig, axes = plt.subplots(2, len(indices), figsize=(1.9 * len(indices), 4.4))
    for col, i in enumerate(indices):
        heat, pred, probs = cam.heatmap(to_model_input(x[i])[0])
        axes[0, col].imshow(cv2.resize(x[i], (192, 192), interpolation=cv2.INTER_CUBIC), cmap="gray")
        axes[0, col].set_title(f"true: {config.EMOTIONS[y[i]]}", fontsize=9)
        axes[1, col].imshow(overlay_heatmap(x[i], heat))
        axes[1, col].set_title(f"pred: {config.EMOTIONS[pred]} {probs[pred]:.0%}", fontsize=9)
        for ax in axes[:, col]:
            ax.axis("off")
    fig.suptitle(title, fontweight="bold", color=TEXT_PRIMARY)
    fig.text(0.5, -0.01, "Model Attention / Grad-CAM: orange = regions that most increased the predicted "
             "class score. Not proof of correct reasoning.", ha="center", fontsize=8)
    fig.tight_layout()
    return fig


def save_examples(n_wrong: int = 7):
    """Grad-CAM grids on test images: one correct example per class + misclassifications."""
    from src.data_loader import load_fer2013
    from src.predict import load_emotion_model
    from src.preprocessing import to_model_input

    model = load_emotion_model()
    cam = GradCAM(model)
    x, y = load_fer2013()["test"]
    probs = model.predict(to_model_input(x), batch_size=256, verbose=0)
    pred, conf = probs.argmax(1), probs.max(1)
    rng = np.random.default_rng(config.SEED)

    correct = []
    for c in range(config.NUM_CLASSES):
        candidates = np.flatnonzero((y == c) & (pred == c) & (conf >= config.HIGH_CONFIDENCE))
        if len(candidates) == 0:
            candidates = np.flatnonzero((y == c) & (pred == c))
        if len(candidates):
            correct.append(int(rng.choice(candidates)))
    wrong = rng.choice(np.flatnonzero(pred != y), n_wrong, replace=False)

    out_dir = config.RESULTS_DIR / "gradcam"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, idx, title in [("gradcam_correct", correct, "Grad-CAM: correctly classified test faces"),
                             ("gradcam_misclassified", wrong, "Grad-CAM: misclassified test faces")]:
        fig = _example_grid(cam, x, y, idx, title)
        fig.savefig(out_dir / f"{name}.png", bbox_inches="tight")
        print(f"Saved results/gradcam/{name}.png (layer: {cam.layer_name})")


if __name__ == "__main__":
    save_examples()
