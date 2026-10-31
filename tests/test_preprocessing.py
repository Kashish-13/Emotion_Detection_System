import numpy as np
import pytest

from src import config
from src.data_quality import blank_mask, leakage_free_test_mask, overlap_mask, remove_blank_images
from src.preprocessing import compute_class_weights, make_dataset, preprocess_face, to_model_input


def test_labels_are_the_seven_fer2013_classes_in_index_order():
    assert config.EMOTIONS == ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]
    assert config.NUM_CLASSES == 7
    assert config.INPUT_SHAPE == (48, 48, 1)


@pytest.mark.parametrize("shape", [(48, 48), (5, 48, 48), (5, 48, 48, 1)])
def test_to_model_input_shape_and_range(shape):
    x = np.random.default_rng(0).integers(0, 256, shape, dtype=np.uint8)
    out = to_model_input(x)
    assert out.ndim == 4 and out.shape[1:] == config.INPUT_SHAPE
    assert out.dtype == np.float32
    assert 0.0 <= out.min() and out.max() <= 1.0


def test_to_model_input_scales_extremes_exactly():
    out = to_model_input(np.array([[0, 255]] * 48 * 24, dtype=np.uint8).reshape(48, 48))
    assert out.min() == 0.0 and out.max() == 1.0


@pytest.mark.parametrize("shape", [(200, 150, 3), (30, 30), (480, 640, 3)])
def test_preprocess_face_handles_color_gray_and_any_size(shape):
    face = np.random.default_rng(1).integers(0, 256, shape, dtype=np.uint8)
    out = preprocess_face(face)
    assert out.shape == config.INPUT_SHAPE
    assert 0.0 <= out.min() and out.max() <= 1.0


def test_class_weights_are_balanced_and_favour_minority_class():
    y = np.array([0] * 100 + [1] * 10 + [2] * 50 + [3] * 200 + [4] * 60 + [5] * 40 + [6] * 80)
    w = compute_class_weights(y)
    assert set(w) == set(range(7))
    counts = np.bincount(y)
    for c in range(7):  # balanced formula: n / (k * n_c)
        assert w[c] == pytest.approx(len(y) / (7 * counts[c]))
    assert max(w, key=w.get) == 1 and min(w, key=w.get) == 3


def test_validation_pipeline_is_deterministic_and_unaugmented():
    rng = np.random.default_rng(2)
    x, y = rng.integers(0, 256, (70, 48, 48), dtype=np.uint8), rng.integers(0, 7, 70)
    batches_a = [b for b, _ in make_dataset(x, y, training=False, batch_size=32)]
    batches_b = [b for b, _ in make_dataset(x, y, training=False, batch_size=32)]
    np.testing.assert_array_equal(np.concatenate(batches_a), np.concatenate(batches_b))
    np.testing.assert_allclose(np.concatenate(batches_a), to_model_input(x))  # same order, no augmentation


def test_training_pipeline_keeps_shape_range_and_labels():
    rng = np.random.default_rng(3)
    x, y = rng.integers(0, 256, (64, 48, 48), dtype=np.uint8), np.arange(64) % 7
    xb, yb = next(iter(make_dataset(x, y, training=True, batch_size=64)))
    assert tuple(xb.shape) == (64, 48, 48, 1)
    assert float(xb.numpy().min()) >= 0.0 and float(xb.numpy().max()) <= 1.0
    assert sorted(yb.numpy().tolist()) == sorted(y.tolist())  # shuffled, but labels preserved


def test_blank_and_overlap_masks():
    rng = np.random.default_rng(4)
    faces = rng.integers(0, 256, (4, 48, 48), dtype=np.uint8)
    images = np.concatenate([faces, np.zeros((1, 48, 48), np.uint8)])
    assert blank_mask(images).tolist() == [False] * 4 + [True]
    x, y, removed = remove_blank_images(images, np.arange(5))
    assert removed == 1 and len(x) == 4 and y.tolist() == [0, 1, 2, 3]
    assert overlap_mask(faces[:2], faces[1:]).tolist() == [False, True]


def test_leakage_free_mask_excludes_test_images_seen_in_train_or_val():
    rng = np.random.default_rng(5)
    imgs = rng.integers(0, 256, (6, 48, 48), dtype=np.uint8)
    splits = {"train": (imgs[:3], np.zeros(3)), "val": (imgs[3:4], np.zeros(1)),
              "test": (np.stack([imgs[0], imgs[3], imgs[4], imgs[5]]), np.zeros(4))}
    assert leakage_free_test_mask(splits).tolist() == [False, False, True, True]
