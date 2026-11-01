"use client";

// Wellbeing pieces shared by the dashboard, detect, check-in and wellbeing pages (src/ui/components.py).
// Everything here is user-initiated; nothing is ever triggered by the model.
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import { newEntry, saveEntry } from "@/lib/history";
import {
  ACTIVITIES, DISTRESS_NOTE, FEELING_ICONS, FEELINGS_AFTER, JOURNAL_PROMPTS, type Suggestion,
} from "@/lib/wellbeing";

export const activityHref = (id: string) => `/wellbeing?activity=${encodeURIComponent(id)}`;

export function DistressNote() {
  return <div className="alert alert-info">💜 {DISTRESS_NOTE}</div>;
}

/** Confirmation after saving, honest about where the entry went. */
export function SavedMessage({ text, cloud }: { text: string; cloud: boolean }) {
  return (
    <div className="alert alert-success" role="status">
      {text}{!cloud && " Cloud history is unavailable right now, so it is kept in this browser."}
    </div>
  );
}

/** Suggestion rows; those linked to an activity get a "Try it" link to the wellbeing page. */
export function SuggestionList({ items, compact = false }: { items: Suggestion[]; compact?: boolean }) {
  return (
    <div className="suggestions">
      {items.map(([text, id]) => (
        <div key={text} className={`suggestion${compact ? " compact" : ""}`}>
          <div>
            <div style={{ fontWeight: 600 }}>{text}</div>
            {id && <div className="muted small">{ACTIVITIES[id].minutes} min · {ACTIVITIES[id].title}</div>}
          </div>
          {id && <Link href={activityHref(id)} className="btn btn-sm">▶ Try it</Link>}
        </div>
      ))}
    </div>
  );
}

/** Save state for one button: idle → saving → saved (cloud or browser). */
function useSaver() {
  const { user } = useAuth();
  const [state, setState] = useState<"idle" | "saving" | { cloud: boolean }>("idle");
  async function save(entry: Parameters<typeof saveEntry>[1]) {
    if (!user) return;
    setState("saving");
    setState({ cloud: await saveEntry(user.uid, entry) });
  }
  return { state, save, reset: () => setState("idle") };
}

// ---------------------------------------------------------------------------------------------------------------
// Timers
// ---------------------------------------------------------------------------------------------------------------
/** Seconds elapsed since start (null when stopped); stops by itself after `total` seconds. */
function useElapsed(total: number) {
  const [start, setStart] = useState<number | null>(null);
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (start == null) return;
    const t = setInterval(() => {
      const n = Date.now();
      setNow(n);
      if ((n - start) / 1000 >= total) setStart(null);
    }, 250);
    return () => clearInterval(t);
  }, [start, total]);
  return {
    elapsed: start == null ? null : Math.min(Math.max((now - start) / 1000, 0), total),
    start: () => { setNow(Date.now()); setStart(Date.now()); },
    stop: () => setStart(null),
  };
}

