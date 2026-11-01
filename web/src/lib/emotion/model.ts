// TensorFlow.js model (the validated conversion of models/emotion_model.keras), loaded once and cached.
import { EMOTIONS, GRADCAM_LAYER, IMG_SIZE, MODEL_URL } from "./core";

type TF = typeof import("@tensorflow/tfjs");
type LayersModel = import("@tensorflow/tfjs").LayersModel;
type Layer = import("@tensorflow/tfjs").layers.Layer;
type Tensor = import("@tensorflow/tfjs").Tensor;

export type Model = {
  tf: TF;
  model: LayersModel;
  backend: string;
  featureModel: LayersModel; // input -> block4_2_relu feature map (Grad-CAM)
  head: Layer[];             // remaining layers: feature map -> softmax
};

let pending: Promise<Model> | null = null;

/** Prefer WebGL when it renders in full float32 (needed for parity), then WASM, then plain CPU. */
async function pickBackend(tf: TF, preferred?: string): Promise<string> {
  const candidates = preferred ? [preferred] : ["webgl", "wasm", "cpu"];
  for (const name of candidates) {
    try {
      if (name === "wasm") {
        const wasm = await import("@tensorflow/tfjs-backend-wasm");
        wasm.setWasmPaths("/vendor/tfjs-wasm/");
      }
      if (!(await tf.setBackend(name))) continue;
      await tf.ready();
      if (name === "webgl" && !tf.env().getBool("WEBGL_RENDER_FLOAT32_CAPABLE")) continue; // float16 GPUs
      return name;
    } catch { /* try the next backend */ }
  }
  await tf.setBackend("cpu");
  return "cpu";
}

export function loadModel(preferredBackend?: string): Promise<Model> {
  if (!pending) {
    pending = (async () => {
      const tf = await import("@tensorflow/tfjs");
      const backend = await pickBackend(tf, preferredBackend);
      const model = await tf.loadLayersModel(MODEL_URL);
      const [inShape, outShape] = [model.inputs[0].shape, model.outputs[0].shape];
      if (inShape.join() !== [null, IMG_SIZE, IMG_SIZE, 1].join() || outShape[1] !== EMOTIONS.length) {
        throw new Error("Unexpected model shape.");
      }
      const camIndex = model.layers.findIndex((l) => l.name === GRADCAM_LAYER);
      const featureModel = tf.model({ inputs: model.inputs, outputs: model.layers[camIndex].output as never });
      const head = model.layers.slice(camIndex + 1);
      tf.tidy(() => { (model.predict(tf.zeros([1, IMG_SIZE, IMG_SIZE, 1])) as Tensor).dataSync(); }); // warm-up
      return { tf, model, backend, featureModel, head };
    })().catch((err) => {
      pending = null;
      throw err;
    });
  }
  return pending;
}

/** (N, 48, 48, 1) inputs -> (N, 7) probabilities. */
export async function predictBatch(m: Model, inputs: Float32Array[]): Promise<Float32Array[]> {
  if (!inputs.length) return [];
  const flat = new Float32Array(inputs.length * IMG_SIZE * IMG_SIZE);
  inputs.forEach((x, i) => flat.set(x, i * IMG_SIZE * IMG_SIZE));
  const probs = m.tf.tidy(() => m.model.predict(m.tf.tensor4d(flat, [inputs.length, IMG_SIZE, IMG_SIZE, 1])) as Tensor);
  try {
    const data = (await probs.data()) as Float32Array;
    return inputs.map((_, i) => data.slice(i * EMOTIONS.length, (i + 1) * EMOTIONS.length));
  } finally {
    probs.dispose();
  }
}

/**
 * Grad-CAM raw map (6x6, normalised to [0, 1]) for one face — the same calculation as
 * src/gradcam.py GradCAM.heatmap before its resize: gradient of the predicted class score with
 * respect to block4_2_relu, channel weights = mean gradient, ReLU(weighted sum), divide by max.
 */
export function gradcamRaw(m: Model, input: Float32Array): { cam: Float32Array; rows: number; cols: number; classIndex: number } {
  const { tf } = m;
  const applyHead = (x: Tensor) => m.head.reduce((t, layer) => layer.apply(t, { training: false }) as Tensor, x);
  return tf.tidy(() => {
    const x = tf.tensor4d(input, [1, IMG_SIZE, IMG_SIZE, 1]);
    const feats = m.featureModel.predict(x) as Tensor;               // [1, h, w, c]
    const classIndex = (applyHead(feats).argMax(-1).dataSync() as Int32Array)[0];
    // Score of the predicted class. A one-hot mask (instead of gather) keeps the gradient available on every
    // backend — the WASM backend has no gradient kernel for gather — and is mathematically identical.
    const mask = tf.oneHot([classIndex], EMOTIONS.length).toFloat();
    const grads = tf.grad((f: Tensor) => applyHead(f).mul(mask).sum())(feats);
    const weights = grads.mean([0, 1, 2]);
    let cam = tf.relu(feats.squeeze([0]).mul(weights).sum(-1));
    const max = cam.max().dataSync()[0];
    if (max > 0) cam = cam.div(max);
    const [rows, cols] = cam.shape as [number, number];
    return { cam: cam.dataSync() as Float32Array, rows, cols, classIndex };
  });
}

export function memoryStats(m: Model | null) {
  return m ? { backend: m.backend, numTensors: m.tf.memory().numTensors, numBytes: m.tf.memory().numBytes } : null;
}
