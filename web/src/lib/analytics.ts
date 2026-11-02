// Summaries and simple rule-based insights (port of src/analytics.py).
//
// Two kinds of signal are kept strictly apart:
// * Model signal: facial expressions the model detected (kind "detection").
// * Self-reported mood: what the user said in a daily check-in.
// Neither is a measurement of anyone's actual emotional or mental state, and no insight here is a diagnosis.
import { EMOTIONS, MODERATE_CONFIDENCE } from "./emotion/core.ts";
import type { HistoryEntry } from "./history";
import { MOOD_SCORE, type ScaleKey } from "./wellbeing.ts";

const DAY_MS = 24 * 3600 * 1000;

/** Counts in first-seen order; the most common value wins ties by first appearance (like Counter.most_common). */
function mostCommon(values: string[]): [string, number] | null {
  const counts = new Map<string, number>();
  for (const v of values) counts.set(v, (counts.get(v) ?? 0) + 1);
  let best: [string, number] | null = null;
  for (const [k, n] of counts) if (!best || n > best[1]) best = [k, n];
  return best;
}

export function emotionCounts(values: string[]): Record<string, number> {
  const counts = Object.fromEntries(EMOTIONS.map((e) => [e, 0])) as Record<string, number>;
  for (const v of values) if (v in counts) counts[v] += 1;
  return counts;
}

