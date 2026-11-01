// Dashboard statistics from saved detections (mirrors src/analytics.py history_stats).
import { EMOTIONS } from "./emotions";
import type { HistoryEntry } from "./history";

export type Stats = {
  predictions: number;
  thisWeek: number;
  mostDetected: string | null;
  averageConfidence: number | null;
  counts: Record<string, number>;
};

export function detections(entries: HistoryEntry[]) {
  return entries.filter((e) => e.kind === "detection" && e.detectedEmotion);
}

export function computeStats(entries: HistoryEntry[], now = Date.now()): Stats {
  const det = detections(entries);
  const counts = Object.fromEntries(EMOTIONS.map((e) => [e, 0])) as Record<string, number>;
  for (const e of det) counts[e.detectedEmotion!] = (counts[e.detectedEmotion!] ?? 0) + 1;
  const ranked = Object.entries(counts).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  const confidences = det.map((e) => e.confidence).filter((c): c is number => typeof c === "number");
  const weekAgo = now - 7 * 24 * 3600 * 1000;
  return {
    predictions: det.length,
    thisWeek: det.filter((e) => Date.parse(e.timestamp) >= weekAgo).length,
    mostDetected: ranked[0]?.[0] ?? null,
    averageConfidence: confidences.length ? confidences.reduce((a, b) => a + b, 0) / confidences.length : null,
    counts,
  };
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
