# Dataset — FER-2013

The dataset is **not committed** to this repository (see `.gitignore`). Follow the steps below to place it locally.

## What it is

**FER-2013** (Facial Expression Recognition 2013) was released for the *"Challenges in Representation Learning: Facial Expression Recognition Challenge"* (ICML 2013 workshop, Goodfellow et al., 2013). The images were collected automatically with Google Image Search and labelled with one of seven expressions.

- 35,887 grayscale face images
- 48 × 48 pixels, faces roughly centred and aligned
- 7 labels

| Index | Label    |
|-------|----------|
| 0     | Angry    |
| 1     | Disgust  |
| 2     | Fear     |
| 3     | Happy    |
| 4     | Sad      |
| 5     | Surprise |
| 6     | Neutral  |

## Official splits

| `Usage` value | Used here as | Images |
|---------------|--------------|--------|
| Training      | train        | 28,709 |
| PublicTest    | validation   | 3,589  |
| PrivateTest   | test         | 3,589  |

The test split is used **only once**, for final evaluation.

## How to get it

### Option A: automatic (recommended)

```bash
python -m src.data_loader --download
```

This downloads a public Hugging Face mirror of the original splits ([`AutumnQiu/fer2013`](https://huggingface.co/datasets/AutumnQiu/fer2013), about 136 MB) into `data/raw_hf/`. It then converts it to the original `fer2013.csv` format and prints the class counts so you can check them against the table above.

### Option B: Kaggle

1. Download from Kaggle, either the original challenge CSV
   ([challenges-in-representation-learning-facial-expression-recognition-challenge](https://www.kaggle.com/c/challenges-in-representation-learning-facial-expression-recognition-challenge/data))
   or the image-folder version ([msambare/fer2013](https://www.kaggle.com/datasets/msambare/fer2013)).
2. Place it in one of these layouts:

```
data/
└── fer2013/
    └── fer2013.csv                 # columns: emotion, pixels, Usage
```

or

```
data/
└── fer2013/
    ├── train/{angry,disgust,fear,happy,neutral,sad,surprise}/*.png
    └── test/{angry,disgust,fear,happy,neutral,sad,surprise}/*.png
```

The folder version has no validation split, so the loader takes a stratified 10% of `train` for validation.

## Why it is imbalanced

The images were scraped from the web using emotion-related search queries. Some expressions, especially **Happy**, are far more common in online photos than others. **Disgust** has only 436 of the 28,709 training images (about 1.5%), roughly 16.5× fewer than Happy (7,215). A model trained naively can ignore Disgust and still reach high accuracy. That is why this project uses **class weights** and reports **macro F1** alongside accuracy.

## Data-quality findings

These come from `notebooks/eda_and_model_analysis.ipynb` and `python -m src.data_quality`, which writes `results/data_leakage_report.json`.

### Near-blank images

13 images contain no face: 12 are completely black and 1 is flat grey (pixel standard deviation below 1). There are 12 in Training, 1 in PublicTest and none in PrivateTest. **They are excluded from training and validation at load time.** The files on disk are never modified.

### Exact duplicates across splits (data leakage)

Each image is hashed (MD5 of the raw pixels). Matching images are then confirmed to be pixel-identical with `np.array_equal`. Blank images are excluded from this check.

| Overlap | Images | Share | Copies with a different label |
|---------|--------|-------|-------------------------------|
| PublicTest (val) images also in Training | 279 | 7.8% of val | 15 |
| PrivateTest (test) images also in Training | 288 | 8.0% of test | 22 |
| PrivateTest (test) images also in PublicTest (val) | 44 | 1.2% of test | 2 |

There are also 1,226 extra copies of images within Training.

**Why it matters:** a model may have memorised a duplicated image during training. Its accuracy on the test copy then measures memory rather than generalisation, so official test metrics are slightly optimistic.

**What this project does:** the official splits are kept unchanged and nothing is deleted. Evaluation reports **both**:

1. the **official test set** (3,589 images), comparable with published FER-2013 results;
2. a **leakage-aware test subset** (3,275 images) that excludes every test image whose exact pixels appear in Training or PublicTest. PublicTest is excluded too because it drives early stopping and checkpoint selection.

Only exact duplicates are detected. Near-duplicates, such as the same photo re-cropped or re-compressed, would need perceptual hashing and are not covered.

## Limitations

- **Low resolution:** at 48 × 48 grayscale, fine detail and colour cues are lost.
- **Noisy labels:** human accuracy on FER-2013 is estimated at about 65 ± 5%. Some images are mislabelled, some are not faces, and many are ambiguous (Fear vs. Surprise, Sad vs. Neutral).
- **Posed vs. spontaneous:** many images show exaggerated, posed expressions.
- **Variation:** lighting, head pose, occlusion (hands, glasses, watermarks) and age vary a lot.
- **Demographics:** the demographic composition is undocumented. Performance may differ across groups, and this has not been audited.
- **Labels describe expressions, not feelings:** a label is an annotator's reading of a facial expression, not the person's actual emotional state.
