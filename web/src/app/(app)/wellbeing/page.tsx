"use client";

// Wellbeing Toolkit: ways to feel better by situation, small resets and eight short activities
// (src/ui/views/toolkit.py). General wellbeing ideas, not treatment.
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ActivityPanel, DistressNote, SuggestionList } from "@/components/Wellbeing";
import { ACTIVITIES, OVERWHELMED_RESETS, SITUATIONS, TOOLKIT_ORDER } from "@/lib/wellbeing";

function Toolkit() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const active = params.get("activity");
  const panel = useRef<HTMLDivElement>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [situation, setSituation] = useState("stressed");
  const sit = SITUATIONS[situation];

  const open = (id: string | null) => router.replace(id ? `${pathname}?activity=${id}` : pathname, { scroll: false });

  useEffect(() => {
    if (active && ACTIVITIES[active]) panel.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [active]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Wellbeing · Toolkit</div>
        <h1 className="title">Ways to <span className="accent">feel better</span></h1>
        <p className="subtitle">Practical, everyday ideas to help you pause, reset and refocus. Pick what fits how you feel.</p>
      </div>

      <div ref={panel} style={{ scrollMarginTop: 80 }}>
        {active && ACTIVITIES[active] && (
          <div style={{ marginBottom: 24 }}><ActivityPanel key={active} id={active} onClose={() => open(null)} /></div>
        )}
      </div>

      <div className="card overwhelmed">
        <div className="eyebrow">Feeling overwhelmed?</div>
        <h2 style={{ fontSize: "1.35rem", margin: "6px 0 4px" }}>If you&apos;re feeling overwhelmed, try one small reset.</h2>
        <p className="muted small">Pick whatever feels doable. This is something you choose — it is never triggered by the model.</p>
        <div className="grid grid-3" style={{ marginTop: 14 }}>
          {OVERWHELMED_RESETS.map((r) => (
            <button key={r.label} className="btn reset-btn" title={r.hint}
                    onClick={() => { if (r.activity) open(r.activity); setToast(`${r.hint}. Take your time.`); }}>
              <span aria-hidden="true">{r.icon}</span> {r.label}
            </button>
          ))}
        </div>
        {toast && <div className="alert alert-info" role="status" style={{ marginTop: 12 }}>💜 {toast}</div>}
      </div>

      <div className="section"><h2>What&apos;s going on?</h2><p>Choose a situation for a few general ideas that often help.</p></div>
      <div className="card">
        <div className="row" role="tablist" aria-label="Situation">
          {Object.entries(SITUATIONS).map(([id, s]) => (
            <button key={id} role="tab" aria-selected={situation === id} aria-controls="situation-panel"
                    className={`chip${situation === id ? " active" : ""}`} onClick={() => setSituation(id)}>
              <span aria-hidden="true">{s.emoji}</span> {s.title}
            </button>
          ))}
        </div>
        <div id="situation-panel" role="tabpanel" style={{ marginTop: 14 }}>
          <div className="card-title">{sit.emoji} {sit.title}</div>
          <p className="muted small" style={{ marginBottom: 4 }}>{sit.intro}</p>
          <SuggestionList items={sit.items} />
        </div>
        <p className="muted small" style={{ marginTop: 10 }}>
          If these feelings last for weeks or get in the way of daily life, <Link href="/support">talking to a professional</Link> can help.
        </p>
      </div>

      <div className="section"><h2>Your toolkit</h2><p>Short guided activities. Each one ends with a quick “How do you feel after this?”.</p></div>
      <div className="grid grid-4">
        {TOOLKIT_ORDER.map((id) => {
          const a = ACTIVITIES[id];
          return (
            <div key={id} className="card hover act-card">
              <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <span className="act-emoji" aria-hidden="true">{a.emoji}</span>
                <span className="chip">⏱ {a.minutes} min</span>
              </div>
              <div className="card-title" style={{ marginTop: 8 }}>{a.title}</div>
              <p className="muted small" style={{ flex: 1, margin: "4px 0 12px" }}>{a.summary}</p>
              <button className="btn btn-sm btn-block" onClick={() => open(id)} aria-label={`Start ${a.title}`}>▶ Start</button>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 24 }}><DistressNote /></div>
      <p className="muted small" style={{ marginTop: 10 }}>These activities are general wellbeing ideas, not medical or psychological advice.</p>
    </>
  );
}

export default function WellbeingPage() {
  return <Suspense fallback={<div className="center"><span className="spinner muted" aria-label="Loading" /></div>}><Toolkit /></Suspense>;
}
