// Pure, dependency-free inference logic, mirrored from the Python app (the source of truth):
// src/config.py, src/predict.py (make_prediction, confidence_level) and src/face_detector.py (crop_face).
// Kept free of imports so it can be unit-tested with `node --test`.

/** The seven FER-2013 classes in the model's output order (src/config.py EMOTIONS). Do not reorder. */
export const EMOTIONS = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"] as const;
export type Emotion = (typeof EMOTIONS)[number];

// src/config.py
export const IMG_SIZE = 48;
export const FACE_SCALE_FACTOR = 1.1;
export const FACE_MIN_NEIGHBORS = 5;
export const MIN_DETECT_FACE_SIZE = 30;
export const FACE_PADDING = 0.1;
export const SMALL_FACE_SIZE = 48;
export const HIGH_CONFIDENCE = 0.7;
export const MODERATE_CONFIDENCE = 0.4;
export const WEBCAM_DETECTION_DOWNSCALE = 0.5;
export const GRADCAM_LAYER = "block4_2_relu"; // last convolutional feature map (validated against Python)

// Static assets (web/public). OPENCV_VERSION must match the pinned @techstark/opencv-js package.
export const OPENCV_VERSION = "4.12.0";
export const OPENCV_URL = `/vendor/opencv-${OPENCV_VERSION}.js`;
export const CASCADE_URL = "/models/haarcascade_frontalface_default.xml";
export const MODEL_URL = "/models/emotion/model.json";

// User-facing messages (same wording as src/predict.py).
export const NO_FACE_MESSAGE = "No face detected. Try a well-lit, front-facing photo where the face is clearly visible, "
  + "or treat the whole image as one face for an already-cropped face.";
export const WHOLE_IMAGE_MESSAGE = "No face detected, so the whole image was treated as one face.";

export type Level = "High" | "Moderate" | "Low";
export type Box = { x: number; y: number; width: number; height: number };

export type FacePrediction = {
  box: Box | null; // null when the whole image was used as the face
  emotion: Emotion;
  confidence: number;
  level: Level;
  probabilities: Record<Emotion, number>;
  top3: { emotion: Emotion; probability: number }[];
  smallFace: boolean;
  warning: string | null;
};

/** Application confidence band (a heuristic, not calibrated certainty). */
export function confidenceLevel(confidence: number): Level {
  if (confidence >= HIGH_CONFIDENCE) return "High";
  return confidence >= MODERATE_CONFIDENCE ? "Moderate" : "Low";
}

/** One softmax vector -> prediction (src/predict.py make_prediction). */
export function makePrediction(probs: ArrayLike<number>, box: Box | null, smallFace: boolean): FacePrediction {
  if (probs.length !== EMOTIONS.length) throw new Error(`expected ${EMOTIONS.length} probabilities, got ${probs.length}`);
  const order = EMOTIONS.map((_, i) => i).sort((a, b) => probs[b] - probs[a]);
  const best = order[0];
  const confidence = probs[best];
  const level = confidenceLevel(confidence);
  const notes: string[] = [];
  if (level === "Low") notes.push("Low-confidence prediction. Consider using a clearer, front-facing image.");
  if (smallFace) notes.push(`Face is smaller than ${SMALL_FACE_SIZE}px, so detail is limited.`);
  return {
    box,
    emotion: EMOTIONS[best],
    confidence,
    level,
    probabilities: Object.fromEntries(EMOTIONS.map((e, i) => [e, probs[i]])) as Record<Emotion, number>,
    top3: order.slice(0, 3).map((i) => ({ emotion: EMOTIONS[i], probability: probs[i] })),
    smallFace,
    warning: notes.join(" ") || null,
  };
}

/** Padded crop rectangle clipped to the image (src/face_detector.py crop_face). */
export function cropRect(box: Box, imageWidth: number, imageHeight: number, padding = FACE_PADDING) {
  const padW = Math.trunc(box.width * padding); // Python int() truncates toward zero
  const padH = Math.trunc(box.height * padding);
  const top = Math.max(0, box.y - padH);
  const left = Math.max(0, box.x - padW);
  const bottom = Math.min(imageHeight, box.y + box.height + padH);
  const right = Math.min(imageWidth, box.x + box.width + padW);
  return { x: left, y: top, width: right - left, height: bottom - top };
}

/** Python's round(): round half to even. */
export function pyRound(v: number): number {
  const r = Math.round(v);
  return Math.abs(v % 1) === 0.5 && r % 2 !== 0 ? r - 1 : r;
}

/** Map boxes detected on a downscaled image back to full resolution and sort left to right
 *  (src/face_detector.py FaceDetector.detect). */
export function scaleAndSortBoxes(boxes: Box[], downscale = 1): Box[] {
  const s = (v: number) => (downscale === 1 ? v : pyRound(v / downscale));
  return boxes
    .map((b) => ({ x: s(b.x), y: s(b.y), width: s(b.width), height: s(b.height) }))
    .sort((a, b) => a.x - b.x);
}

/** Minimum face size passed to detectMultiScale (src/face_detector.py). */
export const minDetectSize = (downscale = 1) => Math.max(1, Math.trunc(MIN_DETECT_FACE_SIZE * downscale));

/** The largest face, usually the person closest to the camera (src/ui/views/webcam.py _primary). */
export function primaryFace<T extends { box: Box | null }>(faces: T[]): T | undefined {
  return faces.reduce<T | undefined>((best, f) => {
    const area = f.box ? f.box.width * f.box.height : 0;
    const bestArea = best?.box ? best.box.width * best.box.height : -1;
    return area > bestArea ? f : best;
  }, undefined);
}

export const MAX_UPLOAD_MB = 5;
export const MAX_IMAGE_PIXELS = 25_000_000;
export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/bmp"];

/** Client-side upload checks. Returns an error message or null. */
export function validateFile(file: { type: string; size: number }): string | null {
  if (!ACCEPTED_TYPES.includes(file.type)) return "Please choose a JPG, PNG, WebP or BMP image.";
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `Images must be smaller than ${MAX_UPLOAD_MB} MB.`;
  return null;
}
