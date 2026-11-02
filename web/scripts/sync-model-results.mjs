// Copies the model's evaluation results from ../results (written by `python -m src.evaluate` / `src.train`) into the
// web app: src/data/model-metrics.json and the figures in public/results/. Run after re-training or re-evaluating:
//   node scripts/sync-model-results.mjs
// The outputs are committed, because Vercel builds only this folder.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const results = join(web, "..", "results");
const read = (name) => JSON.parse(readFileSync(join(results, name), "utf8"));
const m = read("metrics.json");
const s = read("training_summary.json");

const split = (x) => ({
  n: x.n, accuracy: x.accuracy, macroPrecision: x.macro_precision, macroRecall: x.macro_recall,
  macroF1: x.macro_f1, weightedF1: x.weighted_f1,
});
const out = {
  _source: "Generated from results/metrics.json and results/training_summary.json by scripts/sync-model-results.mjs. Do not edit by hand.",
  leakageAware: split(m.leakage_aware_test),
  official: split(m.official_test),
  seenInTrainOrVal: split(m.test_images_seen_in_train_or_val),
  baselineAlwaysHappy: split(m.baseline_always_happy_official_test),
  top3AccuracyOfficial: m.top3_accuracy_official_test,
  baselineAlwaysHappyAccuracy: m.baseline_always_happy_official_test.accuracy,
  parameters: s.parameters,
  modelSizeMb: s.model_size_mb,
  trainImages: s.train_images,
  valImages: s.val_images,
  trainingMinutes: s.training_minutes,
  bestEpoch: s.best_epoch,
  epochsRun: s.epochs_run,
  inferenceMsPerFaceCpu: m.inference_ms_per_face_cpu,
  perClassF1LeakageAware: Object.fromEntries(Object.entries(m.per_class_leakage_aware_test).map(([k, v]) => [k, v.f1])),
  perClassLeakageAware: m.per_class_leakage_aware_test,
  perClassOfficial: m.per_class_official_test,
  confidenceReliability: m.confidence_reliability_validation,
};
writeFileSync(join(web, "src/data/model-metrics.json"), `${JSON.stringify(out, null, 2)}\n`);

const figures = ["training_curves.png", "confusion_matrix.png", "confusion_matrix_normalized.png", "per_class_metrics.png",
  "eda_class_distribution.png", "gradcam/gradcam_correct.png", "gradcam/gradcam_misclassified.png"];
mkdirSync(join(web, "public/results"), { recursive: true });
for (const f of figures) copyFileSync(join(results, f), join(web, "public/results", f.replace("gradcam/", "")));
console.log(`model-metrics.json + ${figures.length} figures updated`);
