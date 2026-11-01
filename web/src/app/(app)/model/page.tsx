/* eslint-disable @next/next/no-img-element -- static evaluation figures, shown at their natural size */
// Model Insights (src/ui/views/model_insights.py): every number comes from results/ via scripts/sync-model-results.mjs.
import type { CSSProperties } from "react";
import metrics from "@/data/model-metrics.json";
import { color, emoji } from "@/lib/emotions";

export const metadata = { title: "Model insights" };

const FLOW = ["Image / frame", "Haar face detection", "Crop · grayscale · 48×48 · ÷255", "CNN (4 conv blocks)",
  "Softmax · 7 expressions", "Top-3 + confidence band"];
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`;
const n0 = (x: number) => x.toLocaleString("en-US");

function Metric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="card hover">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color: "var(--primary)", fontSize: "1.8rem" }}>{value}</div>
      <div className="stat-hint">{hint}</div>
    </div>
  );
}

function Figure({ src, caption }: { src: string; caption: string }) {
  return (
    <figure className="frame figure">
      <img src={`/results/${src}`} alt={caption} loading="lazy" />
      <figcaption>{caption}</figcaption>
    </figure>
  );
}

export default function ModelInsightsPage() {
  const { leakageAware: clean, official: off, seenInTrainOrVal: seen, baselineAlwaysHappy: base } = metrics;
  const ranked = Object.entries(metrics.perClassLeakageAware).sort((a, b) => a[1].f1 - b[1].f1);
  const rows = [["Official test", off], ["Leakage-aware test", clean], ["Test images also seen in train/val", seen],
    ["Baseline: always “Happy”", base]] as const;
  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Learn · Machine learning</div>
        <h1 className="title">Model <span className="accent">insights</span></h1>
        <p className="subtitle">How the facial-expression model was built, how well it performs and where it struggles.</p>
      </div>

      <div className="section" style={{ marginTop: 0 }}><h2>How the model works</h2><p>From a photo to seven expression probabilities.</p></div>
      <div className="row">
        {FLOW.map((s, i) => <span key={s} className="row" style={{ gap: 8 }}><span className="chip">{s}</span>{i < FLOW.length - 1 && <span className="muted">→</span>}</span>)}
      </div>
      <div className="grid grid-4" style={{ marginTop: 14 }}>
        <Metric label="Parameters" value={n0(metrics.parameters)} hint={`${metrics.modelSizeMb} MB on disk`} />
        <Metric label="Training" value={`${Math.round(metrics.trainingMinutes)} min`} hint={`CPU · best epoch ${metrics.bestEpoch} of ${metrics.epochsRun}`} />
        <Metric label="Inference" value={`${Math.round(metrics.inferenceMsPerFaceCpu)} ms`} hint="Per face, Python on CPU" />
        <Metric label="Training images" value={n0(metrics.trainImages)} hint={`${n0(metrics.valImages)} validation`} />
      </div>
      <pre className="code">{`Input 48×48×1 (grayscale, /255)
