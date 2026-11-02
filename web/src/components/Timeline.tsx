// Vertical timeline of saved entries (the dashboard's "Recent activity" and History's "Recent check-ins").
import type { CSSProperties, ReactNode } from "react";
import { EmotionPill } from "@/components/Emotion";
import { formatShort } from "@/lib/analytics";
import { color } from "@/lib/emotions";
import type { HistoryEntry } from "@/lib/history";
import { ACTIVITIES, MOODS } from "@/lib/wellbeing";

const MOOD_COLOR = "#4f46e5";
// Self-reported mood uses one violet hue, lighter for brighter moods (it is not an emotion class).
export const MOOD_COLORS: Record<string, string> = {
  Great: "#a5b4fc", Good: "#818cf8", Okay: "#6366f1", Low: "#4f46e5", Difficult: "#3730a3",
};

export function entrySummary(e: HistoryEntry): { c: string; main: ReactNode } {
  if (e.kind === "detection" && e.detectedEmotion) {
    return { c: color(e.detectedEmotion), main: <><EmotionPill emotion={e.detectedEmotion} /> {Math.round((e.confidence ?? 0) * 100)}% confidence</> };
  }
  if (e.kind === "checkin") {
    const mood = e.selfReportedMood ?? "";
    return { c: MOOD_COLORS[mood] ?? MOOD_COLOR, main: <>Check-in · {MOODS[mood] ?? ""} {mood}</> };
  }
  if (e.kind === "journal") return { c: MOOD_COLOR, main: <>Journal · {e.prompt ?? "Reflection"}</> };
  const act = ACTIVITIES[e.activity ?? ""];
  return { c: MOOD_COLOR, main: <>{act?.emoji ?? "🌿"} {act?.title ?? "Wellbeing activity"} → {e.feelingAfter ?? ""}</> };
}

export function Timeline({ entries, factors = false }: { entries: HistoryEntry[]; factors?: boolean }) {
  return (
    <div className="card">
      <ol className="timeline">
        {entries.map((e) => {
          const { c, main } = entrySummary(e);
          return (
            <li key={e.id} style={{ "--c": c } as CSSProperties}>
              <div className="tl-time">{formatShort(e.timestamp)}</div>
              <div className="tl-main">
                {main}
                {factors && (e.moodFactors ?? []).map((f) => <span key={f} className="chip chip-xs">{f}</span>)}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
