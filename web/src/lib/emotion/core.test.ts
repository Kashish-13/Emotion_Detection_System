// Unit tests for the in-browser inference logic. Run: npm test  (Node's built-in runner; no extra deps).
// Cross-checks against the Python app (src/config.py) so the two can't silently drift apart.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import {
  ACCEPTED_TYPES, confidenceLevel, cropRect, EMOTIONS, FACE_MIN_NEIGHBORS, FACE_PADDING, FACE_SCALE_FACTOR,
  GRADCAM_LAYER, HIGH_CONFIDENCE, IMG_SIZE, makePrediction, MIN_DETECT_FACE_SIZE, minDetectSize, MODERATE_CONFIDENCE,
  OPENCV_VERSION, primaryFace, pyRound, scaleAndSortBoxes, SMALL_FACE_SIZE, validateFile, WEBCAM_DETECTION_DOWNSCALE,
} from "./core.ts";

const web = join(dirname(fileURLToPath(import.meta.url)), "../../..");
const repo = join(web, "..");
const pyConfig = readFileSync(join(repo, "src/config.py"), "utf8");
const pyValue = (name: string) => {
  const m = pyConfig.match(new RegExp(`^${name}\\s*=\\s*([^#\\n]+)`, "m"));
  assert.ok(m, `${name} not found in src/config.py`);
  return m[1].trim();
};

test("labels and settings match the Python app (src/config.py)", () => {
  assert.deepEqual(EMOTIONS, JSON.parse(pyValue("EMOTIONS").replace(/'/g, '"')));
  assert.equal(EMOTIONS.length, 7);
  const numbers: [string, number][] = [
    ["IMG_SIZE", IMG_SIZE], ["FACE_SCALE_FACTOR", FACE_SCALE_FACTOR], ["FACE_MIN_NEIGHBORS", FACE_MIN_NEIGHBORS],
    ["MIN_DETECT_FACE_SIZE", MIN_DETECT_FACE_SIZE], ["FACE_PADDING", FACE_PADDING], ["SMALL_FACE_SIZE", SMALL_FACE_SIZE],
    ["HIGH_CONFIDENCE", HIGH_CONFIDENCE], ["MODERATE_CONFIDENCE", MODERATE_CONFIDENCE],
    ["WEBCAM_DETECTION_DOWNSCALE", WEBCAM_DETECTION_DOWNSCALE],
  ];
  for (const [name, value] of numbers) assert.equal(Number(pyValue(name)), value, name);
});

test("confidence bands", () => {
  assert.equal(confidenceLevel(0.95), "High");
  assert.equal(confidenceLevel(0.7), "High");
  assert.equal(confidenceLevel(0.69), "Moderate");
  assert.equal(confidenceLevel(0.4), "Moderate");
  assert.equal(confidenceLevel(0.39), "Low");
});

test("makePrediction: argmax, top-3 order, probabilities and warnings", () => {
  const p = makePrediction([0.1, 0.01, 0.08, 0.7, 0.05, 0.04, 0.02], { x: 1, y: 2, width: 3, height: 4 }, false);
  assert.equal(p.emotion, "Happy");
  assert.equal(p.confidence, 0.7);
  assert.equal(p.level, "High");
  assert.deepEqual(p.top3.map((t) => t.emotion), ["Happy", "Angry", "Fear"]);
  assert.deepEqual(Object.keys(p.probabilities), [...EMOTIONS]);
  assert.equal(p.warning, null);
  const low = makePrediction([0.3, 0.1, 0.2, 0.1, 0.1, 0.1, 0.1], null, true);
  assert.equal(low.level, "Low");
  assert.match(low.warning!, /Low-confidence/);
  assert.match(low.warning!, /smaller than 48px/);
  assert.throws(() => makePrediction([0.5, 0.5], null, false));
});

test("cropRect pads by int(w * 0.10) and clips to the image (crop_face)", () => {
  assert.deepEqual(cropRect({ x: 100, y: 100, width: 50, height: 50 }, 640, 480), { x: 95, y: 95, width: 60, height: 60 });
  assert.deepEqual(cropRect({ x: 2, y: 3, width: 50, height: 40 }, 54, 45), { x: 0, y: 0, width: 54, height: 45 });
  assert.deepEqual(cropRect({ x: 10, y: 10, width: 39, height: 39 }, 100, 100), { x: 7, y: 7, width: 45, height: 45 });
});

test("box scaling uses Python rounding and boxes are sorted left to right", () => {
  assert.equal(pyRound(2.5), 2);
  assert.equal(pyRound(3.5), 4);
  assert.equal(pyRound(-0.5), -0);
  assert.deepEqual(scaleAndSortBoxes([{ x: 50, y: 1, width: 20, height: 20 }, { x: 5, y: 2, width: 15, height: 15 }], 0.5),
    [{ x: 10, y: 4, width: 30, height: 30 }, { x: 100, y: 2, width: 40, height: 40 }]);
  assert.equal(minDetectSize(), 30);
  assert.equal(minDetectSize(0.5), 15);
});

test("primaryFace picks the largest box", () => {
  const faces = [{ box: { x: 0, y: 0, width: 10, height: 10 } }, { box: { x: 0, y: 0, width: 40, height: 30 } }, { box: null }];
  assert.equal(primaryFace(faces), faces[1]);
});

test("upload validation", () => {
  assert.equal(validateFile({ type: "image/png", size: 1000 }), null);
  assert.match(validateFile({ type: "image/gif", size: 1000 })!, /JPG, PNG/);
  assert.match(validateFile({ type: "image/jpeg", size: 0 })!, /empty/);
  assert.match(validateFile({ type: "image/jpeg", size: 6 * 1024 * 1024 })!, /smaller than 5 MB/);
  assert.ok(ACCEPTED_TYPES.includes("image/webp"));
});

test("the converted TF.js model has the expected structure and complete weights", () => {
  const model = JSON.parse(readFileSync(join(web, "public/models/emotion/model.json"), "utf8"));
  const layers = model.modelTopology.config.layers;
  assert.equal(model.format, "layers-model");
  assert.equal(layers.length, 36);
  assert.deepEqual(layers[0].config.batch_input_shape, [null, IMG_SIZE, IMG_SIZE, 1]);
  assert.equal(layers.at(-1).config.units, EMOTIONS.length);
  assert.equal(layers.at(-1).config.activation, "softmax");
  assert.ok(layers.some((l: { config: { name: string } }) => l.config.name === GRADCAM_LAYER));
  const specs = model.weightsManifest[0].weights as { shape: number[] }[];
  const values = specs.reduce((n, s) => n + s.shape.reduce((a, b) => a * b, 1), 0);
  assert.equal(values, 713439); // model.count_params() of models/emotion_model.keras
  assert.equal(readFileSync(join(web, "public/models/emotion/weights.bin")).length, values * 4);
});

test("served OpenCV.js version and Haar cascade match the pinned package / the Python app", () => {
  const pkg = JSON.parse(readFileSync(join(web, "package.json"), "utf8"));
  assert.equal(pkg.dependencies["@techstark/opencv-js"].split("-")[0], OPENCV_VERSION);
  const python = join(repo, ".venv/Lib/site-packages/cv2/data/haarcascade_frontalface_default.xml");
  if (existsSync(python)) {
    const sha = (f: string) => createHash("sha256").update(readFileSync(f)).digest("hex");
    assert.equal(sha(join(web, "public/models/haarcascade_frontalface_default.xml")), sha(python));
  }
});
