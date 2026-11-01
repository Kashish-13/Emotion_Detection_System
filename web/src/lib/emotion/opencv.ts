// OpenCV.js (face detection + preprocessing), loaded once from a static file and cached.
import { CASCADE_URL, OPENCV_URL } from "./core";

/* eslint-disable @typescript-eslint/no-explicit-any -- the OpenCV.js script build ships no usable types */
export type CV = any;
export type OpenCv = { cv: CV; classifier: any };

const CASCADE_FILE = "haarcascade_frontalface_default.xml";
let pending: Promise<OpenCv> | null = null;

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).cv) return resolve();
    const el = document.createElement("script");
    el.src = src;
    el.async = true;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error("Could not load the face detector."));
    document.head.appendChild(el);
  });
}

/**
 * Load OpenCV.js and the Haar cascade (the same XML file the Python app uses) once.
 * Note: the OpenCV.js Module has a `then` that resolves to itself, so it must never be awaited
 * or returned from an async function directly — it is always handed out wrapped in an object.
 */
export function loadOpenCv(): Promise<OpenCv> {
  if (!pending) {
    pending = (async () => {
      await loadScript(OPENCV_URL);
      const cv = (window as any).cv;
      if (!cv.Mat) await new Promise<void>((resolve) => { cv.onRuntimeInitialized = () => resolve(); });
      const response = await fetch(CASCADE_URL);
      if (!response.ok) throw new Error("Could not load the face detector model.");
      const xml = new Uint8Array(await response.arrayBuffer());
      try {
        cv.FS_createDataFile("/", CASCADE_FILE, xml, true, false, false);
      } catch { /* already created by an earlier attempt */ }
      const classifier = new cv.CascadeClassifier();
      if (!classifier.load(CASCADE_FILE)) throw new Error("Could not load the face detector model.");
      return { cv, classifier };
    })().catch((err) => {
      pending = null; // allow a retry
      throw err;
    });
  }
  return pending;
}
