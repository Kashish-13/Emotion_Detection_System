"use client";

/* eslint-disable @next/next/no-img-element -- results are data: URLs generated in the browser */
import Link from "next/link";
import { useEffect, useRef, useState, type DragEvent } from "react";
import { EmotionBars, RankCards, ResultCard } from "@/components/Emotion";
import WebcamPanel from "@/components/WebcamPanel";
import { SavedMessage, SuggestionList } from "@/components/Wellbeing";
import { useAuth } from "@/lib/auth";
import {
  ACCEPTED_TYPES, analyzeFile, analyzePixels, loadEngine, MAX_UPLOAD_MB, validateFile, type ImageResult,
} from "@/lib/emotion";
import { emoji } from "@/lib/emotions";
import { detectionEntry, saveEntry } from "@/lib/history";
import { logPredictions, rememberFace } from "@/lib/session";
import { MOODS, SELF_CHECK_PROMPT, suggestionsFor } from "@/lib/wellbeing";

const TIPS = [
  ["🙂", "Face the camera", "Frontal faces work best; turned heads are often missed."],
  ["💡", "Even, bright light", "Heavy shadows and backlight lower confidence."],
  ["🔍", "Big enough", "Faces at least ~50 px wide; the model sees 48×48 grayscale."],
  ["🧠", "Seven expressions", "Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral."],
];

type Status = "idle" | "loading" | "done" | "error";
type Mode = "upload" | "webcam";
type Source = { kind: "file"; file: File } | { kind: "frame"; frame: ImageData };

