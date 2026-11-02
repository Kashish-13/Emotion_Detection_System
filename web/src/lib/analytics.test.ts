// Unit tests for the analytics and wellbeing ports (same cases as tests/test_wellbeing.py), plus cross-checks
// against src/wellbeing.py so the web and Streamlit content can't silently drift apart. Run: npm test
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import {
  averageScore, dailyAverages, dayCounts, filterBetween, filterSince, generateInsights, historyStats, localDay, metricScore,
  previousPeriod, sourceLabel, streakDays, summarizeSession, topFactors, trackerInsights, weekdayAverages, wellbeingReports,
} from "./analytics.ts";
import { EMOTIONS } from "./emotion/core.ts";
import type { HistoryEntry } from "./history";
import {
  ACTIVITIES, EMOTION_SUGGESTIONS, JOURNAL_PROMPTS, MOOD_FACTORS, MOOD_SCORE, MOOD_SUGGESTIONS, MOODS, OVERWHELMED_RESETS,
  SCALES, SITUATIONS, suggestionsFor, TOOLKIT_ORDER,
} from "./wellbeing.ts";

const repo = join(dirname(fileURLToPath(import.meta.url)), "../../..");
const pyWellbeing = readFileSync(join(repo, "src/wellbeing.py"), "utf8");

let n = 0;
const at = (daysAgo: number, fields: Partial<HistoryEntry>): HistoryEntry =>
  ({ id: String(n++), kind: "detection", timestamp: new Date(Date.now() - daysAgo * 86400_000).toISOString(), ...fields });

test("every emotion has suggestions and every link points to a real activity", () => {
  assert.deepEqual(Object.keys(EMOTION_SUGGESTIONS).sort(), [...EMOTIONS].sort());
  for (const s of Object.values(EMOTION_SUGGESTIONS)) {
    assert.ok(s.headline && s.items.length);
    assert.ok(s.items.every(([, a]) => a === null || a in ACTIVITIES));
  }
  assert.ok(Object.keys(MOODS).every((m) => MOOD_SUGGESTIONS[m][1]! in ACTIVITIES));
  assert.ok(OVERWHELMED_RESETS.every((r) => r.activity === null || r.activity in ACTIVITIES));
  assert.equal(TOOLKIT_ORDER.length, 8);
  assert.ok(TOOLKIT_ORDER.every((a) => a in ACTIVITIES));
  assert.equal(suggestionsFor("Unknown"), EMOTION_SUGGESTIONS.Neutral);
  for (const s of Object.values(SITUATIONS)) {
    assert.ok(s.title && s.items.length >= 3);
    assert.ok(s.items.every(([, a]) => a === null || a in ACTIVITIES));
  }
  assert.deepEqual(SCALES.map((s) => s.key), ["energyLevel", "stressLevel", "sleepQuality"]);
});

test("wellbeing content matches src/wellbeing.py", () => {
  for (const [id, a] of Object.entries(ACTIVITIES)) {
    assert.ok(pyWellbeing.includes(`"title": "${a.title}"`), `activity title ${a.title}`);
    for (const step of a.steps) assert.ok(pyWellbeing.includes(`"${step}"`), `step ${step}`);
    assert.ok(pyWellbeing.includes(`"${id}"`), id);
  }
  for (const [m, icon] of Object.entries(MOODS)) assert.ok(pyWellbeing.includes(`"${m}": "${icon}"`), m);
  for (const [m, score] of Object.entries(MOOD_SCORE)) assert.ok(pyWellbeing.includes(`"${m}": ${score}`), m);
  for (const f of MOOD_FACTORS) assert.ok(pyWellbeing.includes(`"${f}"`), f);
  for (const p of JOURNAL_PROMPTS) assert.ok(pyWellbeing.includes(`"${p}"`), p);
  for (const s of Object.values(EMOTION_SUGGESTIONS)) {
    assert.ok(pyWellbeing.includes(`"${s.headline}"`), s.headline);
    for (const [text] of s.items) assert.ok(pyWellbeing.includes(`"${text}"`), text);
  }
});