/** Local calendar day of an entry, as "YYYY-MM-DD". */
export function localDay(value: string | Date): string {
  const d = typeof value === "string" ? new Date(value) : value;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export const detections = (entries: HistoryEntry[]) => entries.filter((e) => e.kind === "detection" && e.detectedEmotion);

/** Every entry where the user reported a mood (a check-in, or a saved detection with a mood). */
export const moodReports = (entries: HistoryEntry[]) =>
  entries.filter((e) => e.selfReportedMood != null && e.selfReportedMood in MOOD_SCORE);

/** Consecutive days with at least one entry, ending today (or yesterday, so a streak isn't "lost" just because
 *  today's check-in hasn't happened yet). */
export function streakDays(days: Set<string>, today: Date): number {
  const shift = (n: number) => localDay(new Date(today.getFullYear(), today.getMonth(), today.getDate() - n));
  const start = days.has(shift(0)) ? 0 : 1;
  let streak = 0;
  while (days.has(shift(start + streak))) streak += 1;
  return streak;
}

export type HistoryStats = {
  total: number; today: number; streak: number; detections: number; moodReports: number;
  dominantExpression: string | null; averageConfidence: number | null; expressionCounts: Record<string, number>;
};

export function historyStats(entries: HistoryEntry[], today = new Date()): HistoryStats {
  const day = localDay(today);
  const det = detections(entries);
  const confidences = det.map((e) => e.confidence ?? 0);
  return {
    total: entries.length,
    today: entries.filter((e) => localDay(e.timestamp) === day).length,
    streak: streakDays(new Set(entries.map((e) => localDay(e.timestamp))), today),
    detections: det.length,
    moodReports: moodReports(entries).length,
    dominantExpression: mostCommon(det.map((e) => e.detectedEmotion!))?.[0] ?? null,
    averageConfidence: det.length ? confidences.reduce((a, b) => a + b, 0) / det.length : null,
    expressionCounts: emotionCounts(det.map((e) => e.detectedEmotion!)),
  };
}

export function filterSince(entries: HistoryEntry[], days: number | null, now = Date.now()): HistoryEntry[] {
  if (!days) return entries;
  const cutoff = now - days * DAY_MS;
  return entries.filter((e) => Date.parse(e.timestamp) >= cutoff);
}

export const mostCommonMood = (entries: HistoryEntry[]) => mostCommon(moodReports(entries).map((e) => e.selfReportedMood!));

/** The factors selected most often in check-ins, most common first. */
export function topFactors(entries: HistoryEntry[], n = 2): string[] {
  const counts = new Map<string, number>();
  for (const e of moodReports(entries)) for (const f of e.moodFactors ?? []) counts.set(f, (counts.get(f) ?? 0) + 1);
  return [...counts].sort((a, b) => b[1] - a[1]).slice(0, n).map(([f]) => f);
}

export type Insight = { source: "Model signal" | "Self-reported mood" | "Tip"; text: string };

/** Rule-based observations about the user's own history. Entries are expected newest first. */
export function generateInsights(entries: HistoryEntry[], recent = 10): Insight[] {
  const insights: Insight[] = [];
  const det = detections(entries).slice(0, recent);
  if (det.length >= 3) {
    const [top, n] = mostCommon(det.map((e) => e.detectedEmotion!))!;
    if (n / det.length >= 0.5) {
      insights.push({ source: "Model signal", text: `${top} has appeared in ${n} of your last ${det.length} saved detections.` });
      if (top === "Neutral") {
        insights.push({ source: "Tip", text: "Your recent predictions have mostly been Neutral. A facial expression often "
          + "doesn't show how you feel — the daily check-in lets you note that in your own words." });
      }
    }
    const low = det.filter((e) => (e.confidence ?? 0) < MODERATE_CONFIDENCE).length;
    if (low / det.length >= 0.4) {
      insights.push({ source: "Tip", text: `${low} of your last ${det.length} detections had low model confidence. Better `
        + "lighting and a front-facing image usually give the model a clearer view." });
    }
  }

  const moods = moodReports(entries).slice(0, recent);
  if (moods.length >= 3) {
    const [top, n] = mostCommon(moods.map((e) => e.selfReportedMood!))!;
    insights.push({ source: "Self-reported mood",
      text: `You've most often described your mood as “${top}” (${n} of your last ${moods.length} check-ins).` });
    const hard = moods.slice(0, 5).filter((e) => MOOD_SCORE[e.selfReportedMood!] <= 2).length;
    if (hard >= 3) {
      insights.push({ source: "Self-reported mood", text: "You've reported feeling low or finding things difficult several "
        + "times recently. It may help to talk with someone you trust, or try one of the wellbeing activities." });
    }
  }

  if (det.filter((e) => e.selfReportedMood).length >= 3) {
    insights.push({ source: "Tip", text: "When you save a detection together with your own mood, compare them: the model "
      + "reads expressions, and expressions and feelings often differ." });
  }
  return insights;
}

// ---------------------------------------------------------------------------------------------------------------
// Wellbeing tracker: the user's own 1–5 reports (mood from any mood report; energy, stress, sleep from check-ins).
// ---------------------------------------------------------------------------------------------------------------
export type Metric = "mood" | ScaleKey;
export const METRIC_LABEL: Record<Metric, string> = {
  mood: "Mood", energyLevel: "Energy", stressLevel: "Stress", sleepQuality: "Sleep",
};

/** The entry's 1–5 score for a metric, or null if it wasn't reported. */
export function metricScore(e: HistoryEntry, m: Metric): number | null {
  if (m === "mood") return e.selfReportedMood != null && e.selfReportedMood in MOOD_SCORE ? MOOD_SCORE[e.selfReportedMood] : null;
  const v = e[m];
  return typeof v === "number" && v >= 1 && v <= 5 ? v : null;
}

export function averageScore(entries: HistoryEntry[], m: Metric): number | null {
  const v = entries.map((e) => metricScore(e, m)).filter((x): x is number => x != null);
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}

/** Average score per local day, oldest first. */
export function dailyAverages(entries: HistoryEntry[], m: Metric): { day: string; value: number; n: number }[] {
  const days = new Map<string, number[]>();
  for (const e of entries) {
    const v = metricScore(e, m);
    if (v != null) days.set(localDay(e.timestamp), [...(days.get(localDay(e.timestamp)) ?? []), v]);
  }
  return [...days].sort(([a], [b]) => a.localeCompare(b))
    .map(([day, v]) => ({ day, value: v.reduce((a, b) => a + b, 0) / v.length, n: v.length }));
}

/** Entries in [now - 2·days, now - days): the period just before filterSince(entries, days). */
export function previousPeriod(entries: HistoryEntry[], days: number, now = Date.now()): HistoryEntry[] {
  return entries.filter((e) => {
    const t = Date.parse(e.timestamp);
    return t >= now - 2 * days * DAY_MS && t < now - days * DAY_MS;
  });
}

/** Entries between two local dates ("YYYY-MM-DD", both inclusive; either may be empty). */
export function filterBetween(entries: HistoryEntry[], from?: string, to?: string): HistoryEntry[] {
  return entries.filter((e) => {
    const d = localDay(e.timestamp);
    return (!from || d >= from) && (!to || d <= to);
  });
}

/** Entries per local day for the last `days` days (zeros included), or for every day with data. Oldest first. */
export function dayCounts(entries: HistoryEntry[], days: number | null, today = new Date()): [string, number][] {
  const counts = new Map<string, number>();
  if (days) {
    for (let i = days - 1; i >= 0; i--) {
      counts.set(localDay(new Date(today.getFullYear(), today.getMonth(), today.getDate() - i)), 0);
    }
  }
  for (const e of entries) {
    const d = localDay(e.timestamp);
    if (!days || counts.has(d)) counts.set(d, (counts.get(d) ?? 0) + 1);
  }
  return [...counts].sort(([a], [b]) => a.localeCompare(b));
}

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** Average score by weekday, Monday first (null where there is no data). */
export function weekdayAverages(entries: HistoryEntry[], m: Metric): (number | null)[] {
  const sums = WEEKDAYS.map(() => [0, 0]);
  for (const e of entries) {
    const v = metricScore(e, m);
    if (v == null) continue;
    const w = (new Date(e.timestamp).getDay() + 6) % 7;
    sums[w][0] += v;
    sums[w][1] += 1;
  }
  return sums.map(([s, n]) => (n ? s / n : null));
}

/** Entries where the user reported any wellbeing metric (check-ins, or detections saved with a mood). */
export const wellbeingReports = (entries: HistoryEntry[]) =>
  entries.filter((e) => (Object.keys(METRIC_LABEL) as Metric[]).some((m) => metricScore(e, m) != null));

const fmt1 = (x: number) => x.toFixed(1);

/** Plain-language observations for the tracker. `entries` is the full history; `days` the selected range
 *  (null = all data, compared month by month). Describes the user's own reports only — never a diagnosis. */
export function trackerInsights(entries: HistoryEntry[], days: number | null, now = Date.now()): Insight[] {
  const span = days ?? 30;
  const current = filterSince(entries, span, now);
  const previous = previousPeriod(entries, span, now);
  const before = days ? `the previous ${days} days` : "the 30 days before";
  const insights: Insight[] = [];
  const count = (list: HistoryEntry[], m: Metric) => list.filter((e) => metricScore(e, m) != null).length;

  for (const m of ["mood", "stressLevel", "energyLevel", "sleepQuality"] as Metric[]) {
    if (count(current, m) < 2 || count(previous, m) < 2) continue;
    const a = averageScore(current, m)!;
    const b = averageScore(previous, m)!;
    if (Math.abs(a - b) < 0.3) continue;
    const what = m === "mood" ? "self-reported mood" : m === "sleepQuality" ? "sleep rating" : `${METRIC_LABEL[m].toLowerCase()} level`;
    insights.push({ source: "Self-reported mood",
      text: `${days ? "Your" : "Over the last 30 days, your"} average ${what} was ${a > b ? "higher" : "lower"} than in ${before} (${fmt1(a)} vs ${fmt1(b)} out of 5).` });
  }

  const inRange = days ? current : entries;
  const stressful = dailyAverages(inRange, "stressLevel").filter((d) => d.value >= 4).length;
  if (stressful) {
    insights.push({ source: "Self-reported mood",
      text: `You reported high stress (4–5) on ${stressful} day${stressful === 1 ? "" : "s"} ${days ? `in the last ${days} days` : "so far"}.` });
  }
  const checkinDays = new Set(inRange.filter((e) => e.kind === "checkin").map((e) => localDay(e.timestamp))).size;
  if (days && checkinDays) {
    insights.push({ source: "Self-reported mood", text: `You checked in on ${checkinDays} of the last ${days} days.` });
  }
  const moods = inRange.map((e) => metricScore(e, "mood")).filter((x): x is number => x != null);
  if (moods.length >= 3 && moods.filter((v) => v <= 2).length >= 3) {
    insights.push({ source: "Tip", text: "You've described your mood as low or difficult several times. Talking with someone "
      + "you trust can help, and if it keeps feeling hard, a mental-health professional can offer support." });
  }
  return insights;
}

/** Where an entry came from, for the history table. */
export function sourceLabel(e: HistoryEntry): string {
  if (e.kind === "detection") return /cam/i.test(e.source ?? "") ? "Webcam" : "Image";
  return { checkin: "Check-in", journal: "Journal", reset: "Activity" }[e.kind] ?? e.kind;
}

/** Webcam/image session summary (summarize_session). */
export function summarizeSession(history: { emotion: string; confidence: number }[]) {
  const total = history.length;
  return {
    predictions: total,
    counts: emotionCounts(history.map((h) => h.emotion)),
    dominant: mostCommon(history.map((h) => h.emotion))?.[0] ?? null,
    averageConfidence: total ? history.reduce((a, h) => a + h.confidence, 0) / total : null,
  };
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function formatShort(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
