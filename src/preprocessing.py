"""Preprocessing shared by training and inference.

The single source of truth is ``to_model_input``: every image the model ever
sees, from FER-2013 or from an uploaded photo or webcam frame, passes
through it. Training-only augmentation is applied afterwards, inside the
tf.data pipeline, and never touches validation or test data.
"""
import cv2
import numpy as np
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight
from tensorflow import keras

from src import config


def to_model_input(images: np.ndarray) -> np.ndarray:
    """uint8 grayscale image(s) of size 48x48 -> float32 (N, 48, 48, 1) in [0, 1]."""
    images = np.asarray(images, dtype=np.float32)
    if images.ndim == 2:                       # single image
        images = images[np.newaxis]
    if images.ndim == 3:                       # add channel dimension
        images = images[..., np.newaxis]
    return images / 255.0


def preprocess_face(face: np.ndarray) -> np.ndarray:
    """Any face crop (BGR or grayscale, any size) -> model input of shape (48, 48, 1)."""
    if face.ndim == 3:
        face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    # INTER_AREA is the recommended interpolation for downscaling.
    face = cv2.resize(face, (config.IMG_SIZE, config.IMG_SIZE), interpolation=cv2.INTER_AREA)
    return to_model_input(face)[0]


def build_augmenter() -> keras.Sequential:
    """Mild, expression-preserving augmentation (training only)."""
    return keras.Sequential([
        keras.layers.RandomFlip("horizontal"),
        keras.layers.RandomRotation(config.AUG_ROTATION, fill_mode="nearest"),
        keras.layers.RandomZoom(config.AUG_ZOOM, fill_mode="nearest"),
        keras.layers.RandomTranslation(config.AUG_TRANSLATE, config.AUG_TRANSLATE, fill_mode="nearest"),
        # Small photometric jitter: EDA showed mean brightness differs by class,
        # so this discourages the model from using brightness as a shortcut.
        keras.layers.RandomBrightness(config.AUG_BRIGHTNESS, value_range=(0.0, 1.0)),
        keras.layers.RandomContrast(config.AUG_CONTRAST, value_range=(0.0, 1.0)),
    ], name="augmenter")


def make_dataset(x: np.ndarray, y: np.ndarray, training: bool,
                 batch_size: int = config.BATCH_SIZE) -> tf.data.Dataset:
    """Batched tf.data pipeline. Shuffling and augmentation only when ``training``."""
    ds = tf.data.Dataset.from_tensor_slices((to_model_input(x), y.astype(np.int32)))
    if training:
        ds = ds.shuffle(len(x), seed=config.SEED, reshuffle_each_iteration=True)
    ds = ds.batch(batch_size)
    if training:
        augmenter = build_augmenter()
        ds = ds.map(lambda img, label: (tf.clip_by_value(augmenter(img, training=True), 0.0, 1.0), label),
                    num_parallel_calls=tf.data.AUTOTUNE)
    return ds.prefetch(tf.data.AUTOTUNE)


def compute_class_weights(y_train: np.ndarray) -> dict:
    """'Balanced' weights n_samples / (n_classes * n_class_samples), from TRAINING labels only."""
    classes = np.arange(config.NUM_CLASSES)
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    return {int(c): float(w) for c, w in zip(classes, weights)}