function TimerBar({ seconds, label }: { seconds: number; label: string }) {
  const { elapsed, start, stop } = useElapsed(seconds);
  const [finished, setFinished] = useState(false);
  const prev = useRef<number | null>(null);
  useEffect(() => {
    if (prev.current != null && elapsed == null && prev.current >= seconds - 0.5) setFinished(true);
    prev.current = elapsed;
  }, [elapsed, seconds]);
  const left = elapsed == null ? seconds : Math.max(0, Math.ceil(seconds - elapsed));
  return (
    <div style={{ marginTop: 12 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span className="muted small">{label}</span>
        <span className="small" style={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
          {Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")}
        </span>
      </div>
      <div className="bar-track" style={{ height: 10, marginTop: 6 }} role="progressbar" aria-label={label}
           aria-valuemin={0} aria-valuemax={seconds} aria-valuenow={Math.round(elapsed ?? 0)}>
        <div className="bar-fill" style={{ "--c": "var(--primary)", width: `${((elapsed ?? (finished ? seconds : 0)) / seconds) * 100}%` } as React.CSSProperties} />
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        {elapsed == null
          ? <button className="btn btn-sm btn-primary" onClick={() => { setFinished(false); start(); }}>{finished ? "Start again" : "Start timer"}</button>
          : <button className="btn btn-sm" onClick={stop}>Stop</button>}
        {finished && elapsed == null && <span className="muted small">Time&apos;s up — nicely done.</span>}
      </div>
    </div>
  );
}

const CYCLE = [{ phase: "Inhale", s: 4 }, { phase: "Hold", s: 4 }, { phase: "Exhale", s: 6 }]; // 14 s

function Breathing({ steps }: { steps: string[] }) {
  const { elapsed, start, stop } = useElapsed(60);
  let phase = "Ready", left = 0, scale = 0.7, duration = 0.6;
  if (elapsed != null) {
    let t = elapsed % 14;
    for (const c of CYCLE) {
      if (t < c.s) {
        phase = c.phase;
        left = Math.ceil(c.s - t);
        scale = c.phase === "Exhale" ? 0.7 : 1;
        duration = c.phase === "Hold" ? 0.2 : c.s;
        break;
      }
      t -= c.s;
    }
  }
  return (
    <div className="split" style={{ alignItems: "center" }}>
      <div className="orb-wrap">
        <div className="orb-box" aria-hidden="true">
          <div className="orb" style={{ transform: `scale(${scale})`, transitionDuration: `${duration}s` }} />
        </div>
        <div className="orb-label" aria-live="polite">
          <div style={{ fontWeight: 700, letterSpacing: ".08em", textTransform: "uppercase" }}>{phase}</div>
          {elapsed != null && <div className="muted small">{left}…</div>}
        </div>
      </div>
      <div>
        {steps.map((s, i) => <p key={s} style={{ marginBottom: 6 }}><strong>Step {i + 1}</strong> — {s}</p>)}
        <div className="row" style={{ marginTop: 12 }}>
          {elapsed == null
            ? <button className="btn btn-sm btn-primary" onClick={start}>Start one minute</button>
            : <button className="btn btn-sm" onClick={stop}>Stop</button>}
          {elapsed != null && <span className="muted small">{Math.max(0, Math.ceil(60 - elapsed))} s left</span>}
        </div>
      </div>
    </div>
  );
}

function Grounding({ steps }: { steps: string[] }) {
  const [step, setStep] = useState(0);
  return (
    <div>
      <div className="muted small">Step {step + 1} of {steps.length}</div>
      <div className="bar-track" style={{ marginTop: 6 }}>
        <div className="bar-fill" style={{ "--c": "var(--primary)", width: `${((step + 1) / steps.length) * 100}%` } as React.CSSProperties} />
      </div>
      <h3 style={{ margin: "16px 0 4px", fontSize: "1.25rem" }}>{steps[step]}</h3>
      <p className="muted small">Take your time. Name them silently or out loud.</p>
      <div className="row" style={{ marginTop: 14 }}>
        <button className="btn" disabled={step === 0} onClick={() => setStep(step - 1)}>Back</button>
        <button className="btn btn-primary" onClick={() => setStep((step + 1) % steps.length)}>
          {step < steps.length - 1 ? "Next" : "Start again"}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------
// Journaling
// ---------------------------------------------------------------------------------------------------------------
function JournalSave({ prompt, text }: { prompt: string; text: string }) {
  const { state, save, reset } = useSaver();
  const [warn, setWarn] = useState(false);
  useEffect(() => { reset(); setWarn(false); }, [prompt, text]); // eslint-disable-line react-hooks/exhaustive-deps
  async function click() {
    if (!text.trim()) return setWarn(true);
    await save(newEntry("journal", { prompt, journalText: text.trim() }));
  }
  return (
    <div className="stack" style={{ marginTop: 10 }}>
      <div><button className="btn btn-primary btn-sm" onClick={click} disabled={state === "saving"}>
        {state === "saving" ? "Saving…" : "Save to my journal"}
      </button></div>
      {warn && <div className="alert alert-warning">Write something first, then save.</div>}
      {typeof state === "object" && <SavedMessage text="✓ Journal saved." cloud={state.cloud} />}
    </div>
  );
}

function Writing() {
  const [prompt, setPrompt] = useState(JOURNAL_PROMPTS[0]);
  const [text, setText] = useState("");
  return (
    <div>
      <label className="field"><span>Prompt</span>
        <select className="input" value={prompt} onChange={(e) => setPrompt(e.target.value)}>
          {JOURNAL_PROMPTS.map((p) => <option key={p}>{p}</option>)}
        </select>
      </label>
      <label className="field" style={{ marginBottom: 0 }}><span>Write freely</span>
        <textarea className="input" rows={6} value={text} placeholder="Start typing…" onChange={(e) => setText(e.target.value)} />
      </label>
      <JournalSave prompt={prompt} text={text} />
    </div>
  );
}

function Gratitude() {
  const [items, setItems] = useState(["", "", ""]);
  const text = items.filter((t) => t.trim()).map((t) => `• ${t.trim()}`).join("\n");
  return (
    <div>
      {items.map((v, i) => (
        <label key={i} className="field"><span>{i + 1}.</span>
          <input className="input" value={v} placeholder="Something I appreciate…"
                 onChange={(e) => setItems(items.map((x, j) => (j === i ? e.target.value : x)))} />
        </label>
      ))}
      <JournalSave prompt="Three things I'm grateful for" text={text} />
    </div>
  );
}

/** "How do you feel after this?" — a self-reflection saved as a "reset" entry. */
function FeelingAfter({ activity }: { activity: string }) {
  const [choice, setChoice] = useState<string | null>(null);
  const { state, save, reset } = useSaver();
  return (
    <div>
      <div className="card-title">How do you feel after this?</div>
      <div className="row" style={{ marginTop: 10 }} role="radiogroup" aria-label="How do you feel after this?">
        {FEELINGS_AFTER.map((f) => (
          <button key={f} role="radio" aria-checked={choice === f} className={`chip${choice === f ? " active" : ""}`}
                  onClick={() => { setChoice(f); reset(); }}>{FEELING_ICONS[f]} {f}</button>
        ))}
      </div>
      {choice && typeof state !== "object" && (
        <button className="btn btn-sm btn-primary" style={{ marginTop: 12 }} disabled={state === "saving"}
                onClick={() => save(newEntry("reset", { activity, feelingAfter: choice }))}>
          {state === "saving" ? "Saving…" : "Save reflection"}
        </button>
      )}
      {typeof state === "object" && <div style={{ marginTop: 12 }}><SavedMessage text="✓ Reflection saved." cloud={state.cloud} /></div>}
      {choice === "Still difficult" && <div style={{ marginTop: 12 }}><DistressNote /></div>}
      <p className="muted small" style={{ marginTop: 10 }}>This is a self-reflection, not a test or an assessment.</p>
    </div>
  );
}

/** Interactive panel for one wellbeing activity, followed by a "how do you feel" reflection. */
export function ActivityPanel({ id, onClose }: { id: string; onClose: () => void }) {
  const act = ACTIVITIES[id];
  return (
    <section className="card activity" aria-label={act.title}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 style={{ fontSize: "1.3rem" }}>{act.emoji} {act.title}</h2>
          <p className="muted small">{act.summary} · about {act.minutes} min</p>
        </div>
        <button className="btn btn-sm" onClick={onClose}>✕ Close</button>
      </div>
      <div style={{ marginTop: 18 }}>
        {act.kind === "breathing" && <Breathing steps={act.steps} />}
        {act.kind === "grounding" && <Grounding steps={act.steps} />}
        {act.kind === "timer" && (
          <>
            <ol style={{ margin: 0, paddingLeft: 20 }}>{act.steps.map((s) => <li key={s} style={{ marginBottom: 4 }}>{s}</li>)}</ol>
            <TimerBar seconds={act.seconds!} label={`${act.seconds! / 60} minute timer`} />
          </>
        )}
        {act.kind === "writing" && <Writing />}
        {act.kind === "gratitude" && <Gratitude />}
      </div>
      <hr className="divider" />
      <FeelingAfter key={id} activity={id} />
    </section>
  );
}
