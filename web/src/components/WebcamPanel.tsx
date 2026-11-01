"use client";

// Live webcam analysis with the same in-browser inference module as image upload.
// Frames are processed on the device and never recorded or uploaded.
import { useCallback, useEffect, useRef, useState } from "react";
import { EmotionBars, ResultCard, StatCard } from "@/components/Emotion";
import { CountBars } from "@/components/Charts";
import { summarizeSession } from "@/lib/analytics";
import { color, emoji } from "@/lib/emotions";
import { logPredictions, rememberFace, resetSessionPredictions, useSession } from "@/lib/session";
import {
  analyzeFrame, drawFaces, primaryFace, WEBCAM_DETECTION_DOWNSCALE, type FaceAnalysis,
} from "@/lib/emotion";

const PREDICT_EVERY_MS = 150; // ≈ 6–7 predictions per second at most; never overlapping
const LOG_INTERVAL_MS = 1000; // add at most one entry per face per second to the session summary (WEBCAM_LOG_INTERVAL_S)

type Live = { faces: FaceAnalysis[]; fps: number; predictionsPerSecond: number; main: FaceAnalysis | null };

function cameraError(err: unknown): string {
  const name = (err as { name?: string })?.name;
  if (name === "NotAllowedError" || name === "SecurityError") return "Camera access was blocked. Allow camera access for this site in your browser settings and try again.";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "No camera was found on this device.";
  if (name === "NotReadableError") return "The camera is being used by another app. Close it and try again.";
  return "The camera could not be started.";
}

