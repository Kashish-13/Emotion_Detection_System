"use client";

// Wellbeing Tracker: trends in the user's own reports (mood from any mood report; energy, stress and sleep from
// check-ins). Self-reported only — no model signal and no diagnosis.
import Link from "next/link";
import { useState } from "react";
import { CountBars, DayColumns, TimeChart } from "@/components/Charts";
import { EmptyState, StatCard } from "@/components/Emotion";
import {
  averageScore, dailyAverages, dayCounts, filterSince, METRIC_LABEL, previousPeriod, trackerInsights, weekdayAverages,
  WEEKDAYS, wellbeingReports, type Metric,
} from "@/lib/analytics";
import { useHistory } from "@/lib/useHistory";
import { MOOD_SCORE, SCALES } from "@/lib/wellbeing";

const RANGES: Record<string, number | null> = { "7 days": 7, "30 days": 30, "All data": null };
const METRICS: { key: Metric; icon: string; color: string; hint: string }[] = [
  { key: "mood", icon: "🙂", color: "#4f46e5", hint: "1 = Difficult · 5 = Great" },
  { key: "stressLevel", icon: "🌡️", color: "#b45309", hint: "1 = Not at all · 5 = Very stressed" },
  { key: "energyLevel", icon: "⚡", color: "#0f766e", hint: "1 = Very low · 5 = Very high" },
  { key: "sleepQuality", icon: "🌙", color: "#475569", hint: "1 = Very poorly · 5 = Very well" },
];
const MOOD_WORD = Object.fromEntries(Object.entries(MOOD_SCORE).map(([m, v]) => [v, m]));
const INSIGHT_ICON = { "Model signal": "🧭", "Self-reported mood": "💬", Tip: "💡" };
const scaleTicks = (m: Metric) => [1, 2, 3, 4, 5].map((v) => ({
  v, label: m === "mood" ? MOOD_WORD[v] : String(v),
}));

