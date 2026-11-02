"use client";

// Daily Check-In: self-reported mood, optional energy / stress / sleep ratings, factors and a written reflection
// (src/ui/views/checkin.py; the ratings are web-only extra fields the Streamlit app ignores).
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { DistressNote, SavedMessage, ScalePicker, SuggestionList } from "@/components/Wellbeing";
import { useAuth } from "@/lib/auth";
import { newEntry, saveEntry } from "@/lib/history";
import { MOOD_FACTORS, MOOD_SUGGESTIONS, MOODS, SCALES, type ScaleKey } from "@/lib/wellbeing";

export default function CheckInPage() {
  const { user } = useAuth();
  const [mood, setMood] = useState<string | null>(null);
  const [factors, setFactors] = useState<string[]>([]);
  const [ratings, setRatings] = useState<Partial<Record<ScaleKey, number>>>({});
  const [note, setNote] = useState("");
  const [keepNote, setKeepNote] = useState(true);
  const [saving, setSaving] = useState(false);
  const [warn, setWarn] = useState(false);
  const [saved, setSaved] = useState<{ mood: string; cloud: boolean } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!mood) return setWarn(true);
    if (!user) return;
    setSaving(true);
    const cloud = await saveEntry(user.uid, newEntry("checkin", {
      selfReportedMood: mood, moodFactors: factors, ...ratings, journalText: keepNote ? note.trim() : undefined,
    }));
    setSaved({ mood, cloud });
    setMood(null); // the form clears after saving, like the Streamlit form
    setFactors([]);
    setRatings({});
    setNote("");
    setSaving(false);
  }

  const toggle = (f: string) => setFactors(factors.includes(f) ? factors.filter((x) => x !== f) : [...factors, f]);

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Reflect · Daily check-in</div>
        <h1 className="title">How are you feeling <span className="accent">right now?</span></h1>
        <p className="subtitle">A minute to notice how you&apos;re doing, in your own words.</p>
      </div>

      <div className="split wide">
        <form onSubmit={submit} className="stack">
          <h3 className="form-h">Pick the card that fits best</h3>
          <p className="muted small" style={{ marginTop: -4 }}>Recorded for {new Date().toLocaleString(undefined, { weekday: "long", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</p>
          <div className="mood-grid" role="radiogroup" aria-label="Mood">
            {Object.entries(MOODS).map(([m, icon]) => (
              <button type="button" key={m} role="radio" aria-checked={mood === m} className={`mood-card${mood === m ? " active" : ""}`}
                      onClick={() => { setMood(m); setWarn(false); setSaved(null); }}>
                <span className="mood-emoji" aria-hidden="true">{icon}</span>{m}
              </button>
            ))}
          </div>
          <h3 className="form-h">A few quick ratings</h3>
          <div className="card stack" style={{ padding: "14px 16px" }}>
            {SCALES.map((sc) => (
              <ScalePicker key={sc.key} scale={sc} value={ratings[sc.key]}
                           onChange={(v) => { setRatings({ ...ratings, [sc.key]: v }); setSaved(null); }} />
            ))}
          </div>
          <h3 className="form-h">What has been affecting you today?</h3>
          <div className="row" role="group" aria-label="Factors">
            {MOOD_FACTORS.map((f) => (
              <button type="button" key={f} aria-pressed={factors.includes(f)} className={`chip${factors.includes(f) ? " active" : ""}`}
                      onClick={() => toggle(f)}>{f}</button>
            ))}
          </div>
          <h3 className="form-h">Want to put it into words?</h3>
          <textarea className="input" rows={7} value={note} onChange={(e) => setNote(e.target.value)} aria-label="Note"
                    placeholder="Optional — what's on your mind today?" />
          <label className="check">
            <input type="checkbox" checked={keepNote} onChange={(e) => setKeepNote(e.target.checked)} />
            Save my note with this check-in
          </label>
          <button type="submit" className="btn btn-primary btn-block" disabled={saving}>{saving ? "Saving…" : "✓ Save check-in"}</button>
          {warn && <div className="alert alert-warning" role="alert">Pick how you&apos;re feeling to save a check-in.</div>}
          {saved && (
            <SavedMessage cloud={saved.cloud}
                          text="Check-in saved ✨ Taking a minute to reflect is already a good step." />
          )}
        </form>

        <div className="stack">
          {saved ? (
            <>
              <div className="section" style={{ marginTop: 0 }}>
                <h2>A small next step</h2><p>You checked in as {MOODS[saved.mood]} {saved.mood}.</p>
              </div>
              <div className="card"><SuggestionList items={[MOOD_SUGGESTIONS[saved.mood]]} compact /></div>
              <Link href="/tracker" className="btn btn-block">See your wellbeing trends →</Link>
              {(saved.mood === "Low" || saved.mood === "Difficult") && <DistressNote />}
            </>
          ) : (
            <div className="card empty">
              <div className="icon" aria-hidden="true">🌤️</div>
              <h3>No right or wrong answer</h3>
              <p className="small">Your check-in is about how you see your day — the model isn&apos;t involved.</p>
            </div>
          )}
          <div className="card">
            <div className="stat-label">🔒 Your data</div>
            <p className="muted small" style={{ marginTop: 4 }}>
              Only your mood, your ratings, the factors you pick, and (if you choose) your note are saved — privately, in your own
              account. This is self-reported and is never combined into a diagnosis.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