test("streak counts consecutive days ending today or yesterday", () => {
  const today = new Date(2026, 9, 31);
  const d = (k: number) => localDay(new Date(2026, 9, 31 - k));
  assert.equal(streakDays(new Set([d(0), d(1), d(2)]), today), 3);
  assert.equal(streakDays(new Set([d(1), d(2)]), today), 2); // today not done yet
  assert.equal(streakDays(new Set([d(0), d(2)]), today), 1);
  assert.equal(streakDays(new Set([d(3)]), today), 0);
  assert.equal(streakDays(new Set(), today), 0);
  // across a month boundary
  assert.equal(streakDays(new Set(["2026-11-01", "2026-10-31", "2026-10-30"]), new Date(2026, 10, 1)), 3);
});

test("history stats", () => {
  const entries = [at(0, { detectedEmotion: "Happy", confidence: 0.9 }), at(0, { kind: "checkin", selfReportedMood: "Good" }),
    at(1, { detectedEmotion: "Happy", confidence: 0.5 }), at(1, { detectedEmotion: "Sad", confidence: 0.4 })];
  const s = historyStats(entries);
  assert.deepEqual([s.total, s.today, s.streak, s.detections, s.moodReports], [4, 2, 2, 3, 1]);
  assert.equal(s.dominantExpression, "Happy");
  assert.ok(Math.abs(s.averageConfidence! - 0.6) < 1e-9);
  assert.deepEqual(Object.keys(s.expressionCounts), [...EMOTIONS]);
});

test("insights are labelled and rule based", () => {
  const det = [0, 1, 2, 3].map((i) => at(i, { detectedEmotion: "Neutral", confidence: 0.3 }));
  const moods = [0, 1, 2].map((i) => at(i, { kind: "checkin", selfReportedMood: "Difficult" }));
  const insights = generateInsights([...det, ...moods]);
  assert.ok(insights.every((i) => ["Model signal", "Self-reported mood", "Tip"].includes(i.source)));
  const texts = insights.map((i) => i.text).join(" ");
  assert.ok(texts.includes("Neutral has appeared in 4 of your last 4"));
  assert.ok(texts.includes("low model confidence"));
  assert.ok(texts.includes("talk with someone you trust"));
  assert.deepEqual(generateInsights([]), []);
});

test("time range filter, top factors and session summary", () => {
  const entries = [at(1, { kind: "checkin", selfReportedMood: "Okay", moodFactors: ["Sleep", "Exams"] }),
    at(10, { kind: "checkin", selfReportedMood: "Low", moodFactors: ["Sleep"] })];
  assert.equal(filterSince(entries, 7).length, 1);
  assert.equal(filterSince(entries, null).length, 2);
  assert.deepEqual(topFactors(entries), ["Sleep", "Exams"]);
  const s = summarizeSession([{ emotion: "Sad", confidence: 0.2 }, { emotion: "Happy", confidence: 0.8 }, { emotion: "Happy", confidence: 0.5 }]);
  assert.equal(s.predictions, 3);
  assert.equal(s.dominant, "Happy");
  assert.equal(s.counts.Happy, 2);
  assert.ok(Math.abs(s.averageConfidence! - 0.5) < 1e-9);
});

