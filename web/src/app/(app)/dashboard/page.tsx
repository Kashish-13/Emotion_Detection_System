"use client";

// Dashboard (src/ui/views/dashboard.py): a short wellbeing summary, this week's self-reported numbers, mood trend,
// the latest detected expression, recent activity, and next steps (a suggestion, the toolkit, professional support).
import Link from "next/link";
import { TimeChart } from "@/components/Charts";
import { EmotionBars, EmptyState, ResultCard, StatCard } from "@/components/Emotion";
import { Timeline } from "@/components/Timeline";
import { activityHref, SuggestionList } from "@/components/Wellbeing";
import {
  averageScore, dailyAverages, detections, filterSince, formatShort, historyStats, localDay, moodReports,
} from "@/lib/analytics";
import { displayName, useAuth } from "@/lib/auth";
import { emoji } from "@/lib/emotions";
import type { HistoryEntry } from "@/lib/history";
import { useSession, type LastFace } from "@/lib/session";
import { useHistory } from "@/lib/useHistory";
import { DISCLAIMER, MOOD_SCORE, MOOD_SUGGESTIONS, MOODS, suggestionsFor } from "@/lib/wellbeing";

type Current = { emotion: string; confidence: number; meta: string };
const MOOD_WORD = Object.fromEntries(Object.entries(MOOD_SCORE).map(([m, v]) => [v, m]));

/** Latest expression: this session's last analysis, else the latest saved detection. */
function current(last: LastFace | null, entries: HistoryEntry[]): Current | null {
  if (last) return { ...last, meta: `From your latest ${last.source} analysis this session.` };
  const det = detections(entries)[0];
  if (!det) return null;
  return { emotion: det.detectedEmotion!, confidence: det.confidence ?? 0, meta: `Latest saved detection · ${formatShort(det.timestamp)}` };
}

