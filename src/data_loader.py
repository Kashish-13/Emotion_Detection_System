"""Loading FER-2013 from disk.

Two on-disk layouts are supported:

1. ``data/fer2013/fer2013.csv`` — the original challenge CSV with columns
   ``emotion, pixels, Usage``. Usage = Training / PublicTest / PrivateTest,
   which we map to train / val / test. This is the preferred layout because
   it keeps the official splits.
2. ``data/fer2013/train/<Emotion>/*.png`` and ``data/fer2013/test/<Emotion>/*.png``
   — the popular Kaggle image-folder release. It has no validation split, so a
   stratified one is carved out of train.

Run ``python -m src.data_loader --download`` to fetch a public mirror of the
original splits and write layout (1).
"""
import argparse
import io
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from src import config

USAGE_TO_SPLIT = {"Training": "train", "PublicTest": "val", "PrivateTest": "test"}
HF_MIRROR = "https://huggingface.co/datasets/AutumnQiu/fer2013/resolve/main/data/{split}-00000-of-00001.parquet"
HF_SPLIT_TO_USAGE = {"train": "Training", "valid": "PublicTest", "test": "PrivateTest"}


class DatasetNotFoundError(FileNotFoundError):
    """Raised when FER-2013 is not present in any supported layout."""


def _missing_dataset_message() -> str:
    return (
        "FER-2013 dataset not found.\n"
        f"  Expected either {config.FER_CSV_PATH}\n"
        f"  or image folders {config.FER_FOLDER_DIR / 'train'} and {config.FER_FOLDER_DIR / 'test'}.\n"
        "  Fix: run `python -m src.data_loader --download`, or follow data/README.md."
    )


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------
def _load_from_csv(csv_path: Path) -> dict:
    """Parse the CSV once, then reuse a compressed .npz cache (parsing takes ~25 s)."""
    cache = csv_path.with_name("fer2013_cache.npz")
    if cache.is_file() and cache.stat().st_mtime >= csv_path.stat().st_mtime:
        with np.load(cache) as npz:
            return {name: (npz[f"x_{name}"], npz[f"y_{name}"]) for name in USAGE_TO_SPLIT.values()}

    df = pd.read_csv(csv_path)
    pixels = np.stack(
        [np.asarray(p.split(), dtype=np.uint8) for p in df["pixels"]]
    ).reshape(-1, config.IMG_SIZE, config.IMG_SIZE)
    labels = df["emotion"].to_numpy(dtype=np.int64)
    splits = {}
    for usage, name in USAGE_TO_SPLIT.items():
        mask = (df["Usage"] == usage).to_numpy()
        splits[name] = (pixels[mask], labels[mask])
    np.savez_compressed(cache, **{f"{k}_{name}": v for name, xy in splits.items() for k, v in zip("xy", xy)})
    return splits


def _read_image_folder(folder: Path):
    images, labels = [], []
    for label, emotion in enumerate(config.EMOTIONS):
        class_dir = folder / emotion.lower()
        if not class_dir.is_dir():
            class_dir = folder / emotion
        for path in sorted(class_dir.glob("*")):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            img = Image.open(path).convert("L").resize((config.IMG_SIZE, config.IMG_SIZE))
            images.append(np.asarray(img, dtype=np.uint8))
            labels.append(label)
    return np.stack(images), np.asarray(labels, dtype=np.int64)


def _load_from_folders(root: Path) -> dict:
    from sklearn.model_selection import train_test_split

    x_train, y_train = _read_image_folder(root / "train")
    x_test, y_test = _read_image_folder(root / "test")
    x_train, x_val, y_train, y_val = train_test_split(
        x_train, y_train, test_size=config.VAL_SPLIT,
        stratify=y_train, random_state=config.SEED,
    )
    return {"train": (x_train, y_train), "val": (x_val, y_val), "test": (x_test, y_test)}


def load_fer2013() -> dict:
    """Return ``{"train": (X, y), "val": (X, y), "test": (X, y)}``.

    X is uint8 with shape (N, 48, 48); y holds integer labels indexing
    ``config.EMOTIONS``. Raises DatasetNotFoundError with fix instructions.
    """
    if config.FER_CSV_PATH.is_file():
        return _load_from_csv(config.FER_CSV_PATH)
    if (config.FER_FOLDER_DIR / "train").is_dir() and (config.FER_FOLDER_DIR / "test").is_dir():
        return _load_from_folders(config.FER_FOLDER_DIR)
    raise DatasetNotFoundError(_missing_dataset_message())


def class_distribution(labels: np.ndarray) -> pd.Series:
    """Count of samples per emotion, in label order."""
    counts = np.bincount(labels, minlength=config.NUM_CLASSES)
    return pd.Series(counts, index=config.EMOTIONS, name="count")


# ---------------------------------------------------------------------------
# Download / conversion
# ---------------------------------------------------------------------------
def download_mirror(dest: Path = config.HF_PARQUET_DIR) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for split in HF_SPLIT_TO_USAGE:
        target = dest / f"{split}.parquet"
        if target.is_file():
            print(f"  already present: {target}")
            continue
        print(f"  downloading {split} split ...")
        urllib.request.urlretrieve(HF_MIRROR.format(split=split), target)


def parquet_to_csv(src: Path = config.HF_PARQUET_DIR, out: Path = config.FER_CSV_PATH) -> None:
    """Convert the mirror's parquet files into the original fer2013.csv format."""
    frames = []
    for split, usage in HF_SPLIT_TO_USAGE.items():
        df = pd.read_parquet(src / f"{split}.parquet")
        pixels = []
        for item in df["image"]:
            img = Image.open(io.BytesIO(item["bytes"])).convert("L")
            if img.size != (config.IMG_SIZE, config.IMG_SIZE):
                raise ValueError(f"Unexpected image size {img.size} in {split} split")
            pixels.append(" ".join(map(str, np.asarray(img).ravel())))
        frames.append(pd.DataFrame({"emotion": df["label"], "pixels": pixels, "Usage": usage}))
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, ignore_index=True).to_csv(out, index=False)
    print(f"  wrote {out}")


def main():
    parser = argparse.ArgumentParser(description="FER-2013 dataset utilities")
    parser.add_argument("--download", action="store_true",
                        help="download the public mirror and build data/fer2013/fer2013.csv")
    args = parser.parse_args()

    if args.download:
        download_mirror()
        parquet_to_csv()

    try:
        splits = load_fer2013()
    except DatasetNotFoundError as err:
        print(err)
        raise SystemExit(1)
    for name, (x, y) in splits.items():
        print(f"{name:>5}: {len(y):>6} images, shape {x.shape[1:]}")
        print(class_distribution(y).to_string(), "\n")


if __name__ == "__main__":
    main()
