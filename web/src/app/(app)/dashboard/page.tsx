"use client";

// Dashboard (src/ui/views/dashboard.py): the latest expression front and centre, then today's status,
// a suggestion, recent activity and quick actions.
import Link from "next/link";
import { EmotionBars, EmotionPill, EmptyState, ResultCard, StatCard } from "@/components/Emotion";
import { Timeline } from "@/components/Timeline";
import { activityHref, SuggestionList } from "@/components/Wellbeing";
import { detections, formatShort, formatTime, historyStats, localDay, moodReports } from "@/lib/analytics";
import { displayName, useAuth } from "@/lib/auth";
import { emoji } from "@/lib/emotions";
import type { HistoryEntry } from "@/lib/history";
import { useSession, type LastFace } from "@/lib/session";
import { useHistory } from "@/lib/useHistory";
import { DISCLAIMER, MOOD_SUGGESTIONS, MOODS, suggestionsFor } from "@/lib/wellbeing";

type Current = { emotion: string; confidence: number; probabilities: Record<string, number> | null;
  top3: { emotion: string; probability: number }[]; meta: string };

/** Latest expression: this session's last analysis, else the latest saved detection. */
function current(last: LastFace | null, entries: HistoryEntry[]): Current | null {
  if (last) return { ...last, meta: `From your latest ${last.source} analysis this session.` };
  const det = detections(entries)[0];
  if (!det) return null;
  const top3 = det.topPredictions?.length ? det.topPredictions : [{ emotion: det.detectedEmotion!, probability: det.confidence ?? 0 }];
  return { emotion: det.detectedEmotion!, confidence: det.confidence ?? 0, probabilities: null, top3,
    meta: `Latest saved detection · ${formatShort(det.timestamp)}` };
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
      <p className="muted small" style={{ marginTop: 8 }}>General wellbeing ideas, not medical advice.</p>
    </>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { entries } = useHistory();
  const session = useSession();

  if (!entries) {
    return <div className="center"><span className="spinner muted" aria-label="Loading your history" /></div>;
  }
  const stats = historyStats(entries);
  const now = current(session.lastFace, entries);
  const today = localDay(new Date());
  const checkedIn = moodReports(entries).some((e) => localDay(e.timestamp) === today);
  const recentDet = detections(entries).slice(0, 5);

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Dashboard</div>
        <h1 className="title">Good to see you, {displayName(user)} 👋</h1>
        <p className="subtitle">How are you feeling today?</p>
      </div>

      <div className="split dash-top">
        <div className="stack">
          {now ? (
            <ResultCard emotion={now.emotion} confidence={now.confidence} title="Current emotion" meta={now.meta} />
          ) : (
            <div className="card result" style={{ "--c": "#4f46e5" } as React.CSSProperties}>
              <div className="eyebrow">Current emotion</div>
              <div className="result-main">
                <div className="emoji-orb" aria-hidden="true">✨</div>
                <div>
                  <div className="result-name" style={{ fontSize: "1.6rem", letterSpacing: 0 }}>Nothing analysed yet</div>
                  <p className="muted" style={{ marginTop: 6 }}>Analyse a photo or a webcam frame to see the expression the model
                    detects, with its confidence.</p>
                </div>
              </div>
            </div>
          )}
          <div className="row">
            <Link href="/detect" className="btn btn-primary">{now ? "Analyze again" : "Analyze my emotion"}</Link>
            <Link href="/detect?mode=webcam" className="btn">Use camera</Link>
          </div>
        </div>
        {now?.probabilities ? (
          <EmotionBars values={now.probabilities} title="Emotion probabilities" />
        ) : now ? (
          <EmotionBars values={Object.fromEntries(now.top3.map((p) => [p.emotion, p.probability]))} title="Top 3 predictions" />
        ) : (
          <EmptyState icon="📊" title="Probabilities appear here" text="All seven expressions, ranked by the model." />
        )}
      </div>

      <div className="grid grid-4" style={{ marginTop: 24 }}>
        <StatCard label="Today's check-in" value={checkedIn ? "Done" : "Not yet"}
                  hint={checkedIn ? "Thanks for checking in" : "Takes about a minute"} icon={checkedIn ? "✅" : "📝"} />
        <StatCard label="Top expression" value={stats.dominantExpression ?? "—"} hint={`From ${stats.detections} saved detection${stats.detections === 1 ? "" : "s"}`}
                  icon="🧭" emotion={stats.dominantExpression} />
        <StatCard label="Average confidence" value={stats.averageConfidence == null ? "—" : `${Math.round(stats.averageConfidence * 100)}%`}
                  hint="Of saved detections" icon="🎯" />
        <StatCard label="Current streak" value={`${stats.streak} day${stats.streak === 1 ? "" : "s"}`} hint="Days in a row" icon="🔥" />
      </div>

      <div className="split" style={{ marginTop: 8 }}>
        <div>
          <div className="section"><h2>Recommended for you</h2><p>A small, optional next step.</p></div>
          <div className="card"><Recommended entries={entries} /></div>
        </div>
        <div>
          <div className="section"><h2>Recent activity</h2><p>Your latest saved moments.</p></div>
          {entries.length ? <Timeline entries={entries.slice(0, 6)} /> : (
            <EmptyState icon="🌱" title="Your journey starts here." text="Complete your first check-in to see your insights." />
          )}
        </div>
      </div>

      <div className="section"><h2>Quick actions</h2></div>
      <div className="grid grid-4">
        <Link href="/detect" className="btn">📷 Detect emotion</Link>
        <Link href="/checkin" className="btn">📝 Daily check-in</Link>
        <Link href={activityHref("breathing")} className="btn">🌬️ Breathing reset</Link>
        <Link href="/history" className="btn">📈 View insights</Link>
      </div>

      {recentDet.length > 0 && (
        <>
          <div className="section"><h2>Saved predictions</h2><p>Detected expressions across your saved results, from this site or the Streamlit app.</p></div>
          <div className="split">
            <EmotionBars values={stats.expressionCounts} title="Detected expressions (saved predictions)" mode="count" />
            <div className="card table-wrap" style={{ padding: "6px 10px" }}>
              <table className="table">
                <thead><tr><th>Expression</th><th>Confidence</th><th>When</th><th>Source</th></tr></thead>
                <tbody>
                  {recentDet.map((e) => (
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
          </div>
        </>
      )}
      <p className="muted small" style={{ marginTop: 28 }}>{DISCLAIMER}</p>
    </>
  );
}
