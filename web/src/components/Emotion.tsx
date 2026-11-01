// Emotion display components. Every emotion is shown with its emoji and name, never colour alone.
import type { CSSProperties, ReactNode } from "react";
import { color, confidenceLevel, describeExpression, emoji, pct } from "@/lib/emotions";

const cssVar = (c: string, extra: Record<string, string | number> = {}) => ({ "--c": c, ...extra }) as CSSProperties;

export function EmotionPill({ emotion }: { emotion: string }) {
  return <span className="pill" style={cssVar(color(emotion))}>{emoji(emotion)} {emotion}</span>;
}

export function ResultCard({ emotion, confidence, title = "Model detected", text, meta }:
  { emotion: string; confidence: number; title?: string; text?: string; meta?: ReactNode }) {
  const level = confidenceLevel(confidence);
  return (
    <div className="card result" style={cssVar(color(emotion))}>
      <div className="eyebrow">{title}</div>
      <div className="result-main">
        <div className="emoji-orb" aria-hidden="true">{emoji(emotion)}</div>
        <div>
          <div className="result-name">{emotion.toUpperCase()}</div>
          <div className="result-conf">{Math.round(confidence * 100)}% confidence <span className={`badge ${level}`}>{level} confidence</span></div>
        </div>
        <div className="ring" style={cssVar(color(emotion), { "--p": (confidence * 100).toFixed(1) })}
             role="img" aria-label={`Confidence ${Math.round(confidence * 100)}%`}>
          <span>{Math.round(confidence * 100)}%</span>
        </div>
      </div>
      <p className="muted" style={{ marginTop: 12 }}>{text ?? describeExpression(emotion)}</p>
      {meta && <p className="muted small" style={{ marginTop: 6 }}>{meta}</p>}
    </div>
  );
}

/** Horizontal bars, highest first; each row is labelled with emoji, name and value.
 *  mode "probability": values are 0–1 shown as %; mode "count": bars scale to the largest count. */
export function EmotionBars({ values, title, mode = "probability" }:
  { values: Record<string, number>; title?: string; mode?: "probability" | "count" }) {
  const items = Object.entries(values).sort((a, b) => b[1] - a[1]);
  const scale = mode === "count" ? Math.max(...items.map(([, v]) => v), 1) : 1;
  const format = mode === "count" ? (v: number) => String(v) : pct;
  return (
    <div className="card">
      {title && <div className="stat-label" style={{ marginBottom: 6 }}>{title}</div>}
      {items.map(([e, v], i) => (
        <div key={e} className={`bar-row${i === 0 && v > 0 ? " top" : ""}`} style={cssVar(color(e))}>
          <div className="bar-name"><span aria-hidden="true">{emoji(e)}</span>{e}</div>
          <div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max((v / scale) * 100, v > 0 ? 1 : 0)}%` }} /></div>
          <div className="bar-value">{format(v)}</div>
        </div>
      ))}
    </div>
  );
}

export function RankCards({ top3 }: { top3: { emotion: string; probability: number }[] }) {
  return (
    <div className="grid grid-3">
      {top3.map((p, i) => (
        <div key={p.emotion} className={`card hover rank${i === 0 ? " first" : ""}`} style={cssVar(color(p.emotion))}>
          <div className="rank-n">#{i + 1}</div>
          <div className="rank-emoji" aria-hidden="true">{emoji(p.emotion)}</div>
          <div className="rank-name">{p.emotion}</div>
          <div className="rank-pct">{pct(p.probability)}</div>
          <div className="bar-track" style={{ marginTop: 8 }}><div className="bar-fill" style={{ width: `${Math.max(p.probability * 100, 1)}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

export function StatCard({ label, value, hint, icon, emotion }:
  { label: string; value: string; hint?: string; icon: string; emotion?: string | null }) {
  return (
    <div className="card hover">
      <div className="stat">
        <div className="stat-icon" style={cssVar(emotion ? color(emotion) : "#4f46e5")} aria-hidden="true">
          {emotion ? emoji(emotion) : icon}
        </div>
        <div style={{ minWidth: 0 }}>
          <div className="stat-label">{label}</div>
          <div className="stat-value">{value}</div>
          <div className="stat-hint">{hint || " "}</div>
        </div>
      </div>
    </div>
  );
}

export function EmptyState({ icon, title, text, children }:
  { icon: string; title: string; text: string; children?: ReactNode }) {
  return (
    <div className="card empty">
      <div className="icon" aria-hidden="true">{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
      {children && <div className="row" style={{ justifyContent: "center", marginTop: 16 }}>{children}</div>}
    </div>
  );
}
