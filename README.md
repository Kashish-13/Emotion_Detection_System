# Emotion Detection System

Facial-expression recognition with a custom CNN trained on **FER-2013**, OpenCV face detection, Grad-CAM explainability, real-time webcam inference and a Streamlit interface. It was built and trained locally on a CPU-only Windows laptop.

> **Responsible-use note:** this system classifies **facial expressions** in images. It does not detect what a person actually feels and is not a medical, psychological or hiring tool. See [Ethical considerations](#ethical-considerations).

---

## Overview

| | |
|---|---|
| Task | 7-class facial-expression classification: Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral |
| Data | FER-2013: 35,887 grayscale 48×48 faces, official Training / PublicTest / PrivateTest splits |
| Model | Custom VGG-style CNN, **713k parameters**, 8.7 MB, about 75 ms per webcam frame (detection + prediction) on CPU |
| Headline result | **59.6% accuracy / 0.545 macro F1** on the leakage-aware test set (official test: 60.9% / 0.570) |
| Baseline | Always predicting "Happy": 24.5% accuracy / 0.056 macro F1 |

All numbers in this README come from `results/metrics.json` and `results/training_summary.json`, written by the evaluation and training scripts.

## Features

- **Face detection** with OpenCV's Haar cascade, supporting **multiple faces** per image.
- **Prediction for each face** with confidence, **top-3 alternatives** and the full **7-class probability chart**.
- **Confidence bands** (High ≥ 70%, Moderate 40–70%, Low < 40%) with a low-confidence warning. The thresholds are checked against validation accuracy (see [Results](#results)).
- **Grad-CAM** "model attention" heatmap for every detected face.
- **Live webcam mode** with Start/Stop control. Prediction runs every 3rd frame to save CPU.
- **Session analytics:** prediction counts, most frequent expression, average confidence.
- **Leakage-aware evaluation:** FER-2013's cross-split duplicate images are detected and reported transparently.
- **Friendly error handling** for a missing model, missing dataset, invalid image, no face, a very small face, or an unavailable webcam.

## Demo

Output of the real inference pipeline (`src/predict.py`) on four FER-2013 test faces that the model never saw in train or validation:

![Pipeline demo](results/demo_multi_face.png)

The box colour and label show the confidence band. The third face is turned sharply and is **missed by the frontal Haar detector**, which is a real limitation of this design and is shown here deliberately.

*Screenshots of the Streamlit app are not included yet. Run `streamlit run app.py` to see it.*

## Tech stack

Python 3.13 · TensorFlow 2.21 / Keras 3 · OpenCV 4.14 · NumPy · pandas · scikit-learn · Matplotlib · Streamlit 1.66 (Altair charts) · pytest

> OpenCV is pinned to `<5` because OpenCV 5 removed `cv2.CascadeClassifier` and its bundled Haar-cascade files.

## Dataset

**FER-2013** (Goodfellow et al., 2013). The dataset is **not committed**; see [`data/README.md`](data/README.md) for download instructions. In short, `python -m src.data_loader --download` fetches a public mirror of the original splits. The class counts were verified to match the original challenge exactly.

| Split (official name) | Used as | Images |
|---|---|---|
| Training | train | 28,709 |
| PublicTest | validation | 3,589 |
| PrivateTest | test | 3,589 |

### FER-2013 class distribution

![Class distribution](results/eda_class_distribution.png)

**Disgust is 16.5× rarer than Happy** (436 vs 7,215 training images). A model can ignore Disgust entirely and still reach high accuracy, so this project uses class weights and reports **macro F1**.

### Data-quality findings and the leakage issue

The EDA (`notebooks/eda_and_model_analysis.ipynb`) found two problems:

1. **13 near-blank images** with no face: 12 black and 1 grey, but all labelled. They are excluded from train and validation at load time; the files are never modified.
2. **Exact duplicate images across splits**, checked by MD5 hash and then confirmed pixel by pixel:

| Overlap | Images | Share |
|---|---|---|
| Test images also in train | 288 | 8.0% of test |
| Validation images also in train | 279 | 7.8% of validation |
| Test images also in validation | 44 | 1.2% of test |

A model can memorise a duplicated training image, which inflates test scores. The project **keeps the official splits** but reports **two evaluations**:

- **Official test**: all 3,589 images, comparable with published FER-2013 results.
- **Leakage-aware test**: 3,275 images, excluding every test image found in train *or* validation. Validation is excluded too because it drives early stopping and checkpoint selection.

The inflation is measurable. On the 314 leaked test images the model scores **75.2%** accuracy, compared with **59.6%** on unseen images.

## Data preprocessing

One function, `to_model_input`, is used everywhere: training, evaluation and the app.

```
face crop → grayscale → resize to 48×48 (INTER_AREA) → divide by 255 → shape (48, 48, 1)
```

**Training-only augmentation** (inside the `tf.data` pipeline; validation and test are never augmented):
horizontal flip, ±10° rotation, 10% zoom, 10% shift, and ±10% brightness and contrast. The photometric jitter was added because the EDA showed **mean brightness differs by class** (Surprise 146 vs Sad 121), a shortcut the model should not learn.

![Augmentation](results/augmentation_examples.png)

## Model architecture

```
Input 48×48×1
Block 1: [Conv 3×3, 24  → BatchNorm → ReLU] ×2 → MaxPool → Dropout 0.20   → 24×24
Block 2: [Conv 3×3, 48  → BatchNorm → ReLU] ×2 → MaxPool → Dropout 0.25   → 12×12
Block 3: [Conv 3×3, 96  → BatchNorm → ReLU] ×2 → MaxPool → Dropout 0.30   → 6×6
Block 4: [Conv 3×3, 192 → BatchNorm → ReLU] ×2                             → 6×6  (Grad-CAM layer)
GlobalAveragePooling → Dense 256 → BatchNorm → ReLU → Dropout 0.5 → Dense 7 → Softmax
```

**Design choices:**

- Two stacked 3×3 convolutions cover a 5×5 region with fewer parameters than a single 5×5 convolution.
- Global average pooling replaces a large Flatten→Dense layer, which keeps the model at 713k parameters.
- The filter widths were chosen with a **CPU benchmark**: a 32-64-128-256 version took about 156 s per epoch, while 24-48-96-192 took about 97 s.

**Transfer learning was not trained.** A MobileNetV2 comparison was considered. On this CPU it would have needed roughly another hour of training, plus upscaling the 48×48 grayscale inputs to 3-channel 96×96. That was judged not worth the cost, so the custom CNN is the only model, and it remains fully explainable.

## Training strategy

| Setting | Value |
|---|---|
| Optimizer | Adam, learning rate 1e-3 |
| Loss | Sparse categorical cross-entropy with **balanced class weights** |
| Batch / max epochs | 64 / 50 |
| Model selection | **Validation macro F1** (custom callback); the test set is never used |
| Callbacks | ReduceLROnPlateau (val loss, ×0.5, patience 3), EarlyStopping (val macro F1, patience 8, restore best), ModelCheckpoint |
| Result | **35 epochs, best epoch 27, 67.8 min on CPU** (about 95–100 s per epoch; one epoch was slowed to 747 s by battery throttling) |

![Training curves](results/training_curves.png)

- **Slow start:** in epochs 1–4 the predictions briefly collapse onto one class. This comes from heavy regularisation, BatchNorm warm-up and the 9.4× Disgust weight.
- **Learning-rate reductions** at epochs 21 and 25 each produced a clear jump in macro F1: 0.480 → 0.511 → 0.553.
- **No overfitting:** training accuracy stays at or below validation accuracy. Training metrics are measured with dropout and augmentation active.
- **Early stopping** ended training at epoch 35 and restored the epoch-27 weights.

## Class imbalance handling

Class weights are computed **from training labels only** as *n / (k · n_c)*:

| Angry | Disgust | Fear | Happy | Sad | Surprise | Neutral |
|---|---|---|---|---|---|---|
| 1.03 | **9.40** | 1.00 | 0.57 | 0.85 | 1.29 | 0.83 |

**Effect:** Disgust reaches **0.75 recall** despite being 1.5% of the data. The cost is low precision (0.32): the model over-predicts Disgust. That is a deliberate trade-off in favour of macro F1. No oversampling was used, and validation and test are untouched.

## Evaluation metrics

Accuracy alone is misleading on imbalanced data, so the project reports accuracy, macro precision, recall and F1 (every class weighted equally), weighted F1, per-class metrics and confusion matrices. Everything is produced by `python -m src.evaluate`.

## Results

| Evaluation | Images | Accuracy | Macro precision | Macro recall | **Macro F1** | Weighted F1 |
|---|---|---|---|---|---|---|
| **Official FER-2013 test** | 3,589 | **60.9%** | 0.560 | 0.614 | **0.570** | **0.608** |
| **Leakage-aware test** | 3,275 | **59.6%** | 0.536 | 0.596 | **0.545** | **0.595** |
| Leaked test images only | 314 | 75.2% | 0.710 | 0.734 | 0.718 | 0.749 |
| Baseline: always "Happy" (official test) | 3,589 | 24.5% | 0.035 | 0.143 | 0.056 | 0.096 |

Top-3 accuracy on the official test set is **89.5%**. For context, human accuracy on FER-2013 is estimated at about 65 ± 5% because of label noise.

### Per-class performance (official test)

| Expression | Precision | Recall | F1 | Support | F1 (leakage-aware) |
|---|---|---|---|---|---|
| Happy | 0.894 | 0.779 | **0.833** | 879 | 0.833 |
| Surprise | 0.687 | 0.803 | **0.741** | 416 | 0.692 |
| Neutral | 0.548 | 0.705 | 0.617 | 626 | 0.607 |
| Angry | 0.569 | 0.438 | 0.495 | 491 | 0.482 |
| Sad | 0.480 | 0.503 | 0.491 | 594 | 0.488 |
| Disgust | 0.318 | 0.746 | 0.446 | 55 | 0.354 |
| Fear | 0.427 | 0.326 | **0.370** | 528 | 0.358 |

![Per-class metrics](results/per_class_metrics.png)

## Confusion matrix

![Normalized confusion matrix](results/confusion_matrix_normalized.png)

- **Fear** is the hardest class. It is confused with Sad (23%), Surprise (15%) and Neutral (14%).
- **Sad ↔ Neutral** is the main two-way confusion: 23% of Sad faces are predicted Neutral, and 13% of Neutral faces are predicted Sad.
- **Happy** and **Surprise** are easiest because of their distinctive mouth shapes.

Raw counts are in `results/confusion_matrix.png`; the full report is in `results/classification_report.txt`.

### Are the confidence bands meaningful? (validation set)

| App band | Share of predictions | Accuracy in band |
|---|---|---|
| High (≥ 70%) | 35.5% | 84.8% |
| Moderate (40–70%) | 44.4% | 50.0% |
| Low (< 40%) | 20.0% | 35.6% |

The bands separate reliable predictions from unreliable ones. They are still **application heuristics**, not calibrated certainty.

## Grad-CAM / Explainability

Grad-CAM weights the last convolutional feature map (`block4_2_relu`, 6×6) by the gradient of the predicted class score. Orange marks the regions that **increased** that score.

![Grad-CAM, correct predictions](results/gradcam/gradcam_correct.png)
![Grad-CAM, misclassifications](results/gradcam/gradcam_misclassified.png)

- **Correct predictions** focus on the mouth and eyes: the open mouth for Angry and Fear, the smile for Happy, the eyes for Surprise.
- **Several misclassifications** attend to hair, background or a beard, which helps explain the error.
- Grad-CAM shows **where the model looked**. It does not prove the model's reasoning is correct. The heatmap is coarse (6×6) and says nothing about what a person feels.

## Streamlit application

| Page | Contents |
|---|---|
| 🏠 Home | Overview, pipeline, supported expressions, key metrics, model summary |
| 📷 Image Detection | Upload, multi-face boxes, prediction and confidence band, top-3, probability chart, Grad-CAM, session analytics |
| 🎥 Live Webcam | Start/stop toggle, live boxes and labels, live session summary |
| 📊 Model Insights | Official vs leakage-aware metrics, curves, confusion matrices, per-class metrics, Grad-CAM, confidence reliability, limitations |
| ℹ️ About | Dataset, architecture, preprocessing, evaluation method, ethics |

The webcam is read with OpenCV **on the machine running Streamlit**, so live mode works when the app runs locally. Frames are processed in memory and never stored.

## Project structure

```
Emotion_Detection_System/
├── app.py                      # Streamlit application
├── src/
│   ├── config.py               # all paths, labels, hyperparameters, thresholds
│   ├── data_loader.py          # FER-2013 loading (+ --download), .npz cache
│   ├── data_quality.py         # blank images, cross-split duplicates, leakage-aware mask
│   ├── preprocessing.py        # to_model_input, augmentation, tf.data, class weights
│   ├── model.py                # custom CNN
│   ├── train.py                # training with macro-F1 model selection
│   ├── evaluate.py             # official + leakage-aware metrics, plots
│   ├── face_detector.py        # Haar cascade detection + padded crops
│   ├── predict.py              # inference pipeline, error types, annotation
│   ├── gradcam.py              # Grad-CAM + example grids
│   ├── analytics.py            # session summary
│   └── utils.py                # plot style, figure saving
├── notebooks/eda_and_model_analysis.ipynb
├── tests/                      # pytest: preprocessing, inference, Streamlit pages
├── models/emotion_model.keras  # trained model (8.7 MB)
├── results/                    # metrics, reports, figures, Grad-CAM examples
├── data/README.md              # dataset instructions (data itself is git-ignored)
├── requirements.txt
└── LICENSE
```

## Installation

```bash
git clone https://github.com/Kashish-13/Emotion_Detection_System.git
cd Emotion_Detection_System
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Tested with Python 3.13 on Windows 11, CPU only.

## How to run locally

The trained model is included in `models/emotion_model.keras`, so the app runs without the dataset:

```bash
streamlit run app.py
```

To reproduce the full pipeline:

```bash
python -m src.data_loader --download   # get FER-2013 (~136 MB) and verify class counts
python -m src.data_quality             # leakage report  -> results/data_leakage_report.json
python -m src.train                    # train the CNN   -> models/emotion_model.keras (~1 h on CPU)
python -m src.evaluate                 # metrics/plots   -> results/
python -m src.gradcam                  # Grad-CAM grids  -> results/gradcam/
python -m src.predict path/to/photo.jpg --save annotated.jpg
```

Open `notebooks/eda_and_model_analysis.ipynb` with the `.venv` interpreter selected as the kernel.

## How to run tests

```bash
pytest -q
```

There are 40 tests covering:

- label mapping
- preprocessing shape and range
- class weights
- deterministic validation pipeline
- blank and leakage masks
- prediction format, probabilities summing to 1, and top-3 ordering
- confidence bands and the low-confidence warning
- no-face, invalid-image, missing-model and corrupt-model handling
- multi-face detection and annotation on real FER faces
- Grad-CAM
- session analytics
- rendering of every Streamlit page

Tests that need the dataset or the model skip themselves if those files are absent.

## Limitations

- **Accuracy ceiling:** about 60% on unseen test faces. Fear, Sad, Angry and Disgust are often confused.
- **Disgust estimates are noisy:** only 55 test images (38 leakage-aware). The model also over-predicts Disgust because of its class weight.
- **Frontal faces only:** the Haar detector misses turned or tilted faces and can produce false positives on textured backgrounds.
- **Domain gap:** the model was trained on 48×48 grayscale web photos with posed expressions. Real webcam conditions (lighting, pose, glasses, masks) reduce accuracy.
- **Leakage handling covers exact duplicates only.** Near-duplicates are not detected.
- **Augmentation artifacts:** shifted training images smear edge pixels (`fill_mode="nearest"`).

## Ethical considerations

- **Expressions are not emotions.** A smile is not proof of happiness, and expressions vary by culture, individual and context.
- The model must **not** be used to diagnose mental health, judge honesty, screen job candidates, monitor students or employees, or infer personality.
- FER-2013's **demographic composition is undocumented**, and performance across groups has **not been audited**. It may be uneven.
- FER-2013 labels are noisy (some duplicated images carry different labels), so the labels themselves are imperfect.
- The app uses wording such as *"detected facial expression"*, never *"you are feeling…"*, and processes webcam frames locally without storing them.

## Future improvements

- A larger CNN or a pretrained backbone (ResNet or EfficientNet on a GPU), and a fair comparison under the same leakage-aware protocol.
- Label smoothing or mixup for noisy labels, test-time augmentation, and probability calibration (temperature scaling).
- A DNN face detector (for example OpenCV YuNet) for better recall on non-frontal faces.
- Perceptual-hash near-duplicate detection, plus a fairness audit on a demographically annotated dataset.

## Author

**Kashish Arya**: [github.com/Kashish-13](https://github.com/Kashish-13)

Licensed under the [MIT License](LICENSE).