export default function TrackerPage() {
  const { entries: all } = useHistory();
  const [span, setSpan] = useState("7 days");

  const head = (
    <div className="page-head">
      <div className="eyebrow">Wellbeing · Tracker</div>
      <h1 className="title">Your wellbeing <span className="accent">over time</span></h1>
      <p className="subtitle">Trends in your own check-ins: mood, stress, energy and sleep. These are your self-reports,
        not a measurement or an assessment.</p>
    </div>
  );
  if (!all) return <>{head}<div className="center"><span className="spinner muted" aria-label="Loading your check-ins" /></div></>;
  if (!wellbeingReports(all).length) {
    return (
      <>
        {head}
        <EmptyState icon="📈" title="No check-ins to chart yet"
                    text="Complete a daily check-in with your mood, stress, energy and sleep — your trends will appear here.">
          <Link href="/checkin" className="btn btn-primary">Daily check-in</Link>
        </EmptyState>
      </>
    );
  }

  const days = RANGES[span];
  const entries = filterSince(all, days);
  const previous = days ? previousPeriod(all, days) : [];
  const insights = trackerInsights(all, days);
  const checkins = entries.filter((e) => e.kind === "checkin");
  const moodByDay = weekdayAverages(entries, "mood");

  return (
    <>
      {head}
      <div className="row" style={{ marginBottom: 16 }} role="tablist" aria-label="Time range">
        {Object.keys(RANGES).map((r) => (
          <button key={r} role="tab" aria-selected={span === r} className={`chip${span === r ? " active" : ""}`} onClick={() => setSpan(r)}>{r}</button>
        ))}
      </div>

      <div className="grid grid-4">
        {METRICS.map((m) => {
          const avg = averageScore(entries, m.key);
          const prev = averageScore(previous, m.key);
          const delta = avg != null && prev != null ? avg - prev : null;
          const word = m.key === "mood" && avg != null ? ` · ${MOOD_WORD[Math.round(avg)]}` : "";
          return (
            <StatCard key={m.key} label={`Average ${METRIC_LABEL[m.key].toLowerCase()}`} icon={m.icon}
                      value={avg == null ? "—" : `${avg.toFixed(1)} / 5${word}`}
                      hint={delta == null || Math.abs(delta) < 0.05 ? m.hint
                        : `${delta > 0 ? "▲" : "▼"} ${Math.abs(delta).toFixed(1)} vs previous ${days} days`} />
          );
        })}
      </div>

      {insights.length > 0 && (
        <>
          <div className="section"><h2>What stands out</h2><p>Simple patterns in your own check-ins — not a diagnosis.</p></div>
          <div className="grid grid-auto">
            {insights.map((i) => (
              <div key={i.text} className="card">
                <span className="chip chip-xs">{INSIGHT_ICON[i.source]} {i.source === "Tip" ? "Worth knowing" : "Your check-ins"}</span>
                <p style={{ marginTop: 8 }}>{i.text}</p>
                {i.source === "Tip" && <Link href="/support" className="small" style={{ display: "inline-block", marginTop: 8 }}>Find support →</Link>}
              </div>
            ))}
          </div>
        </>
      )}

      <div className="section"><h2>Trends</h2><p>Daily averages of what you reported. Hover or focus a point for details.</p></div>
      <div className="grid grid-2">
        {METRICS.map((m) => {
          const series = dailyAverages(entries, m.key);
          const title = `${METRIC_LABEL[m.key]} trend`;
          if (!series.length) {
            return (
              <div key={m.key} className="chart">
                <div className="chart-title">{title}</div>
                <p className="muted small" style={{ padding: "24px 0" }}>
                  No {METRIC_LABEL[m.key].toLowerCase()} ratings in this period.{" "}
                  {m.key !== "mood" && <Link href="/checkin">Add one in your next check-in.</Link>}
                </p>
              </div>
            );
          }
          return (
            <TimeChart key={m.key} title={title} line color={m.color} labelWidth={m.key === "mood" ? 70 : 30} height={200}
                       yMin={1} yMax={5} yTicks={scaleTicks(m.key)}
                       points={series.map((d) => ({
                         t: Date.parse(`${d.day}T12:00:00`), y: d.value, color: m.color,
                         tip: <><strong>{new Date(`${d.day}T12:00:00`).toLocaleDateString(undefined, { weekday: "short", day: "2-digit", month: "short" })}</strong>
                           <br />{METRIC_LABEL[m.key]} {d.value.toFixed(1)} / 5{d.n > 1 ? ` (avg of ${d.n})` : ""}</>,
                       }))} />
          );
        })}
      </div>

      <div className="section"><h2>Patterns</h2><p>How often you check in, and how your mood tends to look across the week.</p></div>
      <div className="grid grid-2">
        <DayColumns title={`Check-ins per day${days ? ` · last ${days} days` : ""}`} days={dayCounts(checkins, days)} />
        <CountBars title="Average mood by weekday" max={5} format={(v) => (v ? v.toFixed(1) : "—")}
                   caption={days === 7 ? "Each weekday appears once in 7 days — try 30 days for a clearer pattern." : undefined}
                   items={WEEKDAYS.map((d, i) => ({ key: d, label: d, color: "#4f46e5", value: moodByDay[i] ?? 0 }))} />
      </div>

      <div className="card row" style={{ marginTop: 24, justifyContent: "space-between" }}>
        <div>
          <div className="card-title">Keep your tracker up to date</div>
          <p className="muted small">A check-in takes about a minute. Rating {SCALES.map((s) => s.label.toLowerCase()).join(", ")} is optional.</p>
        </div>
        <div className="row">
          <Link href="/checkin" className="btn btn-primary">Check in now</Link>
          <Link href="/wellbeing" className="btn">Wellbeing toolkit</Link>
        </div>
      </div>
      <p className="muted small" style={{ marginTop: 16 }}>
        These charts show what you reported about yourself. They are not a medical or psychological assessment. If things
        keep feeling hard, consider talking to someone you trust or <Link href="/support">a professional</Link>.
      </p>
    </>
  );
}