4 × [Conv3×3 → BN → ReLU] ×2  (24 → 48 → 96 → 192 filters), MaxPool + Dropout after blocks 1–3
GlobalAveragePooling → Dense 256 → BN → ReLU → Dropout 0.5 → Dense 7 → Softmax`}</pre>
      <p className="muted small">The web app runs this same trained model in your browser (TensorFlow.js + OpenCV.js), validated to give the
        same predictions as the Python pipeline the Streamlit app uses.</p>

      <div className="section"><h2>Model performance</h2>
        <p>Headline: the leakage-aware test set — {n0(clean.n)} test images that appear in neither the training nor the validation set.</p></div>
      <div className="grid grid-4">
        <Metric label="Accuracy" value={pct1(clean.accuracy)} hint="Leakage-aware test" />
        <Metric label="Macro F1" value={clean.macroF1.toFixed(3)} hint="Every class weighted equally" />
        <Metric label="Weighted F1" value={clean.weightedF1.toFixed(3)} hint="Weighted by class size" />
        <Metric label="Top-3 accuracy" value={pct1(metrics.top3AccuracyOfficial)} hint="True label in top 3 · official test" />
      </div>
      <p className="muted small" style={{ marginTop: 10 }}>
        Official FER-2013 test set ({n0(off.n)} images): accuracy {pct1(off.accuracy)}, macro F1 {off.macroF1.toFixed(3)}, weighted
        F1 {off.weightedF1.toFixed(3)}. Baseline that always predicts “Happy”: {pct1(base.accuracy)} accuracy.
      </p>
      <div className="card table-wrap" style={{ padding: "6px 10px", marginTop: 14 }}>
        <table className="table">
          <thead><tr><th>Set</th><th>Images</th><th>Accuracy</th><th>Macro precision</th><th>Macro recall</th><th>Macro F1</th><th>Weighted F1</th></tr></thead>
          <tbody>
            {rows.map(([name, r]) => (
              <tr key={name}><td>{name}</td><td>{n0(r.n)}</td><td>{r.accuracy.toFixed(3)}</td><td>{r.macroPrecision.toFixed(3)}</td>
                <td>{r.macroRecall.toFixed(3)}</td><td>{r.macroF1.toFixed(3)}</td><td>{r.weightedF1.toFixed(3)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid grid-2" style={{ marginTop: 14 }}>
        <div className="card">
          <div className="card-title">⚖️ Why accuracy isn&apos;t enough</div>
          <p className="muted small" style={{ marginTop: 6, lineHeight: 1.6 }}>
            FER-2013 is imbalanced: <b>Disgust</b> has 16.5× fewer training images than <b>Happy</b>. A model that always says
            <i> Happy</i> already scores <b>{pct1(base.accuracy)} accuracy</b>, yet its macro F1 is only <b>{base.macroF1.toFixed(3)}</b>.
            Macro F1 averages every class equally, so ignoring rare classes is penalised. Training used balanced class weights
            and selected the checkpoint by validation macro F1.
          </p>
        </div>
        <div className="card">
          <div className="card-title">🔍 Honest evaluation: data leakage</div>
          <p className="muted small" style={{ marginTop: 6, lineHeight: 1.6 }}>
            About 8% of FER-2013&apos;s official test images are exact pixel copies of training images. On those {seen.n} images the
            model scores <b>{pct1(seen.accuracy)}</b>, versus <b>{pct1(clean.accuracy)}</b> on unseen images — memorisation
            inflates the official score. Both are reported; the leakage-aware one is the headline.
          </p>
        </div>
      </div>
      <div style={{ marginTop: 14 }}><Figure src="training_curves.png" caption="Training curves" /></div>

      <div className="section"><h2>Where the model struggles</h2><p>Per-class F1 on the leakage-aware test set, weakest first.</p></div>
      <div className="grid class-grid">
        {ranked.map(([e, m]) => (
          <div key={e} className="card hover" style={{ "--c": color(e) } as CSSProperties}>
            <div style={{ fontSize: "1.5rem" }} aria-hidden="true">{emoji(e)}</div>
            <div className="card-title">{e}</div>
            <div className="stat-value">{m.f1.toFixed(2)}</div>
            <div className="stat-hint">F1 · recall {Math.round(m.recall * 100)}% · {m.support} images</div>
            <div className="bar-track" style={{ marginTop: 8 }}><div className="bar-fill" style={{ width: `${m.f1 * 100}%` }} /></div>
          </div>
        ))}
      </div>
      <p className="muted small" style={{ marginTop: 10 }}>
        Weakest classes: {ranked.slice(0, 3).map(([e]) => e).join(", ")}. Fear, Sad and Angry are often confused with each other;
        Disgust has very few test images, so its scores are noisy.
      </p>
      <div className="grid grid-2" style={{ marginTop: 14 }}>
        <Figure src="confusion_matrix.png" caption="Confusion matrix (official test)" />
        <Figure src="confusion_matrix_normalized.png" caption="Normalised by true class" />
      </div>
      <details className="card" style={{ marginTop: 14 }}>
        <summary className="card-title">Class-wise metrics table and chart</summary>
        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table className="table">
            <thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th><th>F1 (leakage-aware)</th></tr></thead>
            <tbody>
              {Object.entries(metrics.perClassOfficial).map(([e, m]) => (
                <tr key={e}><td>{emoji(e)} {e}</td><td>{m.precision.toFixed(3)}</td><td>{m.recall.toFixed(3)}</td><td>{m.f1.toFixed(3)}</td>
                  <td>{m.support}</td><td>{metrics.perClassLeakageAware[e as keyof typeof metrics.perClassLeakageAware].f1.toFixed(3)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="grid grid-2" style={{ marginTop: 14 }}>
          <Figure src="per_class_metrics.png" caption="Per-class metrics (official test)" />
          <Figure src="eda_class_distribution.png" caption="Training-set class imbalance" />
        </div>
      </details>

      <div className="section"><h2>Interpretability</h2>
        <p>Grad-CAM shows which regions increased the predicted class score — where the model looked, not proof that it is correct.</p></div>
      <div className="grid grid-2">
        <Figure src="gradcam_correct.png" caption="Correct predictions" />
        <Figure src="gradcam_misclassified.png" caption="Misclassified examples" />
      </div>

      <div className="section"><h2>Are the confidence bands meaningful?</h2><p>Accuracy by model confidence on the validation set.</p></div>
      <div className="card table-wrap" style={{ padding: "6px 10px" }}>
        <table className="table">
          <thead><tr><th>Confidence</th><th>Share of predictions</th><th>Accuracy</th></tr></thead>
          <tbody>
            {metrics.confidenceReliability.map((r) => (
              <tr key={r.bin}><td>{r.bin}</td><td>{pct1(r.share_of_predictions)}</td><td>{pct1(r.accuracy)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small" style={{ marginTop: 10 }}>The High / Moderate / Low bands are application heuristics, not calibrated certainty.</p>
    </>
  );
}
