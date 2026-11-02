import Link from "next/link";
import { EMOTIONS, color, emoji } from "@/lib/emotions";
import metrics from "@/data/model-metrics.json";

const STEPS = [
  ["Upload a photo or use your webcam", "Everything is analysed in your browser — images are never uploaded or stored."],
  ["The CNN analyses each face", "OpenCV finds every face; a CNN trained on FER-2013 estimates its expression."],
  ["Understand the result", "Confidence, top-3 alternatives, all seven probabilities and Grad-CAM model attention."],
];

// Everything available after signing in (each link goes through login when signed out).
const FEATURES = [
  ["📷", "Emotion detection", "Photo or webcam, with confidence, all seven probabilities and Grad-CAM.", "/detect"],
  ["📝", "Daily check-in", "Note your mood, energy, stress and sleep in about a minute.", "/checkin"],
  ["📈", "Wellbeing tracker", "See your mood, stress, energy and sleep trends over 7 or 30 days.", "/tracker"],
  ["🌿", "Ways to feel better", "Breathing, grounding and practical ideas for stress, worry, low mood, anger and sleep.", "/wellbeing"],
  ["🗂️", "History & insights", "Your saved results and check-ins, with filters and simple patterns.", "/history"],
  ["🤝", "Professional support", "Verified helplines and how to find and check a mental-health professional.", "/support"],
];

const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`;

export default function Landing() {
  return (
    <>
      <div className="container">
        <header className="public-nav">
          <Link href="/" className="brand" style={{ padding: 0 }}><span className="brand-mark">ES</span>EmotionSense</Link>
          <nav className="row">
            <Link href="/login" className="btn btn-ghost">Log in</Link>
            <Link href="/signup" className="btn btn-primary">Sign up</Link>
          </nav>
        </header>

        <section className="hero">
          <div>
            <div className="eyebrow">Facial expression recognition · Deep learning</div>
            <h1>Understand your expressions.<br /><span style={{ color: "var(--primary)" }}>Learn how the model sees them.</span></h1>
            <p className="lead">
              EmotionSense detects faces in a photo and classifies each facial expression into seven categories with a
              custom convolutional neural network trained on FER-2013, then explains the result with confidence scores
              and Grad-CAM.
            </p>
            <div className="row" style={{ marginTop: 22 }}>
              <Link href="/detect" className="btn btn-primary">Try Emotion Detection</Link>
            </div>
            <div className="row" style={{ marginTop: 16 }}>
              <span className="chip">🧠 7 expressions</span>
              <span className="chip">🌿 Not a diagnostic tool</span>
            </div>
          </div>
          <div className="card">
            <div className="stat-label">The seven expression classes</div>
            <div className="row" style={{ marginTop: 10 }}>
              {EMOTIONS.map((e) => (
                <span key={e} className="pill" style={{ "--c": color(e) } as React.CSSProperties}>{emoji(e)} {e}</span>
              ))}
            </div>
            <div className="grid grid-2" style={{ marginTop: 18 }}>
              <div><div className="stat-label">Accuracy (unseen test faces)</div><div className="stat-value">{pct1(metrics.leakageAware.accuracy)}</div></div>
              <div><div className="stat-label">Top-3 accuracy</div><div className="stat-value">{pct1(metrics.top3AccuracyOfficial)}</div></div>
              <div><div className="stat-label">Macro F1</div><div className="stat-value">{metrics.leakageAware.macroF1.toFixed(3)}</div></div>
              <div><div className="stat-label">Parameters</div><div className="stat-value">{metrics.parameters.toLocaleString("en-US")}</div></div>
            </div>
            <p className="muted small" style={{ marginTop: 14 }}>
              Measured on {metrics.leakageAware.n.toLocaleString("en-US")} FER-2013 test images that do not appear in the
              training data. A model that always answers &ldquo;Happy&rdquo; would score {pct1(metrics.baselineAlwaysHappyAccuracy)}.
            </p>
          </div>
        </section>

        <section className="section"><h2>How it works</h2><p>From a photo to an explained prediction in three steps.</p></section>
        <div className="grid grid-3">
          {STEPS.map(([title, text], i) => (
            <div key={title} className="card hover step">
              <div className="step-n">{i + 1}</div>
              <div><div className="card-title">{title}</div><p className="muted small" style={{ marginTop: 4 }}>{text}</p></div>
            </div>
          ))}
        </div>

        <section className="section"><h2>What&apos;s inside</h2><p>A free account gives you the full EmotionSense toolkit.</p></section>
        <div className="grid grid-3">
          {FEATURES.map(([icon, title, text, href]) => (
            <Link key={href} href={href} className="card hover feature-card">
              <div style={{ fontSize: "1.4rem" }} aria-hidden="true">{icon}</div>
              <div className="card-title" style={{ marginTop: 4 }}>{title}</div>
              <p className="muted small" style={{ marginTop: 2 }}>{text}</p>
            </Link>
          ))}
        </div>

        <div className="alert alert-info" style={{ marginTop: 28 }}>
          EmotionSense reads <strong>facial expressions</strong>, which are not a reliable measure of what someone actually
          feels. It is a portfolio machine-learning project, not a medical or diagnostic tool.
        </div>
      </div>
      <footer className="footer"><div className="container row" style={{ justifyContent: "space-between" }}>
        <span>EmotionSense · CNN trained on FER-2013</span>
        <a href="https://github.com/Kashish-13/Emotion_Detection_System" target="_blank" rel="noopener noreferrer">Source on GitHub ↗</a>
      </div></footer>
    </>
  );
}