function greeting(d = new Date()) {
  const h = d.getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

function Recommended({ entries }: { entries: HistoryEntry[] }) {
  const det = detections(entries)[0];
  const mood = moodReports(entries)[0];
  if (mood && (!det || mood.timestamp > det.timestamp)) {
    const m = mood.selfReportedMood!;
    return (
      <>
        <p className="muted small">Based on your latest check-in: {MOODS[m]} {m}</p>
        <SuggestionList items={[MOOD_SUGGESTIONS[m]]} compact />
      </>
    );
  }
  const emotion = det?.detectedEmotion ?? "Neutral";
  const s = suggestionsFor(emotion);
  return (
    <>
      <p className="muted small">{det ? `Based on your latest detected expression: ${emoji(emotion)} ${emotion}` : "A good place to start"}</p>
      <div className="card-title" style={{ margin: "8px 0 4px" }}>{s.headline}</div>
      <SuggestionList items={s.items.slice(0, 2)} compact />
    </>
  );
}

const score = (v: number | null, mood = false) =>
  v == null ? "—" : `${v.toFixed(1)} / 5${mood ? ` · ${MOOD_WORD[Math.round(v)]}` : ""}`;

export default function DashboardPage() {
  const { user } = useAuth();
  const { entries } = useHistory();
  const session = useSession();

  if (!entries) {
    return <div className="center"><span className="spinner muted" aria-label="Loading your dashboard" /></div>;
  }
  const stats = historyStats(entries);
  const now = current(session.lastFace, entries);
  const week = filterSince(entries, 7);
  const latestMood = moodReports(entries)[0];
  const weekMood = averageScore(week, "mood");
  const weekStress = averageScore(week, "stressLevel");
  const weekEnergy = averageScore(week, "energyLevel");
  const checkinDays = new Set(week.filter((e) => e.kind === "checkin").map((e) => localDay(e.timestamp))).size;
  const checkedInToday = moodReports(entries).some((e) => localDay(e.timestamp) === localDay(new Date()));
  const moodTrend = dailyAverages(filterSince(entries, 30), "mood");

  const summary = checkinDays
    ? `You checked in on ${checkinDays} of the last 7 days${weekMood != null ? `, and your average mood was ${MOOD_WORD[Math.round(weekMood)].toLowerCase()}` : ""}.`
      + (checkedInToday ? " Thanks for checking in today." : " A quick check-in today keeps your tracker up to date.")
    : "No check-ins in the last 7 days yet. A quick check-in takes about a minute and starts your wellbeing tracker.";

  return (
    <>
      <div className="page-head row" style={{ justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div className="eyebrow">Dashboard</div>
          <h1 className="title">{greeting()}, {displayName(user)}</h1>
          <p className="subtitle">{summary}</p>
        </div>
        <div className="row">
          <Link href="/checkin" className="btn btn-primary">{checkedInToday ? "Check in again" : "Daily check-in"}</Link>
          <Link href="/detect" className="btn">Detect emotion</Link>
        </div>
      </div>

      <div className="grid grid-5">
        <StatCard label="Recent mood" icon={latestMood ? MOODS[latestMood.selfReportedMood!] : "💬"}
                  value={latestMood?.selfReportedMood ?? "—"} hint={latestMood ? formatShort(latestMood.timestamp) : "Not reported yet"} />
        <StatCard label="Mood this week" icon="🙂" value={score(weekMood)} hint={weekMood == null ? "No reports this week" : MOOD_WORD[Math.round(weekMood)]} />
        <StatCard label="Stress this week" icon="🌡️" value={score(weekStress)} hint="1 low · 5 high" />
        <StatCard label="Energy this week" icon="⚡" value={score(weekEnergy)} hint="1 low · 5 high" />
        <StatCard label="Check-ins this week" icon="📝" value={`${checkinDays} / 7 days`}
                  hint={`Streak: ${stats.streak} day${stats.streak === 1 ? "" : "s"}`} />
      </div>

      <div className="split" style={{ marginTop: 24 }}>
        <div>
          <div className="section" style={{ marginTop: 0 }}><h2>Mood trend</h2><p>Your self-reported mood over the last 30 days.</p></div>
          {moodTrend.length ? (
            <TimeChart title="Daily average mood" line color="#4f46e5" labelWidth={70} height={220} yMin={1} yMax={5}
                       yTicks={[1, 2, 3, 4, 5].map((v) => ({ v, label: MOOD_WORD[v] }))}
                       points={moodTrend.map((d) => ({
                         t: Date.parse(`${d.day}T12:00:00`), y: d.value, color: "#4f46e5",
                         tip: <><strong>{new Date(`${d.day}T12:00:00`).toLocaleDateString(undefined, { day: "2-digit", month: "short" })}</strong><br />{MOOD_WORD[Math.round(d.value)]} ({d.value.toFixed(1)} / 5)</>,
                       }))} />
          ) : (
            <EmptyState icon="📈" title="Your mood trend appears here" text="Check in on a few days to see how your mood changes.">
              <Link href="/checkin" className="btn btn-primary">Check in</Link>
            </EmptyState>
          )}
          <Link href="/tracker" className="small" style={{ display: "inline-block", marginTop: 8 }}>Open the full wellbeing tracker →</Link>
        </div>
        <div>
          <div className="section" style={{ marginTop: 0 }}><h2>Latest expression</h2><p>What the model detected — an estimate, not how you feel.</p></div>
          {now ? (
            <ResultCard emotion={now.emotion} confidence={now.confidence} title="Model detected" meta={now.meta} />
          ) : (
            <EmptyState icon="📷" title="Nothing analysed yet" text="Analyse a photo or a webcam frame to see the expression the model detects." />
          )}
          <div className="row" style={{ marginTop: 12 }}>
            <Link href="/detect" className="btn">{now ? "Analyse again" : "Analyse a photo"}</Link>
            <Link href="/detect?mode=webcam" className="btn btn-ghost">Use camera</Link>
          </div>
        </div>
      </div>

      <div className="split" style={{ marginTop: 8 }}>
        <div>
          <div className="section"><h2>Expression distribution</h2><p>Across your saved detections.</p></div>
          {stats.detections ? <EmotionBars values={stats.expressionCounts} mode="count" />
            : <EmptyState icon="📊" title="No saved detections" text="Save a result on Detect Emotion to see the distribution." />}
        </div>
        <div>
          <div className="section"><h2>Recent activity</h2><p>Your latest saved moments.</p></div>
          {entries.length ? <Timeline entries={entries.slice(0, 6)} /> : (
            <EmptyState icon="🌱" title="Your journey starts here." text="Complete your first check-in to see your activity." />
          )}
        </div>
      </div>

      <div className="section"><h2>For you</h2><p>Small, optional next steps.</p></div>
      <div className="grid grid-3">
        <div className="card">
          <div className="stat-label">Suggestion</div>
          <Recommended entries={entries} />
        </div>
        <div className="card">
          <div className="stat-label">Wellbeing toolkit</div>
          <p className="muted small" style={{ margin: "6px 0 10px" }}>Short guided activities and ideas for when you&apos;re stressed,
            anxious, low, angry or sleeping poorly.</p>
          <div className="stack">
            <Link href={activityHref("breathing")} className="btn btn-sm btn-block">🌬️ 60-second breathing</Link>
            <Link href={activityHref("grounding")} className="btn btn-sm btn-block">🧠 5-4-3-2-1 grounding</Link>
            <Link href="/wellbeing" className="btn btn-sm btn-block btn-ghost">Browse the toolkit →</Link>
          </div>
        </div>
        <div className="card">
          <div className="stat-label">Professional support</div>
          <p className="muted small" style={{ margin: "6px 0 10px" }}>Talking to a qualified professional can help — you don&apos;t need
            to be in crisis to reach out.</p>
          <div className="stack">
            <Link href="/support" className="btn btn-sm btn-block">Find professional support</Link>
            <Link href="/support#urgent" className="btn btn-sm btn-block btn-ghost">Need immediate help?</Link>
          </div>
        </div>
      </div>
      <p className="muted small" style={{ marginTop: 28 }}>{DISCLAIMER}</p>
    </>
  );
}
