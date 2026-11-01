// Browser image helpers: decoding uploads, grabbing webcam frames, and drawing results
// (same box colours and labels as src/predict.py annotate_image).
import { MAX_IMAGE_PIXELS, type Box, type Level } from "./core";

// LEVEL_COLORS in src/predict.py (BGR there, RGB here). The label also states the level.
const LEVEL_COLORS: Record<Level, string> = { High: "rgb(40,160,60)", Moderate: "rgb(235,165,0)", Low: "rgb(220,60,60)" };

export class ImageReadError extends Error {}

/** Decode an uploaded file to RGBA pixels (EXIF orientation applied, no colour conversion — as validated). */
export async function decodeFile(file: Blob): Promise<ImageData> {
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image", premultiplyAlpha: "none", colorSpaceConversion: "none" });
  } catch {
    throw new ImageReadError("The file could not be read as an image. Please upload a JPG or PNG photo.");
  }
  try {
    if (bitmap.width * bitmap.height > MAX_IMAGE_PIXELS) {
      throw new ImageReadError("This image's dimensions are too large. Please use a smaller photo.");
    }
    const canvas = document.createElement("canvas");
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
    ctx.drawImage(bitmap, 0, 0);
    return ctx.getImageData(0, 0, canvas.width, canvas.height);
  } finally {
    bitmap.close();
  }
}

/** Draw the current video frame, mirrored like the Streamlit webcam (cv2.flip), and return its pixels. */
export function captureFrame(video: HTMLVideoElement, canvas: HTMLCanvasElement): ImageData {
  const w = video.videoWidth;
  const h = video.videoHeight;
  if (canvas.width !== w) canvas.width = w;
  if (canvas.height !== h) canvas.height = h;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.save();
  ctx.setTransform(-1, 0, 0, 1, w, 0);
  ctx.drawImage(video, 0, 0, w, h);
  ctx.restore();
  return ctx.getImageData(0, 0, w, h);
}

type Labelled = { box: Box | null; emotion: string; confidence: number; level: Level };

/** annotate_image: a box and an "#1 EMOTION 91%" label above every detected face. */
export function drawFaces(ctx: CanvasRenderingContext2D, faces: Labelled[]) {
  const { width, height } = ctx.canvas;
  const scale = Math.max(0.5, Math.min(width, height) / 900);
  const thickness = Math.max(1, Math.round(2 * scale));
  ctx.font = `600 ${Math.round(17 * scale)}px Inter, system-ui, sans-serif`;
  ctx.textBaseline = "top";
  faces.forEach((face, i) => {
    if (!face.box) return;
    const { x, y, width: w, height: h } = face.box;
    const color = LEVEL_COLORS[face.level];
    ctx.strokeStyle = color;
    ctx.lineWidth = thickness + 1;
    ctx.strokeRect(x, y, w, h);
    const label = `#${i + 1} ${face.emotion.toUpperCase()} ${Math.round(face.confidence * 100)}%${face.level === "Low" ? " (low conf.)" : ""}`;
    const textW = ctx.measureText(label).width;
    const textH = Math.round(17 * scale) + 6;
    const top = y - textH > 0 ? y - textH : y + h; // keep the label inside the image
    ctx.fillStyle = color;
    ctx.fillRect(x, top, textW + 8, textH);
    ctx.fillStyle = "#fff";
    ctx.fillText(label, x + 4, top + 3);
  });
}

/** The image with boxes, as a JPEG data URL no larger than maxSide (like the API's preview). */
export function annotatedDataUrl(image: ImageData, faces: Labelled[], maxSide = 1280): string {
  const canvas = document.createElement("canvas");
  canvas.width = image.width;
  canvas.height = image.height;
  const ctx = canvas.getContext("2d")!;
  ctx.putImageData(image, 0, 0);
  drawFaces(ctx, faces);
  const scale = Math.min(1, maxSide / Math.max(image.width, image.height));
  if (scale === 1) return canvas.toDataURL("image/jpeg", 0.85);
  const out = document.createElement("canvas");
  out.width = Math.round(image.width * scale);
  out.height = Math.round(image.height * scale);
  out.getContext("2d")!.drawImage(canvas, 0, 0, out.width, out.height);
  return out.toDataURL("image/jpeg", 0.85);
}

export function imageDataUrl(image: ImageData): string {
  const canvas = document.createElement("canvas");
  canvas.width = image.width;
  canvas.height = image.height;
  canvas.getContext("2d")!.putImageData(image, 0, 0);
  return canvas.toDataURL("image/png");
}
