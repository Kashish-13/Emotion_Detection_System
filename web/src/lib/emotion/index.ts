// EmotionSense in-browser inference: the public API used by the pages.
// Everything runs on the user's device — images are never uploaded for analysis.
// Browser-only: call these functions from client components (they are no-ops to import on the server).
import { type FacePrediction } from "./core";
import { loadModel, memoryStats, type Model } from "./model";
import { loadOpenCv, type OpenCv } from "./opencv";
import { analyzeImage, gradCam, type Analysis, type AnalyzeOptions } from "./pipeline";
import { annotatedDataUrl, decodeFile, ImageReadError, imageDataUrl } from "./render";

export * from "./core";
export { captureFrame, drawFaces } from "./render";
export type { Analysis, FaceAnalysis } from "./pipeline";

/** A face result ready for display (same shape the Detect page used with the former Python API). */
export type FaceResult = FacePrediction & {
  index: number;
  gradcam: { heatmap: string; modelInput: string } | null;
};

export type ImageResult = {
  faces: FaceResult[];
  message: string | null;
  image: { width: number; height: number };
  annotatedImage: string;
  timingMs: number;
};

type Engine = { ocv: OpenCv; model: Model };
let engine: Engine | null = null;
let pending: Promise<Engine> | null = null;

/** Load OpenCV.js, the face detector and the CNN once (in parallel); later calls reuse them. */
export function loadEngine(): Promise<{ backend: string }> {
  if (!pending) {
    pending = Promise.all([loadOpenCv(), loadModel()]).then(([ocv, model]) => {
      engine = { ocv, model };
      // Read-only diagnostics for testing memory use: window.__emotionsense.stats()
      (window as unknown as { __emotionsense: unknown }).__emotionsense = { stats: () => memoryStats(model) };
      return engine;
    }).catch((err) => {
      pending = null;
      console.error("EmotionSense engine failed to load", err);
      throw new Error("The emotion model could not be loaded. Check your connection and try again.");
    });
  }
  return pending.then((e) => ({ backend: e.model.backend }));
}

export const engineReady = () => engine !== null;

async function getEngine(): Promise<Engine> {
  await loadEngine();
  return engine!;
}

/** Fast analysis for live video: predictions only (no images, no Grad-CAM). */
export async function analyzeFrame(image: ImageData, opts: AnalyzeOptions = {}): Promise<Analysis> {
  const { ocv, model } = await getEngine();
  return analyzeImage(ocv, model, image, opts);
}

/** Full analysis for an image (upload or webcam snapshot), with the annotated preview and optional Grad-CAM. */
export async function analyzePixels(image: ImageData, opts: { wholeImage?: boolean; gradcam?: boolean } = {}): Promise<ImageResult> {
  const started = performance.now();
  const { ocv, model } = await getEngine();
  try {
    const analysis = await analyzeImage(ocv, model, image, { wholeImageIfNoFace: opts.wholeImage });
    const faces: FaceResult[] = analysis.faces.map(({ input, ...face }) => {
      if (!opts.gradcam) return { ...face, gradcam: null };
      const cam = gradCam(ocv, model, input);
      return { ...face, gradcam: { heatmap: imageDataUrl(cam.overlay), modelInput: imageDataUrl(cam.modelInput) } };
    });
    return {
      faces,
      message: analysis.message,
      image: { width: image.width, height: image.height },
      annotatedImage: annotatedDataUrl(image, faces),
      timingMs: performance.now() - started,
    };
  } catch (err) {
    console.error("EmotionSense analysis failed", err);
    throw new Error("Something went wrong while analysing the image. Please try again.");
  }
}

export async function analyzeFile(file: Blob, opts: { wholeImage?: boolean; gradcam?: boolean } = {}): Promise<ImageResult> {
  let image: ImageData;
  try {
    image = await decodeFile(file);
  } catch (err) {
    if (err instanceof ImageReadError) throw err;
    throw new ImageReadError("The file could not be read as an image. Please upload a JPG or PNG photo.");
  }
  return analyzePixels(image, opts);
}

// Exposed for the parity tests (they compare these against the Python reference).
export { gradCam, analyzeImage };
export const _internals = { getEngine };
