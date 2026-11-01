"use client";

/* eslint-disable @next/next/no-img-element -- results are data: URLs returned by the API */
import { useRef, useState, type DragEvent } from "react";
import { EmotionBars, RankCards, ResultCard } from "@/components/Emotion";
import { ACCEPTED_TYPES, MAX_UPLOAD_MB, predict, validateFile, type PredictResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { emoji } from "@/lib/emotions";
import { detectionEntry, saveEntry } from "@/lib/history";

type Status = "idle" | "loading" | "done" | "error";

export default function DetectPage() {
  const { user } = useAuth();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [gradcam, setGradcam] = useState(true);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [selected, setSelected] = useState(0);
  const [saved, setSaved] = useState<Set<number>>(new Set());
  const [saving, setSaving] = useState(false);
  const [drag, setDrag] = useState(false);

  async function analyze(f: File, wholeImage = false) {
    const problem = validateFile(f);
    setFile(f);
    setResult(null);
    setSaved(new Set());
    setSelected(0);
    if (problem) {
      setError(problem);
      setStatus("error");
      return;
    }
    setError(null);
    setStatus("loading");
    try {
      setResult(await predict(f, { gradcam, wholeImage }));
      setStatus("done");
    } catch (err) {
      setError((err as Error).message);
      setStatus("error");
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files?.[0];
    if (f) analyze(f);
  }

  function reset() {
    setFile(null);
    setResult(null);
    setStatus("idle");
    setError(null);
    if (input.current) input.current.value = "";
  }

  async function save() {
    if (!user || !result) return;
    setSaving(true);
    await saveEntry(user.uid, detectionEntry(result.faces[selected]));
    setSaved(new Set(saved).add(selected));
    setSaving(false);
  }

  const face = result?.faces[selected];

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Analyze</div>
        <h1 className="title">Detect <span className="accent">emotion</span></h1>
        <p className="subtitle">Upload a photo. The model finds each face and estimates its facial expression.</p>
      </div>

      <input ref={input} type="file" accept={ACCEPTED_TYPES.join(",")} hidden
             onChange={(e) => e.target.files?.[0] && analyze(e.target.files[0])} />

      {status === "idle" || (status === "error" && !result) ? (
        <>
          <div className={`dropzone${drag ? " drag" : ""}`} role="button" tabIndex={0}
               onClick={() => input.current?.click()} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
               onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}>
            <div className="icon" aria-hidden="true">📷</div>
            <div className="card-title">Drop an image or choose a photo</div>
            <p className="muted small" style={{ marginTop: 4 }}>
              JPG, PNG, WebP or BMP · up to {MAX_UPLOAD_MB} MB · one or several faces · analysed in memory, never stored
            </p>
            <span className="btn btn-primary" style={{ marginTop: 16 }}>Choose image</span>
          </div>
          <label className="check" style={{ marginTop: 14 }}>
            <input type="checkbox" checked={gradcam} onChange={(e) => setGradcam(e.target.checked)} />
            Include Grad-CAM model attention
          </label>
          {error && <div className="alert alert-error" role="alert" style={{ marginTop: 14 }}>{error}</div>}
        </>
      ) : null}

      {status === "loading" && (
        <div className="card row" style={{ gap: 14 }} role="status">
          <span className="spinner" style={{ color: "var(--primary)" }} />
          <div>
            <div className="card-title">Analysing {file?.name}…</div>
            <p className="muted small">Detecting faces and running the CNN. The first request can take up to a minute while the service wakes up.</p>
          </div>
        </div>
      )}

      {status === "done" && result && result.faces.length === 0 && (
        <div className="stack">
          <div className="alert alert-warning">{result.message ?? "No face detected."}</div>
          <div className="frame" style={{ maxWidth: 520 }}><img src={result.annotatedImage} alt="Uploaded image" /></div>
          <div className="row">
            <button className="btn btn-primary" onClick={() => file && analyze(file, true)}>Treat the whole image as one face</button>
            <button className="btn" onClick={reset}>Try another image</button>
          </div>
        </div>
      )}

      {status === "done" && result && face && (
        <>
          {result.message && <div className="alert alert-info" style={{ marginBottom: 16 }}>{result.message}</div>}
          <div className="split">
            <div>
              <div className="frame"><img src={result.annotatedImage} alt={`Uploaded image with ${result.faces.length} detected face(s)`} /></div>
              <p className="muted small" style={{ marginTop: 8 }}>
                {result.faces.length} face{result.faces.length > 1 ? "s" : ""} detected · analysed in memory, not stored
              </p>
              {result.faces.length > 1 && (
                <div className="row" style={{ marginTop: 10 }} role="tablist" aria-label="Detected faces">
                  {result.faces.map((f, i) => (
                    <button key={f.index} role="tab" aria-selected={i === selected}
                            className={`chip${i === selected ? " active" : ""}`} onClick={() => setSelected(i)}>
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
              <div className="row">
                <button className="btn btn-primary" onClick={save} disabled={saving || saved.has(selected)}>
                  {saved.has(selected) ? "✓ Saved to history" : saving ? "Saving…" : "Save to history"}
                </button>
                <button className="btn" onClick={reset}>Try another image</button>
              </div>
              <p className="muted small">Saving stores the expression, confidence and top-3 predictions — never the image.</p>
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
          <p className="muted small" style={{ marginTop: 24 }}>Analysed in {Math.round(result.timingMs)} ms.</p>
        </>
      )}
    </>
  );
}
