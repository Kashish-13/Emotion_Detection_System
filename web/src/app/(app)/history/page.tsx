"use client";

// History & Insights (src/ui/views/history.py): the user's own saved data, model signal and self-report kept apart.
import Link from "next/link";
import { useState } from "react";
import { CountBars, DayColumns, TimeChart } from "@/components/Charts";
import { EmotionPill, EmptyState, StatCard } from "@/components/Emotion";
import { MOOD_COLORS, Timeline } from "@/components/Timeline";
import {
  detections, filterBetween, filterSince, formatTime, generateInsights, historyStats, localDay, moodReports, mostCommonMood,
  sourceLabel, topFactors,
} from "@/lib/analytics";
import { EMOTIONS, HIGH_CONFIDENCE, MODERATE_CONFIDENCE } from "@/lib/emotion/core";
import { color, emoji } from "@/lib/emotions";
import { clearHistory, deleteEntry, type HistoryEntry } from "@/lib/history";
import { useHistory } from "@/lib/useHistory";
import { ACTIVITIES, MOOD_SCORE, MOODS, SCALES } from "@/lib/wellbeing";

const CUSTOM = "Custom range";
const RANGES: Record<string, number | null> = { "7 days": 7, "30 days": 30, "All time": null, [CUSTOM]: null };
const FILTERS = [["all", "All entries"], ["detection", "Predictions"], ["checkin", "Check-ins"], ["journal", "Journal"],
  ["reset", "Activities"]] as const;
const INSIGHT_ICON = { "Model signal": "🧭", "Self-reported mood": "💬", Tip: "💡" };
const pct = (x: number) => `${Math.round(x * 100)}%`;

function details(e: HistoryEntry): string {
  if (e.kind === "detection") return (e.topPredictions ?? []).slice(1).map((p) => `${p.emotion} ${pct(p.probability)}`).join(", ");
  if (e.kind === "checkin") {
    const ratings = SCALES.filter((s) => e[s.key] != null).map((s) => `${s.label} ${e[s.key]}/5`).join(" · ");
    return [ratings, (e.moodFactors ?? []).join(", ")].filter(Boolean).join(" — ");
  }
  if (e.kind === "journal") return e.prompt ?? "";
  return `${ACTIVITIES[e.activity ?? ""]?.title ?? "Activity"} → ${e.feelingAfter ?? ""}`;
}

function ModelSignal({ det, dominant, average, counts }:
  { det: HistoryEntry[]; dominant: string | null; average: number | null; counts: Record<string, number> }) {
  const idx = (e: string) => EMOTIONS.length - 1 - EMOTIONS.indexOf(e as (typeof EMOTIONS)[number]);
  const tip = (e: HistoryEntry) => <><strong>{formatTime(e.timestamp)}</strong><br />{emoji(e.detectedEmotion!)} {e.detectedEmotion} · {pct(e.confidence ?? 0)}</>;
  return (
    <>
      <div className="grid grid-2">
        <StatCard label="Top expression" value={dominant ?? "—"} hint="Model signal" icon="🧭" emotion={dominant} />
        <StatCard label="Average confidence" value={average == null ? "—" : pct(average)} hint={`${det.length} saved detections`} icon="🎯" />
      </div>
      <CountBars title="Expression distribution"
                 items={EMOTIONS.map((e) => ({ key: e, label: <><span aria-hidden="true">{emoji(e)}</span>{e}</>, color: color(e), value: counts[e] }))} />
      <TimeChart title="Expression timeline" labelWidth={92} height={240}
                 points={det.map((e) => ({ t: Date.parse(e.timestamp), y: idx(e.detectedEmotion!), color: color(e.detectedEmotion!), tip: tip(e) }))}
                 yMin={-0.5} yMax={EMOTIONS.length - 0.5} yTicks={EMOTIONS.map((e) => ({ v: idx(e), label: `${emoji(e)} ${e}` }))} />
      <TimeChart title="Confidence trend" line
                 caption={`Dashed lines: the app's confidence bands (${pct(MODERATE_CONFIDENCE)} and ${pct(HIGH_CONFIDENCE)}).`}
                 points={det.map((e) => ({ t: Date.parse(e.timestamp), y: e.confidence ?? 0, color: "var(--primary)", tip: tip(e) }))}
                 yMin={0} yMax={1} yTicks={[0, 0.25, 0.5, 0.75, 1].map((v) => ({ v, label: pct(v) }))}
                 refs={[{ v: MODERATE_CONFIDENCE, label: "Low / moderate" }, { v: HIGH_CONFIDENCE, label: "Moderate / high" }]} />
    </>
  );
}

