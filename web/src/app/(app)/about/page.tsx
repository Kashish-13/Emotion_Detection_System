import metrics from "@/data/model-metrics.json";
import { EMOTIONS, color, emoji } from "@/lib/emotions";

export const metadata = { title: "About the model" };

const FLOW = ["Image", "Haar face detection", "Padded crop · grayscale · 48×48 · ÷255", "CNN", "Softmax · 7 expressions",
  "Top-3 + confidence band"];
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`;

export default function AboutPage() {
  const perClass = Object.entries(metrics.perClassF1LeakageAware).sort((a, b) => a[1] - b[1]);
  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Learn</div>
        <h1 className="title">About the <span className="accent">model</span></h1>
        <p className="subtitle">How predictions are made, how well the model performs, and its limits.</p>
      </div>

      <div className="section" style={{ marginTop: 0 }}><h2>How it works</h2></div>
      <div className="row">
        {FLOW.map((s, i) => <span key={s} className="row" style={{ gap: 8 }}><span className="chip">{s}</span>{i < FLOW.length - 1 && <span className="muted">→</span>}</span>)}
      </div>
      <p className="muted" style={{ marginTop: 12 }}>
        A custom VGG-style CNN ({metrics.parameters.toLocaleString("en-US")} parameters, {metrics.modelSizeMb} MB) trained on
        {" "}{metrics.trainImages.toLocaleString("en-US")} FER-2013 images. The web app runs this same model in your browser
        (TensorFlow.js + OpenCV.js), validated to give the same predictions as the Python pipeline the Streamlit app uses.
      </p>

      <div className="section"><h2>Performance</h2><p>On {metrics.leakageAware.n.toLocaleString("en-US")} test images that do not appear in the training data.</p></div>
      <div className="grid grid-4">
        {[["Accuracy", pct1(metrics.leakageAware.accuracy)], ["Macro F1", metrics.leakageAware.macroF1.toFixed(3)],
          ["Weighted F1", metrics.leakageAware.weightedF1.toFixed(3)], ["Top-3 accuracy", pct1(metrics.top3AccuracyOfficial)]].map(([k, v]) => (
          <div key={k} className="card"><div className="stat-label">{k}</div><div className="stat-value" style={{ color: "var(--primary)", fontSize: "1.8rem" }}>{v}</div></div>
        ))}
      </div>
      <p className="muted small" style={{ marginTop: 10 }}>
        Official FER-2013 test set: {pct1(metrics.official.accuracy)} accuracy, macro F1 {metrics.official.macroF1.toFixed(3)}.
        Always answering &ldquo;Happy&rdquo; would score {pct1(metrics.baselineAlwaysHappyAccuracy)}. Top-3 accuracy is measured on the official test set.
      </p>

      <div className="section"><h2>Where the model struggles</h2><p>Per-class F1 on unseen test images, weakest first.</p></div>
      <div className="card">
        {perClass.map(([e, f1]) => (
          <div key={e} className="bar-row" style={{ "--c": color(e) } as React.CSSProperties}>
            <div className="bar-name"><span aria-hidden="true">{emoji(e)}</span>{e}</div>
            <div className="bar-track"><div className="bar-fill" style={{ width: `${f1 * 100}%` }} /></div>
            <div className="bar-value">{f1.toFixed(2)}</div>
          </div>
        ))}
      </div>

      <div className="section"><h2>Limitations &amp; privacy</h2></div>
      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">⚠️ Limitations</div>
          <ul className="muted small" style={{ margin: "8px 0 0", paddingLeft: 18 }}>
            <li><strong>A facial expression is not an emotion.</strong> People smile when sad and look neutral when happy.</li>
            <li>Frontal faces only; lighting, pose, glasses and image quality change predictions.</li>
            <li>FER-2013 is low-resolution with noisy labels; Fear, Sad and Angry are often confused.</li>
            <li>Not a medical or diagnostic tool.</li>
          </ul>
        </div>
        <div className="card">
          <div className="card-title">🔒 Privacy</div>
          <ul className="muted small" style={{ margin: "8px 0 0", paddingLeft: 18 }}>
            <li>Images and webcam frames are analysed in your browser and never uploaded or stored.</li>
            <li>Saving keeps only the expression, confidence and top-3 — in your own Firestore space.</li>
            <li>Security rules allow only you to read or delete your entries.</li>
          </ul>
        </div>
      </div>
      <p className="muted small" style={{ marginTop: 20 }}>Classes: {EMOTIONS.join(", ")}.</p>
    </>
  );
}
