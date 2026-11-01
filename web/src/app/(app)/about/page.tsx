// About & privacy (src/ui/views/about.py). The detailed model evaluation lives on /model.
import Link from "next/link";
import metrics from "@/data/model-metrics.json";
import { EMOTIONS } from "@/lib/emotions";
import { DISCLAIMER, DISTRESS_NOTE } from "@/lib/wellbeing";

export const metadata = { title: "About" };

const FLOW = ["Image / webcam", "Face detection", "Preprocessing", "CNN", "Emotion probabilities", "Top prediction",
  "Optional wellbeing reflection"];
const TECH = ["Next.js", "TypeScript", "TensorFlow.js", "OpenCV.js", "TensorFlow / Keras (training)", "Firebase Auth",
  "Cloud Firestore", "FER-2013"];
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`;

export default function AboutPage() {
  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Learn · About</div>
        <h1 className="title">About <span className="accent">EmotionSense</span></h1>
        <p className="subtitle">Facial-expression analysis with a personal reflection and wellbeing dashboard.</p>
      </div>

      <div className="section" style={{ marginTop: 0 }}><h2>What is EmotionSense?</h2></div>
      <p style={{ maxWidth: "52rem" }}>
        EmotionSense combines a <strong>facial-expression recognition model</strong> with a small set of <strong>reflection and
        wellbeing tools</strong>. The model looks at a face and estimates which of seven expressions it shows. The rest of the
        app turns that into an invitation to check in with yourself — in your own words.
      </p>

      <div className="section"><h2>How it works</h2></div>
      <div className="row">
        {FLOW.map((s, i) => <span key={s} className="row" style={{ gap: 8 }}><span className="chip">{s}</span>{i < FLOW.length - 1 && <span className="muted">→</span>}</span>)}
      </div>
      <ol style={{ marginTop: 14, paddingLeft: 20, maxWidth: "52rem" }}>
        <li><strong>Face detection</strong>: OpenCV&apos;s Haar cascade finds each face.</li>
        <li><strong>Preprocessing</strong>: crop → grayscale → 48×48 → scale to [0, 1] — identical to training.</li>
        <li><strong>CNN</strong>: a custom convolutional network trained on FER-2013 outputs a probability for each of 7
          expressions: {EMOTIONS.join(", ")}.</li>
        <li><strong>Result</strong>: the top prediction, its confidence band and the top-3 alternatives, with a Grad-CAM view of
          where the model looked.</li>
        <li><strong>Reflection (optional)</strong>: check-ins, journaling and short wellbeing activities.</li>
      </ol>
      <p className="muted small" style={{ marginTop: 10 }}>
        In this web app all of this runs in your browser: the same trained weights in TensorFlow.js and the same preprocessing
        in OpenCV.js. The model scores {pct1(metrics.leakageAware.accuracy)} accuracy on unseen test images —
        see <Link href="/model">Model insights</Link> for the full evaluation.
      </p>

      <div className="section"><h2>Technology</h2></div>
      <div className="row">{TECH.map((t) => <span key={t} className="chip">{t}</span>)}</div>

      <div className="grid grid-2" style={{ marginTop: 24 }}>
        <div className="card">
          <div className="card-title">⚠️ Limitations</div>
          <ul className="muted small" style={{ margin: "8px 0 0", paddingLeft: 18 }}>
            <li><strong>A facial expression is not an emotion.</strong> People smile when sad and look neutral when happy.</li>
            <li>Frontal faces only; lighting, head pose, glasses and image quality change predictions.</li>
            <li>FER-2013 is low-resolution, has noisy labels and an undocumented demographic mix; performance may differ across
              groups. Fear, Sad and Angry are often confused.</li>
            <li>The model can be uncertain — low-confidence results are flagged, not hidden.</li>
            <li><strong>Not a medical or diagnostic tool.</strong> It cannot detect stress, anxiety, depression or any mental-health
              condition.</li>
          </ul>
        </div>
        <div className="card">
          <div className="card-title">🔒 Privacy</div>
          <ul className="muted small" style={{ margin: "8px 0 0", paddingLeft: 18 }}>
            <li><strong>Images and webcam frames are never uploaded or stored.</strong> They are analysed in your browser and
              discarded.</li>
            <li>When you choose <strong>Save</strong>, only the detected expression, confidence and top-3 predictions are stored —
              plus your mood and note if you add them.</li>
            <li>Data is stored in <strong>your own space</strong> (<code>users/{"{your-id}"}/checkins</code>). Firestore security rules
              allow only you to read or delete it.</li>
            <li>You can delete any entry, or all your history, on <Link href="/history">History &amp; Insights</Link>.</li>
          </ul>
        </div>
      </div>

      <div className="alert alert-info" style={{ marginTop: 20 }}>{DISCLAIMER}</div>
      <p className="muted small" style={{ marginTop: 10 }}>{DISTRESS_NOTE}</p>
    </>
  );
}