test("user-facing text never diagnoses", () => {
  const diagnostic = /\byou(?:'re| are)\s+(?:feeling\s+)?(?:stressed|anxious|depressed|sad|angry|happy|afraid|scared|unwell|mentally ill)\b|\byou have (?:anxiety|depression|stress)\b|\bdiagnos(?:e|es|is) (?:your|you)\b/i;
  const web = join(repo, "web/src");
  const files = ["lib/wellbeing.ts", "lib/analytics.ts", "lib/support.ts", "app/(app)/checkin/page.tsx",
    "app/(app)/wellbeing/page.tsx", "app/(app)/dashboard/page.tsx", "app/(app)/history/page.tsx", "app/(app)/tracker/page.tsx",
    "app/(app)/support/page.tsx", "components/Wellbeing.tsx", "components/Support.tsx"];
  for (const f of files) assert.equal(readFileSync(join(web, f), "utf8").match(diagnostic), null, f);
});

test("wellbeing metrics: scores, averages and daily series", () => {
  const e = at(0, { kind: "checkin", selfReportedMood: "Good", energyLevel: 2, stressLevel: 5, sleepQuality: 9 });
  assert.equal(metricScore(e, "mood"), 4);
  assert.equal(metricScore(e, "energyLevel"), 2);
  assert.equal(metricScore(e, "sleepQuality"), null); // out of range is ignored
  assert.equal(metricScore(at(0, { detectedEmotion: "Sad" }), "mood"), null);
  const entries = [e, at(0, { kind: "checkin", selfReportedMood: "Okay", stressLevel: 3 }), at(2, { kind: "checkin", selfReportedMood: "Low" })];
  assert.equal(averageScore(entries, "stressLevel"), 4);
  assert.equal(averageScore([], "mood"), null);
  const series = dailyAverages(entries, "mood");
  assert.equal(series.length, 2);
  assert.ok(series[0].day < series[1].day); // oldest first
  assert.deepEqual([series[1].value, series[1].n], [3.5, 2]);
  assert.equal(wellbeingReports([...entries, at(0, { detectedEmotion: "Happy" })]).length, 3);
});

test("periods, date ranges, day counts and weekdays", () => {
  const entries = [at(1, { kind: "checkin", selfReportedMood: "Good" }), at(9, { kind: "checkin", selfReportedMood: "Low" }),
    at(20, { kind: "checkin", selfReportedMood: "Okay" })];
  assert.equal(previousPeriod(entries, 7).length, 1);
  assert.equal(previousPeriod(entries, 7)[0].selfReportedMood, "Low");
  const d = (k: number) => localDay(new Date(Date.now() - k * 86400_000));
  assert.equal(filterBetween(entries, d(10), d(0)).length, 2);
  assert.equal(filterBetween(entries, "", d(15)).length, 1);
  assert.equal(filterBetween(entries).length, 3);
  const counts = dayCounts(entries, 7);
  assert.equal(counts.length, 7);
  assert.equal(counts.reduce((a, [, n]) => a + n, 0), 1);
  assert.equal(dayCounts(entries, null).length, 3);
  const monday = { id: "w", kind: "checkin" as const, timestamp: new Date(2026, 10, 2, 12).toISOString(), selfReportedMood: "Great" };
  assert.deepEqual(weekdayAverages([monday], "mood"), [5, null, null, null, null, null, null]); // 2 Nov 2026 is a Monday
});

test("tracker insights compare periods without diagnosing", () => {
  const ci = (days: number, mood: string, stress: number) => at(days, { kind: "checkin", selfReportedMood: mood, stressLevel: stress });
  const entries = [ci(0.1, "Great", 4), ci(1, "Good", 5), ci(2, "Good", 2), ci(8, "Low", 2), ci(9, "Low", 2)];
  const texts = trackerInsights(entries, 7).map((i) => i.text);
  assert.ok(texts.some((t) => t.startsWith("Your average self-reported mood was higher than in the previous 7 days")), texts.join("|"));
  assert.ok(texts.some((t) => t.includes("high stress (4–5) on 2 days")), texts.join("|"));
  assert.ok(texts.some((t) => t.includes("checked in on 3 of the last 7 days")), texts.join("|"));
  const low = [0, 1, 2].map((k) => ci(k, "Difficult", 3));
  assert.ok(trackerInsights(low, 7).some((i) => i.source === "Tip" && i.text.includes("professional")));
  assert.deepEqual(trackerInsights([], 7), []);
});

test("history source labels", () => {
  assert.equal(sourceLabel(at(0, { source: "web" })), "Image");
  assert.equal(sourceLabel(at(0, { source: "image" })), "Image");
  assert.equal(sourceLabel(at(0, { source: "webcam" })), "Webcam");
  assert.equal(sourceLabel(at(0, { source: "camera" })), "Webcam");
  assert.equal(sourceLabel(at(0, { kind: "checkin" })), "Check-in");
  assert.equal(sourceLabel(at(0, { kind: "reset" })), "Activity");
});