export default function WebcamPanel({ ready, onSnapshot }: { ready: boolean; onSnapshot: (frame: ImageData) => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const view = useRef<HTMLCanvasElement>(null);                // what the user sees: frame + boxes
  const work = useRef<HTMLCanvasElement | null>(null);         // clean mirrored frame used for analysis
  const stream = useRef<MediaStream | null>(null);
  const raf = useRef(0);
  const busy = useRef(false);
  const lastRun = useRef(0);
  const lastFrame = useRef(0);
  const faces = useRef<FaceAnalysis[]>([]);
  const fps = useRef(0);
  const pps = useRef(0);
  const lastLog = useRef(0);
  const [running, setRunning] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState<Live | null>(null);

  const stop = useCallback(() => {
    cancelAnimationFrame(raf.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    if (video.current) video.current.srcObject = null;
    faces.current = [];
    setRunning(false);
  }, []);

  const loop = useCallback((now: number) => {
    const v = video.current;
    const canvas = view.current;
    if (!v || !canvas || !stream.current) return;
    if (v.readyState >= 2 && v.videoWidth) {
      const w = v.videoWidth;
      const h = v.videoHeight;
      const workCanvas = (work.current ??= document.createElement("canvas"));
      for (const c of [workCanvas, canvas]) {
        if (c.width !== w) c.width = w;
        if (c.height !== h) c.height = h;
      }
      const wctx = workCanvas.getContext("2d", { willReadFrequently: true })!;
      wctx.setTransform(-1, 0, 0, 1, w, 0); // mirror, like the Streamlit webcam (cv2.flip)
      wctx.drawImage(v, 0, 0, w, h);
      wctx.setTransform(1, 0, 0, 1, 0, 0);
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(workCanvas, 0, 0);
      drawFaces(ctx, faces.current);

      if (lastFrame.current) fps.current = 0.9 * fps.current + 0.1 * (1000 / Math.max(now - lastFrame.current, 1));
      lastFrame.current = now;

      if (!busy.current && now - lastRun.current >= PREDICT_EVERY_MS) {
        busy.current = true;
        const started = now;
        if (lastRun.current) pps.current = 0.8 * pps.current + 0.2 * (1000 / (now - lastRun.current));
        lastRun.current = now;
        analyzeFrame(wctx.getImageData(0, 0, w, h), { detectionDownscale: WEBCAM_DETECTION_DOWNSCALE })
          .then((a) => {
            if (!stream.current) return;
            faces.current = a.faces;
            const main = primaryFace(a.faces) ?? null;
            setLive({ faces: a.faces, fps: fps.current, predictionsPerSecond: pps.current, main });
            if (main && Date.now() - lastLog.current >= LOG_INTERVAL_MS) {
              lastLog.current = Date.now();
              logPredictions(a.faces, "webcam");
              rememberFace(main, "webcam");
            }
          })
          .catch((err) => console.error("Live analysis failed", err, performance.now() - started))
          .finally(() => { busy.current = false; });
      }
    }
    raf.current = requestAnimationFrame(loop);
  }, []);

  async function start() {
    setError(null);
    setStarting(true);
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw Object.assign(new Error("unsupported"), { name: "NotFoundError" });
      const s = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }, audio: false });
      stream.current = s;
      video.current!.srcObject = s;
      await video.current!.play();
      lastRun.current = 0;
      lastFrame.current = 0;
      setRunning(true);
      raf.current = requestAnimationFrame(loop);
    } catch (err) {
      stop();
      setError(cameraError(err));
    } finally {
      setStarting(false);
    }
  }

  function snapshot() {
    const c = work.current;
    if (!c || !c.width) return;
    onSnapshot(c.getContext("2d", { willReadFrequently: true })!.getImageData(0, 0, c.width, c.height));
  }

  useEffect(() => {
    const onHidden = () => { if (document.hidden) stop(); };
    document.addEventListener("visibilitychange", onHidden);
    return () => {
      document.removeEventListener("visibilitychange", onHidden);
      stop(); // leaving the page always releases the camera
    };
  }, [stop]);

  const main = live?.main ?? null;
  return (
    <>
    <div className="split">
      <div className="stack">
        <div className="video-frame">
          <video ref={video} playsInline muted hidden />
          <canvas ref={view} hidden={!running} aria-label="Live camera view with detected faces" />
          {!running && (
            <div className="video-off">
              <div style={{ fontSize: "2rem" }} aria-hidden="true">📷</div>
              <div className="card-title" style={{ marginTop: 6 }}>Camera is off</div>
              <p className="muted small" style={{ marginTop: 4, maxWidth: 340 }}>
                Frames are analysed on your device and never recorded or uploaded.
              </p>
            </div>
          )}
        </div>
        <div className="row">
          {running ? (
            <>
              <button className="btn" onClick={stop}>Stop camera</button>
              <button className="btn btn-primary" onClick={snapshot}>Analyze this frame</button>
            </>
          ) : (
            <button className="btn btn-primary" onClick={start} disabled={!ready || starting}>
              {starting ? "Starting…" : "Start camera"}
            </button>
          )}
          {running && <span className="live-badge"><i aria-hidden="true" />LIVE</span>}
        </div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <p className="muted small">
          Predictions run about {Math.round(1000 / PREDICT_EVERY_MS)} times a second at most. “Analyze this frame”
          adds Grad-CAM and lets you save the result.
        </p>
      </div>
      <div className="stack" aria-live="polite">
        <div className="grid grid-2">
          <div className="card"><div className="stat-label">Faces in view</div><div className="stat-value">{running && live ? live.faces.length : "—"}</div></div>
          <div className="card"><div className="stat-label">Predictions / second</div>
            <div className="stat-value">{running && live ? live.predictionsPerSecond.toFixed(1) : "—"}</div>
            <div className="stat-hint">{running && live ? `${live.fps.toFixed(0)} frames / second` : " "}</div></div>
        </div>
        {running && main ? (
          <>
            <ResultCard emotion={main.emotion} confidence={main.confidence}
                        title={live && live.faces.length > 1 ? "Current expression · largest face" : "Current expression"} />
            {main.level === "Low" && <p className="muted small">ⓘ Low confidence — lighting, pose or angle may be affecting the result.</p>}
            <EmotionBars values={main.probabilities} title="Emotion distribution" />
            {live && live.faces.length > 1 && (
              <div className="row">
                {live.faces.map((f, i) => (
                  <span key={i} className="chip">Face {i + 1} · {emoji(f.emotion)} {f.emotion} {Math.round(f.confidence * 100)}%</span>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="card empty">
            <div className="icon" aria-hidden="true">🎯</div>
            <h3>{running ? "No face detected" : "Waiting for a face"}</h3>
            <p>{running ? "Try adjusting your position or lighting." : "Live results appear here once the camera is running."}</p>
          </div>
        )}
      </div>
    </div>
    <SessionSummary />
    </>
  );
}

/** Live predictions from this browser session (not saved), like the Streamlit webcam page's "This session". */
function SessionSummary() {
  const session = useSession();
  const summary = summarizeSession(session.predictions);
  return (
    <>
      <div className="section"><h2>This session</h2><p>Live predictions from this browser session (not saved). They describe
        detected expressions, not how anyone feels.</p></div>
      {!summary.predictions ? <p className="muted small">No live predictions yet.</p> : (
        <>
          <div className="grid grid-4">
            <StatCard label="Predictions logged" value={String(summary.predictions)} hint="At most one per second live" icon="🧾" />
            <StatCard label="Faces detected" value={String(session.facesDetected)} icon="👥" />
            <StatCard label="Most frequent" value={summary.dominant ?? "—"} icon="🧭" emotion={summary.dominant} />
            <StatCard label="Average confidence" value={`${Math.round((summary.averageConfidence ?? 0) * 100)}%`} icon="🎯" />
          </div>
          <div style={{ marginTop: 14 }}>
            <CountBars title="Predictions by expression" items={Object.entries(summary.counts).map(([e, n]) => ({
              key: e, label: <><span aria-hidden="true">{emoji(e)}</span>{e}</>, color: color(e), value: n,
            }))} />
          </div>
          <button className="btn btn-sm" style={{ marginTop: 12 }} onClick={resetSessionPredictions}>↺ Reset session</button>
        </>
      )}
    </>
  );
}
