// Face detection, preprocessing, prediction and Grad-CAM in the browser.
// Each step mirrors the Python source of truth and was validated bit-for-bit against it:
//   src/face_detector.py  RGBA->GRAY, (optional downscale), equalizeHist, detectMultiScale(1.1, 5, minSize 30)
//   src/face_detector.py  crop_face: padded crop clipped to the image
//   src/preprocessing.py  preprocess_face: ->GRAY, resize 48x48 INTER_AREA, /255, shape (48, 48, 1)
//   src/gradcam.py        GradCAM.heatmap + overlay_heatmap
import {
  cropRect, FACE_MIN_NEIGHBORS, FACE_SCALE_FACTOR, IMG_SIZE, makePrediction, minDetectSize, NO_FACE_MESSAGE,
  scaleAndSortBoxes, SMALL_FACE_SIZE, WHOLE_IMAGE_MESSAGE, type Box, type FacePrediction,
} from "./core";
import { gradcamRaw, predictBatch, type Model } from "./model";
import type { CV, OpenCv } from "./opencv";

export type FaceAnalysis = FacePrediction & { index: number; input: Float32Array };
export type Analysis = { faces: FaceAnalysis[]; message: string | null; width: number; height: number };
export type AnalyzeOptions = { wholeImageIfNoFace?: boolean; detectionDownscale?: number };

/** preprocess_face: any RGBA crop -> Float32Array(48*48) in [0, 1]. */
function toModelInput(cv: CV, rgba: CV): Float32Array {
  const gray = new cv.Mat();
  const small = new cv.Mat();
  try {
    cv.cvtColor(rgba, gray, cv.COLOR_RGBA2GRAY);
    cv.resize(gray, small, new cv.Size(IMG_SIZE, IMG_SIZE), 0, 0, cv.INTER_AREA);
    const out = new Float32Array(IMG_SIZE * IMG_SIZE);
    const px: Uint8Array = small.data;
    for (let i = 0; i < out.length; i++) out[i] = px[i] / 255; // == float32(v) / 255 in NumPy (correctly rounded)
    return out;
  } finally {
    gray.delete();
    small.delete();
  }
}

/** FaceDetector.detect: boxes at full resolution, sorted left to right. */
function detectFaces({ cv, classifier }: OpenCv, rgba: CV, downscale = 1): Box[] {
  const gray = new cv.Mat();
  const scaled = new cv.Mat();
  const equalized = new cv.Mat();
  const rects = new cv.RectVector();
  try {
    cv.cvtColor(rgba, gray, cv.COLOR_RGBA2GRAY);
    let work = gray;
    if (downscale !== 1) {
      cv.resize(gray, scaled, new cv.Size(0, 0), downscale, downscale, cv.INTER_AREA);
      work = scaled;
    }
    cv.equalizeHist(work, equalized);
    const min = minDetectSize(downscale);
    classifier.detectMultiScale(equalized, rects, FACE_SCALE_FACTOR, FACE_MIN_NEIGHBORS, 0,
      new cv.Size(min, min), new cv.Size(0, 0));
    const boxes: Box[] = [];
    for (let i = 0; i < rects.size(); i++) {
      const r = rects.get(i);
      boxes.push({ x: r.x, y: r.y, width: r.width, height: r.height });
    }
    return scaleAndSortBoxes(boxes, downscale);
  } finally {
    gray.delete();
    scaled.delete();
    equalized.delete();
    rects.delete();
  }
}

