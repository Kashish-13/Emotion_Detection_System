"use client";

import Link from "next/link";
import { EmotionBars, EmotionPill, EmptyState, ResultCard, StatCard } from "@/components/Emotion";
import { displayName, useAuth } from "@/lib/auth";
import { computeStats, detections, formatTime } from "@/lib/stats";
import { useHistory } from "@/lib/useHistory";

export default function DashboardPage() {
  const { user } = useAuth();
  const { entries } = useHistory();

  if (!entries) {
    return <div className="center"><span className="spinner muted" aria-label="Loading your history" /></div>;
  }
  const stats = computeStats(entries);
  const recent = detections(entries).slice(0, 5);
  const latest = recent[0];

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Dashboard</div>
        <h1 className="title">Good to see you, {displayName(user)} 👋</h1>
        <p className="subtitle">Your saved expression predictions at a glance.</p>
      </div>

      <div className="grid grid-4">
        <StatCard label="Predictions saved" value={String(stats.predictions)} hint={`${stats.thisWeek} in the last 7 days`} icon="🗂️" />
        <StatCard label="Most detected" value={stats.mostDetected ?? "—"} hint="Across saved predictions" icon="🧭" emotion={stats.mostDetected} />
        <StatCard label="Average confidence" value={stats.averageConfidence == null ? "—" : `${Math.round(stats.averageConfidence * 100)}%`}
                  hint="Of saved predictions" icon="🎯" />
        <StatCard label="Last prediction" value={latest ? latest.detectedEmotion! : "—"}
                  hint={latest ? formatTime(latest.timestamp) : "Nothing saved yet"} icon="🕒" emotion={latest?.detectedEmotion} />
      </div>

      {stats.predictions === 0 ? (
        <div style={{ marginTop: 24 }}>
          <EmptyState icon="🌱" title="Your story starts here." text="Analyse a photo and save the result to see your patterns.">
            <Link href="/detect" className="btn btn-primary">Detect emotion</Link>
          </EmptyState>
        </div>
      ) : (
        <div className="split" style={{ marginTop: 24 }}>
          <div className="stack">
            {latest && (
              <ResultCard emotion={latest.detectedEmotion!} confidence={latest.confidence ?? 0} title="Latest saved prediction"
                          meta={`${formatTime(latest.timestamp)}${latest.source ? ` · ${latest.source}` : ""}`} />
            )}
            <div className="row">
              <Link href="/detect" className="btn btn-primary">Analyse a new photo</Link>
              <Link href="/history" className="btn">View full history</Link>
            </div>
          </div>
          <EmotionBars values={stats.counts} title="Detected expressions (saved predictions)" mode="count" />
        </div>
      )}

      {recent.length > 0 && (
        <>
          <div className="section"><h2>Recent predictions</h2><p>Your latest saved results, from this site or the Streamlit app.</p></div>
          <div className="card table-wrap" style={{ padding: "6px 10px" }}>
            <table className="table">
              <thead><tr><th>Expression</th><th>Confidence</th><th>When</th><th>Source</th></tr></thead>
              <tbody>
                {recent.map((e) => (
                  <tr key={e.id}>
                    <td><EmotionPill emotion={e.detectedEmotion!} /></td>
                    <td>{e.confidence != null ? `${Math.round(e.confidence * 100)}%` : "—"}</td>
                    <td className="muted">{formatTime(e.timestamp)}</td>
                    <td className="muted">{e.source ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <p className="muted small" style={{ marginTop: 28 }}>
        EmotionSense reads facial expressions, which are not a reliable measure of what someone actually feels.
        It is not a medical or diagnostic tool.
      </p>
    </>
  );
}
