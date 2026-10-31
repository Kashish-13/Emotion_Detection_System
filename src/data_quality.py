"""Data-quality checks for FER-2013: near-blank images and cross-split duplicates.

Nothing here deletes data from disk. Functions return boolean masks so that
callers decide, transparently, what to exclude:

* training/validation drop near-blank images (no face, meaningless label);
* evaluation reports the official test set AND a leakage-aware subset that
  excludes test images whose exact pixels also appear in train or validation.

Run ``python -m src.data_quality`` to regenerate ``results/data_leakage_report.json``.
"""
import hashlib
import json
from itertools import combinations

import numpy as np

from src import config


def image_hashes(images: np.ndarray) -> np.ndarray:
    """MD5 of each image's raw bytes. Equal hashes == pixel-identical images."""
    return np.array([hashlib.md5(img.tobytes()).hexdigest() for img in images])


def blank_mask(images: np.ndarray, std_threshold: float = config.BLANK_STD_THRESHOLD) -> np.ndarray:
    """True for images that are effectively one flat colour (no face)."""
    return images.reshape(len(images), -1).std(axis=1) < std_threshold


def overlap_mask(images: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """True for each image in ``images`` whose exact pixels occur in ``reference``."""
    ref = set(image_hashes(reference))
    return np.array([h in ref for h in image_hashes(images)], dtype=bool)


def leakage_free_test_mask(splits: dict) -> np.ndarray:
    """Test images that appear in neither train nor validation (and are not blank).

    Validation is excluded too because it drives early stopping and checkpoint
    selection, so it indirectly influences the final model.
    """
    x_test = splits["test"][0]
    seen = np.concatenate([splits["train"][0], splits["val"][0]])
    return ~overlap_mask(x_test, seen) & ~blank_mask(x_test)


def remove_blank_images(x: np.ndarray, y: np.ndarray):
    """Return (x, y, n_removed) with near-blank images dropped."""
    keep = ~blank_mask(x)
    return x[keep], y[keep], int((~keep).sum())


def _verify_exact(x_a, x_b, h_a, h_b) -> bool:
    """Confirm that hash matches are true pixel matches (guards against collisions)."""
    first_b = {}
    for i, h in enumerate(h_b):
        first_b.setdefault(h, i)
    return all(np.array_equal(x_a[i], x_b[first_b[h]]) for i, h in enumerate(h_a) if h in first_b)


def leakage_report(splits: dict) -> dict:
    """Quantify blank images, within-split duplicates and cross-split overlap."""
    hashes = {name: image_hashes(x) for name, (x, _) in splits.items()}
    blanks = {name: blank_mask(x) for name, (x, _) in splits.items()}
    report = {"blank_std_threshold": config.BLANK_STD_THRESHOLD, "splits": {}, "cross_split": {}}

    for name, (x, y) in splits.items():
        h = hashes[name][~blanks[name]]
        report["splits"][name] = {
            "images": int(len(x)),
            "near_blank": int(blanks[name].sum()),
            "within_split_duplicate_copies": int(len(h) - len(set(h))),
        }

    for a, b in combinations(splits, 2):
        x_a, y_a = splits[a]
        x_b, y_b = splits[b]
        keep_a, keep_b = ~blanks[a], ~blanks[b]
        h_a, h_b = hashes[a][keep_a], hashes[b][keep_b]
        labels_b = {}
        for h, label in zip(h_b, y_b[keep_b]):
            labels_b.setdefault(h, set()).add(int(label))
        in_b = np.array([h in labels_b for h in h_a], dtype=bool)
        label_conflicts = sum(
            1 for h, label in zip(h_a[in_b], y_a[keep_a][in_b]) if labels_b[h] != {int(label)}
        )
        report["cross_split"][f"{a}<->{b}"] = {
            f"{a}_images_found_in_{b}": int(in_b.sum()),
            f"pct_of_{a}": round(100 * in_b.sum() / len(x_a), 2),
            f"{b}_images_found_in_{a}": int(np.isin(h_b, h_a).sum()),
            f"pct_of_{b}": round(100 * np.isin(h_b, h_a).sum() / len(x_b), 2),
            "matches_with_different_label": int(label_conflicts),
            "verified_pixel_identical": _verify_exact(x_a[keep_a], x_b[keep_b], h_a, h_b),
        }

    clean = leakage_free_test_mask(splits)
    report["leakage_aware_test_subset"] = {
        "official_test_images": int(len(clean)),
        "leakage_aware_test_images": int(clean.sum()),
        "excluded": int((~clean).sum()),
        "rule": "exclude test images whose exact pixels appear in train or validation",
    }
    return report


def main():
    from src.data_loader import load_fer2013

    report = leakage_report(load_fer2013())
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.RESULTS_DIR / "data_leakage_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nSaved {out.relative_to(config.ROOT_DIR)}")


if __name__ == "__main__":
    main()