function MoodSignal({ moods }: { moods: HistoryEntry[] }) {
  const counts = Object.fromEntries(Object.keys(MOODS).map((m) => [m, 0]));
  for (const e of moods) counts[e.selfReportedMood!] += 1;
  return (
    <>
      <div className="stat-label">Recent check-ins</div>
      <Timeline entries={moods.slice(0, 6)} factors />
      <CountBars title="Mood distribution" items={Object.keys(MOODS).map((m) => ({
        key: m, label: <><span aria-hidden="true">{MOODS[m]}</span>{m}</>, color: MOOD_COLORS[m], value: counts[m],
      }))} />
      <TimeChart title="Mood over time" line labelWidth={70}
                 points={moods.map((e) => ({ t: Date.parse(e.timestamp), y: MOOD_SCORE[e.selfReportedMood!], color: "#6366f1",
                   tip: <><strong>{formatTime(e.timestamp)}</strong><br />{MOODS[e.selfReportedMood!]} {e.selfReportedMood}</> }))}
                 yMin={1} yMax={5} color="#6366f1"
                 yTicks={Object.entries(MOOD_SCORE).map(([m, v]) => ({ v, label: m }))} />
    </>
  );
}

export default function HistoryPage() {
  const { entries: all, reload, uid } = useHistory();
  const [span, setSpan] = useState("30 days");
  const [filter, setFilter] = useState<(typeof FILTERS)[number][0]>("all");
  const [emotion, setEmotion] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [sure, setSure] = useState(false);

  async function remove(id: string) {
    if (!uid || !window.confirm("Delete this entry? This can't be undone.")) return;
    setBusy(id);
    const ok = await deleteEntry(uid, id);
    setNotice(ok ? null : "This entry couldn't be deleted right now. Please try again in a minute.");
    await reload();
    setBusy(null);
  }

  async function removeAll() {
    if (!uid) return;
    setBusy("all");
    const ok = await clearHistory(uid);
    setNotice(ok ? "All history deleted." : "Some entries couldn't be deleted right now. Please try again in a minute.");
    setSure(false);
    await reload();
    setBusy(null);
  }

  const head = (
    <div className="page-head">
      <div className="eyebrow">Reflect · History</div>
      <h1 className="title">History &amp; <span className="accent">insights</span></h1>
      <p className="subtitle">Patterns in your own saved check-ins and predictions, shared with the EmotionSense Streamlit app.
        Images are never stored.</p>
    </div>
  );
  if (!all) return <>{head}<div className="center"><span className="spinner muted" aria-label="Loading your history" /></div></>;
  if (!all.length) {
    return (
      <>
        {head}
        {notice && <div className="alert alert-success" style={{ marginBottom: 14 }}>{notice}</div>}
        <EmptyState icon="🌱" title="No saved check-ins yet." text="Your story starts here — complete your first check-in to see your personal patterns.">
          <Link href="/checkin" className="btn btn-primary">Daily check-in</Link>
          <Link href="/detect" className="btn">Detect emotion</Link>
        </EmptyState>
      </>
    );
  }

  const entries = span === CUSTOM ? filterBetween(all, from, to) : filterSince(all, RANGES[span]);
  const stats = historyStats(entries);
  const det = detections(entries);
  const moods = moodReports(entries);
  const mood = mostCommonMood(entries)?.[0];
  const insights = generateInsights(entries);
  const perDay = new Map<string, number>();
  for (const e of [...entries].reverse()) perDay.set(localDay(e.timestamp), (perDay.get(localDay(e.timestamp)) ?? 0) + 1);
  const matching = entries.filter((e) => (filter === "all" || e.kind === filter) && (!emotion || e.detectedEmotion === emotion));
  const shown = matching.slice(0, 200);
  const rangeHint = span === CUSTOM ? (from || to ? "In the selected dates" : "All time") : RANGES[span] ? `In the last ${span}` : "All time";

  return (
    <>
      {head}
      <div className="row" style={{ marginBottom: 16 }} role="tablist" aria-label="Time range">
        {Object.keys(RANGES).map((r) => (
          <button key={r} role="tab" aria-selected={span === r} className={`chip${span === r ? " active" : ""}`} onClick={() => setSpan(r)}>{r}</button>
        ))}
      </div>
      {span === CUSTOM && (
        <div className="row" style={{ marginBottom: 16 }}>
          <label className="field inline"><span>From</span>
            <input type="date" className="input" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label className="field inline"><span>To</span>
            <input type="date" className="input" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} />
          </label>
          {(from || to) && <button className="btn btn-sm btn-ghost" onClick={() => { setFrom(""); setTo(""); }}>Clear dates</button>}
        </div>
      )}
      {notice && <div className="alert alert-warning" style={{ marginBottom: 14 }}>{notice}</div>}

      <div className="grid grid-4">
        <StatCard label="Total entries" value={String(stats.total)} hint={rangeHint} icon="🗂️" />
        <StatCard label="Most common mood" value={mood ? `${MOODS[mood]} ${mood}` : "—"} hint="Self-reported" icon="💬" />
        <StatCard label="Top factors" value={topFactors(entries).join(" · ") || "—"} hint="Selected most often" icon="🧩" />
        <StatCard label="Current streak" value={`${stats.streak} day${stats.streak === 1 ? "" : "s"}`} hint="Days in a row" icon="🔥" />
      </div>

      {insights.length > 0 && (
        <>
          <div className="section"><h2>Insights</h2><p>Simple patterns in your own data — not a diagnosis or an assessment of your wellbeing.</p></div>
          <div className="grid grid-auto">
            {insights.map((i) => (
              <div key={i.text} className="card hover">
                <span className="chip chip-xs">{INSIGHT_ICON[i.source]} {i.source}</span>
                <p style={{ marginTop: 8 }}>{i.text}</p>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="split" style={{ alignItems: "start" }}>
        <div className="stack">
          <div className="section"><h2>🧭 Model signal</h2><p>Facial expressions the model detected in images you saved.</p></div>
          {det.length ? (
            <ModelSignal det={det} dominant={stats.dominantExpression} average={stats.averageConfidence} counts={stats.expressionCounts} />
          ) : <EmptyState icon="📷" title="No saved detections" text="Save a result on Detect Emotion to see expression patterns." />}
        </div>
        <div className="stack">
          <div className="section"><h2>💬 Self-reported mood</h2><p>How you said you felt, in your own words.</p></div>
          {moods.length ? <MoodSignal moods={moods} />
            : <EmptyState icon="📝" title="No mood check-ins" text="Complete a daily check-in to see your mood over time." />}
          <DayColumns title="Entries per day" days={[...perDay]} />
        </div>
      </div>

      <div className="section"><h2>Your recent activity</h2>
        <p>{matching.length} entr{matching.length === 1 ? "y" : "ies"}{matching.length > shown.length ? ` · showing the latest ${shown.length}` : ""}</p></div>
      <div className="row" style={{ marginBottom: 12, justifyContent: "space-between" }}>
        <div className="row" role="tablist" aria-label="Filter history">
          {FILTERS.map(([k, label]) => (
            <button key={k} role="tab" aria-selected={filter === k} className={`chip${filter === k ? " active" : ""}`} onClick={() => setFilter(k)}>{label}</button>
          ))}
        </div>
        <label className="row small" style={{ gap: 8 }}>
          <span className="muted">Expression</span>
          <select className="input input-sm" value={emotion} onChange={(e) => setEmotion(e.target.value)}>
            <option value="">All expressions</option>
            {EMOTIONS.map((e) => <option key={e} value={e}>{emoji(e)} {e}</option>)}
          </select>
        </label>
      </div>
      {shown.length === 0 ? (
        <EmptyState icon="🔎" title="No matching entries" text="Nothing matches these filters in the selected time range.">
          {(filter !== "all" || emotion) && <button className="btn" onClick={() => { setFilter("all"); setEmotion(""); }}>Clear filters</button>}
        </EmptyState>
      ) : (
        <div className="card table-wrap" style={{ padding: "6px 10px" }}>
          <table className="table">
            <thead><tr><th>When</th><th>Source</th><th>Expression</th><th>Confidence</th><th>Mood</th><th>Details</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>
              {shown.map((e) => (
                <tr key={e.id}>
                  <td className="muted" style={{ whiteSpace: "nowrap" }}>{formatTime(e.timestamp)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{sourceLabel(e)}</td>
                  <td>{e.detectedEmotion ? <EmotionPill emotion={e.detectedEmotion} /> : <span className="muted">—</span>}</td>
                  <td>{e.confidence != null ? pct(e.confidence) : <span className="muted">—</span>}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{e.selfReportedMood ? `${MOODS[e.selfReportedMood] ?? ""} ${e.selfReportedMood}` : <span className="muted">—</span>}</td>
                  <td className="muted small">
                    {details(e) || (e.journalText ? "" : "—")}
                    {e.journalText && (
                      <details><summary>{e.kind === "checkin" ? "Note" : "Entry"}</summary>
                        <p style={{ whiteSpace: "pre-wrap", color: "var(--text)", marginTop: 4 }}>{e.journalText}</p></details>
                    )}
                  </td>
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

      <details className="card manage" style={{ marginTop: 20 }}>
        <summary className="card-title">🗑️ Manage my data</summary>
        <p className="muted small" style={{ margin: "8px 0 12px" }}>
          You can delete any entry with its Delete button above, or all of your history here. Deletion is permanent.
        </p>
        <label className="check"><input type="checkbox" checked={sure} onChange={(e) => setSure(e.target.checked)} />
          I understand this deletes all my history</label>
        <div style={{ marginTop: 12 }}>
          <button className="btn btn-danger" disabled={!sure || busy === "all"} onClick={removeAll}>
            {busy === "all" ? "Deleting…" : "Delete all history"}
          </button>
        </div>
      </details>
    </>
  );
}
