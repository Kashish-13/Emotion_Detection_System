// Unit tests for the analytics and wellbeing ports (same cases as tests/test_wellbeing.py), plus cross-checks
// against src/wellbeing.py so the web and Streamlit content can't silently drift apart. Run: npm test
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { filterSince, generateInsights, historyStats, localDay, streakDays, summarizeSession, topFactors } from "./analytics.ts";
import { EMOTIONS } from "./emotion/core.ts";
import type { HistoryEntry } from "./history";
import {
  ACTIVITIES, EMOTION_SUGGESTIONS, JOURNAL_PROMPTS, MOOD_FACTORS, MOOD_SCORE, MOOD_SUGGESTIONS, MOODS, OVERWHELMED_RESETS,
  suggestionsFor, TOOLKIT_ORDER,
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
  const files = ["lib/wellbeing.ts", "lib/analytics.ts", "app/(app)/checkin/page.tsx", "app/(app)/wellbeing/page.tsx",
    "app/(app)/dashboard/page.tsx", "app/(app)/history/page.tsx", "components/Wellbeing.tsx"];
  for (const f of files) assert.equal(readFileSync(join(web, f), "utf8").match(diagnostic), null, f);
});