/** EmotionPredictor.analyze: detect every face in an RGBA image and classify its expression. */
export async function analyzeImage(ocv: OpenCv, m: Model, image: ImageData, opts: AnalyzeOptions = {}): Promise<Analysis> {
  const { cv } = ocv;
  const { width, height } = image;
  const src = cv.matFromImageData(image);
  let boxes: Box[];
  let inputs: Float32Array[];
  try {
    boxes = detectFaces(ocv, src, opts.detectionDownscale ?? 1);
    if (!boxes.length) {
      if (!opts.wholeImageIfNoFace) return { faces: [], message: NO_FACE_MESSAGE, width, height };
      inputs = [toModelInput(cv, src)];
    } else {
      inputs = boxes.map((b) => {
        const r = cropRect(b, width, height);
        const roi = src.roi(new cv.Rect(r.x, r.y, r.width, r.height));
        try {
          return toModelInput(cv, roi);
        } finally {
          roi.delete();
        }
      });
    }
  } finally {
    src.delete();
  }

  const probs = await predictBatch(m, inputs);
  if (!boxes.length) {
    const face = makePrediction(probs[0], null, Math.min(width, height) < SMALL_FACE_SIZE);
    return { faces: [{ ...face, index: 1, input: inputs[0] }], message: WHOLE_IMAGE_MESSAGE, width, height };
  }
  const faces = boxes.map((b, i) => ({
    ...makePrediction(probs[i], b, Math.min(b.width, b.height) < SMALL_FACE_SIZE), index: i + 1, input: inputs[i],
  }));
  return { faces, message: null, width, height };
}

// ---------------------------------------------------------------------------------------------
// Grad-CAM (src/gradcam.py)
// ---------------------------------------------------------------------------------------------
const OVERLAY_RGB = [235, 104, 52];      // orange: one hue, opacity = importance
const f32 = Math.fround;                  // reproduce NumPy float32 arithmetic step by step

function resizeCubicF32(cv: CV, data: Float32Array, cols: number, rows: number, size: number): Float32Array {
  const src = cv.matFromArray(rows, cols, cv.CV_32F, Array.from(data));
  const dst = new cv.Mat();
  try {
    cv.resize(src, dst, new cv.Size(size, size), 0, 0, cv.INTER_CUBIC);
    return new Float32Array(dst.data32F);
  } finally {
    src.delete();
    dst.delete();
  }
}

export type GradCam = {
  heat: Float32Array;        // 48x48 in [0, 1] — GradCAM.heatmap output
  classIndex: number;
  overlay: ImageData;        // 192x192 — overlay_heatmap output
  modelInput: ImageData;     // 192x192 — the 48x48 model input enlarged (INTER_CUBIC)
};

export function gradCam(ocv: OpenCv, m: Model, input: Float32Array, size = 192): GradCam {
  const { cv } = ocv;
  const raw = gradcamRaw(m, input);
  // GradCAM.heatmap: cv2.resize(cam, (48, 48), INTER_CUBIC), then clip to [0, 1]
  const heat = resizeCubicF32(cv, raw.cam, raw.cols, raw.rows, IMG_SIZE).map((v) => Math.min(1, Math.max(0, v)));

  // overlay_heatmap(face_gray, heat): face_gray = (input * 255).astype(uint8)
  const faceU8 = new Uint8Array(input.length);
  for (let i = 0; i < input.length; i++) faceU8[i] = Math.trunc(f32(input[i] * 255));
  const gray = resizeCubicF32(cv, Float32Array.from(faceU8), IMG_SIZE, IMG_SIZE, size);
  const heatBig = resizeCubicF32(cv, heat, IMG_SIZE, IMG_SIZE, size);
  const overlay = new ImageData(size, size);
  for (let i = 0; i < size * size; i++) {
    const alpha = f32(f32(Math.min(1, Math.max(0, heatBig[i]))) * f32(0.65));
    const keep = f32(1 - alpha);
    for (let c = 0; c < 3; c++) {
      const v = f32(f32(gray[i] * keep) + f32(OVERLAY_RGB[c] * alpha));
      overlay.data[i * 4 + c] = Math.trunc(Math.min(255, Math.max(0, v))); // np.clip(...).astype(np.uint8)
    }
    overlay.data[i * 4 + 3] = 255;
  }

  // Detect page "model input": cv2.resize(face_u8, (192, 192), INTER_CUBIC)
  const small = cv.matFromArray(IMG_SIZE, IMG_SIZE, cv.CV_8UC1, Array.from(faceU8));
  const big = new cv.Mat();
  const modelInput = new ImageData(size, size);
  try {
    cv.resize(small, big, new cv.Size(size, size), 0, 0, cv.INTER_CUBIC);
    const px: Uint8Array = big.data;
    for (let i = 0; i < size * size; i++) {
      modelInput.data.set([px[i], px[i], px[i], 255], i * 4);
    }
  } finally {
    small.delete();
    big.delete();
  }
  return { heat, classIndex: raw.classIndex, overlay, modelInput };
}
