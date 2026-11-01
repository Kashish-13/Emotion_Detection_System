"use client";

import Link from "next/link";
import { useState } from "react";
import { EmotionPill, EmptyState } from "@/components/Emotion";
import { deleteEntry, type HistoryEntry } from "@/lib/history";
import { formatTime } from "@/lib/stats";
import { useHistory } from "@/lib/useHistory";

const KIND_LABEL: Record<HistoryEntry["kind"], string> = {
  detection: "Detection", checkin: "Check-in", journal: "Journal", reset: "Wellbeing activity",
};

function details(e: HistoryEntry): string {
  if (e.kind === "detection") return (e.topPredictions ?? []).slice(1).map((p) => `${p.emotion} ${Math.round(p.probability * 100)}%`).join(", ");
  if (e.kind === "checkin") return [e.selfReportedMood, ...(e.moodFactors ?? [])].filter(Boolean).join(" · ");
  if (e.kind === "journal") return e.prompt ?? "";
  return [e.activity, e.feelingAfter].filter(Boolean).join(" → ");
}

export default function HistoryPage() {
  const { entries, reload, uid } = useHistory();
  const [filter, setFilter] = useState<"detection" | "all">("detection");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function remove(id: string) {
    if (!uid || !window.confirm("Delete this entry? This can't be undone.")) return;
    setBusy(id);
    const ok = await deleteEntry(uid, id);
    setNotice(ok ? null : "This entry couldn't be deleted right now. Please try again in a minute.");
    await reload();
    setBusy(null);
  }

  const shown = (entries ?? []).filter((e) => filter === "all" || e.kind === "detection");

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">History</div>
        <h1 className="title">Your <span className="accent">history</span></h1>
        <p className="subtitle">Predictions you saved, shared with the EmotionSense Streamlit app. Images are never stored.</p>
      </div>

      <div className="row" style={{ marginBottom: 14 }} role="tablist" aria-label="Filter history">
        <button role="tab" aria-selected={filter === "detection"} className={`chip${filter === "detection" ? " active" : ""}`}
                onClick={() => setFilter("detection")}>Predictions</button>
        <button role="tab" aria-selected={filter === "all"} className={`chip${filter === "all" ? " active" : ""}`}
                onClick={() => setFilter("all")}>All entries</button>
      </div>
      {notice && <div className="alert alert-warning" style={{ marginBottom: 14 }}>{notice}</div>}

      {!entries ? (
        <div className="center"><span className="spinner muted" aria-label="Loading your history" /></div>
      ) : shown.length === 0 ? (
        <EmptyState icon="🌱" title="No saved predictions yet." text="Analyse a photo and press “Save to history” to see it here.">
          <Link href="/detect" className="btn btn-primary">Detect emotion</Link>
        </EmptyState>
      ) : (
        <div className="card table-wrap" style={{ padding: "6px 10px" }}>
          <table className="table">
            <thead><tr><th>When</th><th>Type</th><th>Expression</th><th>Confidence</th><th>Details</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>
              {shown.map((e) => (
                <tr key={e.id}>
                  <td className="muted" style={{ whiteSpace: "nowrap" }}>{formatTime(e.timestamp)}</td>
                  <td>{KIND_LABEL[e.kind] ?? e.kind}</td>
                  <td>{e.detectedEmotion ? <EmotionPill emotion={e.detectedEmotion} /> : <span className="muted">—</span>}</td>
                  <td>{e.confidence != null ? `${Math.round(e.confidence * 100)}%` : <span className="muted">—</span>}</td>
                  <td className="muted small">{details(e) || "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-sm btn-ghost btn-danger" onClick={() => remove(e.id)} disabled={busy === e.id}
                            aria-label={`Delete entry from ${formatTime(e.timestamp)}`}>
                      {busy === e.id ? "Deleting…" : "Delete"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
