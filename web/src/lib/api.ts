// Client for the EmotionSense inference API (FastAPI on Hugging Face Spaces).
import { firebaseAuth } from "./firebase";

export const API_URL = (process.env.NEXT_PUBLIC_INFERENCE_API_URL || "").replace(/\/+$/, "");

export const MAX_UPLOAD_MB = 5;
export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/bmp"];

export type FaceResult = {
  index: number;
  box: { x: number; y: number; width: number; height: number } | null;
  emotion: string;
  confidence: number;
  level: "High" | "Moderate" | "Low";
  probabilities: Record<string, number>;
  top3: { emotion: string; probability: number }[];
  smallFace: boolean;
  warning: string | null;
  gradcam: { heatmap: string; modelInput: string } | null;
};

export type PredictResponse = {
  faces: FaceResult[];
  message: string | null;
  image: { width: number; height: number };
  annotatedImage: string;
  labels: string[];
  timingMs: number;
};

export class ApiError extends Error {
  constructor(message: string, public code = "error") {
    super(message);
  }
}

/** Client-side checks before upload (the API validates again). Returns an error message or null. */
export function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.includes(file.type)) return "Please choose a JPG, PNG, WebP or BMP image.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `Images must be smaller than ${MAX_UPLOAD_MB} MB.`;
  if (file.size === 0) return "This file is empty.";
  return null;
}

export async function predict(file: File, opts: { gradcam?: boolean; wholeImage?: boolean } = {}): Promise<PredictResponse> {
  if (!API_URL) throw new ApiError("The prediction service is not configured (NEXT_PUBLIC_INFERENCE_API_URL).", "not_configured");
  const token = await firebaseAuth()?.currentUser?.getIdToken();
  const body = new FormData();
  body.append("file", file);
  body.append("gradcam", String(Boolean(opts.gradcam)));
  body.append("whole_image", String(Boolean(opts.wholeImage)));

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 90_000); // first request after the Space sleeps is slow
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/predict`, {
      method: "POST", body, signal: controller.signal,
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
  } catch {
    throw new ApiError(controller.signal.aborted
      ? "The prediction service took too long to respond. It may be waking up — please try again in a moment."
      : "Could not reach the prediction service. Check your connection and try again.", "network");
  } finally {
    clearTimeout(timer);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(data?.error?.message ?? "Something went wrong while analysing the image.", data?.error?.code);
  }
  return data as PredictResponse;
}

export async function apiHealth(): Promise<boolean> {
  if (!API_URL) return false;
  try {
    const r = await fetch(`${API_URL}/api/health`, { cache: "no-store" });
    return r.ok && (await r.json()).modelLoaded === true;
  } catch {
    return false;
  }
}