export default function DetectView() {
  const { user } = useAuth();
  const input = useRef<HTMLInputElement>(null);
  const [engine, setEngine] = useState<"loading" | "ready" | "error">("loading");
  const [engineError, setEngineError] = useState<string | null>(null);
  // The dashboard's "Use camera" opens this page on the webcam tab (/detect?mode=webcam).
  const [mode, setMode] = useState<Mode>(() =>
    new URLSearchParams(window.location.search).get("mode") === "webcam" ? "webcam" : "upload");
  const [source, setSource] = useState<Source | null>(null);
  const [gradcam, setGradcam] = useState(true);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImageResult | null>(null);
  const [selected, setSelected] = useState(0);
  const [saved, setSaved] = useState<Map<number, boolean>>(new Map()); // face index -> saved to the cloud?
  const [mood, setMood] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [drag, setDrag] = useState(false);

  function initEngine() {
    setEngine("loading");
    setEngineError(null);
    loadEngine().then(() => setEngine("ready"), (err: Error) => { setEngine("error"); setEngineError(err.message); });
  }
  useEffect(initEngine, []);

  async function run(src: Source, wholeImage = false) {
    setSource(src);
    setResult(null);
    setSaved(new Map());
    setSelected(0);
    setMood(null);
    if (src.kind === "file") {
      const problem = validateFile(src.file);
      if (problem) {
        setError(problem);
        setStatus("error");
        return;
      }
    }
    setError(null);
    setStatus("loading");
    try {
      const opts = { gradcam, wholeImage };
      const r = await (src.kind === "file" ? analyzeFile(src.file, opts) : analyzePixels(src.frame, opts));
      setResult(r);
      setStatus("done");
      if (r.faces.length) {
        const sourceLabel = src.kind === "frame" ? "webcam" : "image";
        logPredictions(r.faces, sourceLabel);
        rememberFace(r.faces[0], sourceLabel);
      }
    } catch (err) {
      setError((err as Error).message);
      setStatus("error");
    }
  }

  function pick(f: File | undefined) {
    // A file chosen (or dropped) while the model is still loading waits for it instead of being ignored.
    if (f) run({ kind: "file", file: f });
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    pick(e.dataTransfer.files?.[0]);
  }

  function reset() {
    setSource(null);
    setResult(null);
    setStatus("idle");
    setError(null);
    if (input.current) input.current.value = "";
  }

  async function save() {
    if (!user || !result) return;
    setSaving(true);
    const cloud = await saveEntry(user.uid, detectionEntry(result.faces[selected], source?.kind === "frame" ? "webcam" : "web", mood));
    setSaved(new Map(saved).set(selected, cloud));
    setSaving(false);
  }

  const face = result?.faces[selected];
  const ready = engine === "ready";
  const showPicker = mode === "upload" && (status === "idle" || (status === "error" && !result));

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Analyze</div>
        <h1 className="title">Detect <span className="accent">emotion</span></h1>
        <p className="subtitle">Upload a photo or use your webcam. The model finds each face and estimates its facial
          expression — right here in your browser.</p>
      </div>

      <div className="row" style={{ marginBottom: 16 }} role="tablist" aria-label="Image source">
        {(["upload", "webcam"] as Mode[]).map((m) => (
          <button key={m} role="tab" aria-selected={mode === m} className={`chip${mode === m ? " active" : ""}`}
                  onClick={() => { setMode(m); reset(); }}>
            {m === "upload" ? "Upload image" : "Webcam"}
          </button>
        ))}
      </div>

      {engine === "loading" && (
        <div className="card row" style={{ gap: 14, marginBottom: 16 }} role="status">
          <span className="spinner" style={{ color: "var(--primary)" }} />
          <div>
            <div className="card-title">Loading emotion model…</div>
            <p className="muted small">Downloading the face detector and the CNN (about 14 MB, cached after the first visit).</p>
          </div>
        </div>
      )}
      {engine === "error" && (
        <div className="alert alert-error row" role="alert" style={{ justifyContent: "space-between", marginBottom: 16 }}>
          <span>{engineError}</span>
          <button className="btn btn-sm" onClick={initEngine}>Try again</button>
        </div>
      )}

      <input ref={input} type="file" accept={ACCEPTED_TYPES.join(",")} hidden
             onChange={(e) => pick(e.target.files?.[0])} />

      {mode === "webcam" && (
        <div style={{ marginBottom: 24 }}>
          <WebcamPanel ready={ready} onSnapshot={(frame) => run({ kind: "frame", frame })} />
        </div>
      )}

      {showPicker && (
        <>
          <div className={`dropzone${drag ? " drag" : ""}`} role="button" tabIndex={ready ? 0 : -1} aria-disabled={!ready}
               style={ready ? undefined : { opacity: 0.6, cursor: "not-allowed" }}
               onClick={() => ready && input.current?.click()}
               onKeyDown={(e) => ready && (e.key === "Enter" || e.key === " ") && input.current?.click()}
               onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}>
            <div className="icon" aria-hidden="true">📷</div>
            <div className="card-title">Drop an image or choose a photo</div>
            <p className="muted small" style={{ marginTop: 4 }}>
              JPG, PNG, WebP or BMP · up to {MAX_UPLOAD_MB} MB · one or several faces · analysed on your device, never uploaded
            </p>
            <span className="btn btn-primary" style={{ marginTop: 16 }} aria-disabled={!ready}>
              {ready ? "Choose image" : "Loading model…"}
            </span>
          </div>
          <label className="check" style={{ marginTop: 14 }}>
            <input type="checkbox" checked={gradcam} onChange={(e) => setGradcam(e.target.checked)} />
            Include Grad-CAM model attention
          </label>
          {status === "idle" && (
            <>
              <div className="section"><h2>What the model looks for</h2></div>
              <div className="grid grid-4">
                {TIPS.map(([icon, title, text]) => (
                  <div key={title} className="card hover">
                    <div style={{ fontSize: "1.4rem" }} aria-hidden="true">{icon}</div>
                    <div className="card-title" style={{ marginTop: 4 }}>{title}</div>
                    <p className="muted small">{text}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
      {error && status === "error" && !result && <div className="alert alert-error" role="alert" style={{ marginTop: 14 }}>{error}</div>}

      {status === "loading" && (
        <div className="card row" style={{ gap: 14 }} role="status">
          <span className="spinner" style={{ color: "var(--primary)" }} />
          <div>
            <div className="card-title">Analysing {source?.kind === "file" ? source.file.name : "webcam frame"}…</div>
            <p className="muted small">Detecting faces and running the CNN on your device.</p>
          </div>
        </div>
      )}

      {status === "done" && result && result.faces.length === 0 && (
        <div className="stack">
          <div className="alert alert-warning">{result.message ?? "No face detected."}</div>
          <div className="frame" style={{ maxWidth: 520 }}><img src={result.annotatedImage} alt="Analysed image" /></div>
          <div className="row">
            <button className="btn btn-primary" onClick={() => source && run(source, true)}>Treat the whole image as one face</button>
            <button className="btn" onClick={reset}>{mode === "webcam" ? "Close result" : "Try another image"}</button>
          </div>
        </div>
      )}

      {status === "done" && result && face && (
        <>
          {result.message && <div className="alert alert-info" style={{ marginBottom: 16 }}>{result.message}</div>}
          <div className="split">
            <div>
              <div className="frame"><img src={result.annotatedImage} alt={`Analysed image with ${result.faces.length} detected face(s)`} /></div>
              <p className="muted small" style={{ marginTop: 8 }}>
                {result.faces.length} face{result.faces.length > 1 ? "s" : ""} detected · analysed on your device, not uploaded or stored
              </p>
              {result.faces.length > 1 && (
                <div className="row" style={{ marginTop: 10 }} role="tablist" aria-label="Detected faces">
                  {result.faces.map((f, i) => (
                    <button key={f.index} role="tab" aria-selected={i === selected}
                            className={`chip${i === selected ? " active" : ""}`} onClick={() => { setSelected(i); setMood(null); rememberFace(f, source?.kind === "frame" ? "webcam" : "image"); }}>
                      Face {f.index} · {emoji(f.emotion)} {f.emotion} {Math.round(f.confidence * 100)}%
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="stack">
              <ResultCard emotion={face.emotion} confidence={face.confidence}
                          title={`Model detected${result.faces.length > 1 ? ` · Face ${face.index}` : ""}`} />
              {face.level === "Low" && (
                <div className="alert alert-warning"><strong>Low-confidence prediction.</strong> Lighting, pose, face angle or
                  image quality can affect the result.</div>
              )}
              {face.smallFace && <div className="alert alert-info">This face is small, so the model has limited detail.</div>}
              <div className="card">
                <div className="card-title">Save check-in</div>
                <p className="muted small" style={{ marginTop: 2 }}>How do you actually feel? (optional)</p>
                <div className="row" style={{ marginTop: 8 }} role="radiogroup" aria-label="How do you actually feel? (optional)">
                  {Object.entries(MOODS).map(([m, icon]) => (
                    <button key={m} role="radio" aria-checked={mood === m} disabled={saved.has(selected)}
                            className={`chip${mood === m ? " active" : ""}`} onClick={() => setMood(mood === m ? null : m)}>{icon} {m}</button>
                  ))}
                </div>
                <div className="row" style={{ marginTop: 12 }}>
                  <button className="btn btn-primary" onClick={save} disabled={saving || saved.has(selected)}>
                    {saved.has(selected) ? "✓ Saved to history" : saving ? "Saving…" : "Save to history"}
                  </button>
                  <button className="btn" onClick={reset}>{mode === "webcam" ? "Close result" : "Try another image"}</button>
                </div>
                {saved.get(selected) === false && (
                  <div style={{ marginTop: 10 }}><SavedMessage text="✓ Saved." cloud={false} /></div>
                )}
                <p className="muted small" style={{ marginTop: 8 }}>Saving stores the expression, confidence and top-3 predictions
                  {" "}— plus your mood if you pick one — never the image.</p>
              </div>
            </div>
          </div>

          <div className="section"><h2>Emotion distribution</h2><p>The model&apos;s probability for each of the seven expressions.</p></div>
          <EmotionBars values={face.probabilities} />

          <div className="section"><h2>Top 3 predictions</h2></div>
          <RankCards top3={face.top3} />

          {face.gradcam && (
            <>
              <div className="section"><h2>Model attention (Grad-CAM)</h2><p>Where the model looked when making this prediction.</p></div>
              <div className="split">
                <div className="cam-grid">
                  <figure><img src={face.gradcam.modelInput} alt="The 48×48 grayscale face the model received" /><figcaption>Model input (48×48)</figcaption></figure>
                  <figure><img src={face.gradcam.heatmap} alt="Grad-CAM heatmap over the face" /><figcaption>Grad-CAM</figcaption></figure>
                </div>
                <div className="card">
                  <div className="card-title">Reading the heatmap</div>
                  <p className="muted small" style={{ marginTop: 6 }}>
                    Orange regions most increased the score of the predicted expression. Grad-CAM shows where the model
                    looked — it is not proof that the prediction is right, and a facial expression is not a measure of
                    how someone actually feels.
                  </p>
                </div>
              </div>
            </>
          )}
          <div className="section"><h2>What might help right now?</h2><p>{SELF_CHECK_PROMPT}</p></div>
          <div className="card" style={{ maxWidth: 760 }}>
            <div className="card-title" style={{ marginBottom: 6 }}>{suggestionsFor(face.emotion).headline}</div>
            <SuggestionList items={suggestionsFor(face.emotion).items} />
            <div className="row" style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--line)" }}>
              <Link href="/wellbeing" className="btn btn-sm">Explore the wellbeing toolkit</Link>
              <Link href="/checkin" className="btn btn-sm btn-ghost">Check in with your own words</Link>
              <Link href="/support" className="btn btn-sm btn-ghost">Find support</Link>
            </div>
          </div>
          <p className="muted small" style={{ marginTop: 8 }}>General wellbeing ideas, not medical advice. A detected expression
            doesn&apos;t tell us how you feel.</p>
          <p className="muted small" style={{ marginTop: 24 }}>Analysed in {Math.round(result.timingMs)} ms on your device.</p>
        </>
      )}
    </>
  );
}
