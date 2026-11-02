"use client";

// Find Professional Support: urgent contacts, who can help, a directory of verified providers and how to check a
// professional's registration. Nothing here is invented: see src/lib/support.ts and src/data/providers.json.
import { useState } from "react";
import { EmptyState } from "@/components/Emotion";
import { UrgentHelp } from "@/components/Support";
import providerData from "@/data/providers.json";
import { filterProviders, PROVIDER_TYPES, SUPPORT_CHECKED_ON, verifiedProviders, VERIFY_LINKS } from "@/lib/support";

const PROVIDERS = verifiedProviders(providerData.providers);
const SPECIALTIES = [...new Set(PROVIDERS.flatMap((p) => p.specialties))].sort();
const LOCATIONS = [...new Set(PROVIDERS.map((p) => p.city))].sort();

const WHO = [
  { icon: "🩺", title: "Psychiatrist", text: "A medical doctor specialising in mental health. Can diagnose conditions and prescribe medication." },
  { icon: "🧠", title: "Clinical psychologist", text: "Trained in psychological assessment and talking therapies. In India, should be registered with the RCI." },
  { icon: "🤝", title: "Counsellor", text: "Offers support with everyday stress, relationships and study or work pressure. Many colleges have one on campus." },
];

const fmtDate = (d: string) => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

export default function SupportPage() {
  const [location, setLocation] = useState("");
  const [type, setType] = useState("");
  const [specialty, setSpecialty] = useState("");
  const shown = filterProviders(PROVIDERS, { location, type, specialty });
  const filtered = Boolean(location || type || specialty);

  return (
    <>
      <div className="page-head">
        <div className="eyebrow">Support · Professional help</div>
        <h1 className="title">Find <span className="accent">professional support</span></h1>
        <p className="subtitle">Talking to a qualified professional can help with stress, low mood, anxiety or sleep. You don&apos;t
          need to be in crisis to reach out.</p>
      </div>

      <UrgentHelp id="urgent" />

      <div className="section"><h2>Who can help</h2><p>Different professionals offer different kinds of support.</p></div>
      <div className="grid grid-3">
        {WHO.map((w) => (
          <div key={w.title} className="card">
            <div style={{ fontSize: "1.4rem" }} aria-hidden="true">{w.icon}</div>
            <div className="card-title" style={{ marginTop: 4 }}>{w.title}</div>
            <p className="muted small" style={{ marginTop: 2 }}>{w.text}</p>
          </div>
        ))}
      </div>

      <div className="section">
        <h2>Directory</h2>
        <p>Only providers checked against an official public source are listed, each with a link to that source.</p>
      </div>
      <div className="card filters" role="search" aria-label="Filter providers">
        <label className="field"><span>Location</span>
          <input className="input" list="locations" value={location} placeholder="City, state or country"
                 onChange={(e) => setLocation(e.target.value)} />
          <datalist id="locations">{LOCATIONS.map((l) => <option key={l} value={l} />)}</datalist>
        </label>
        <label className="field"><span>Professional type</span>
          <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">All types</option>
            {PROVIDER_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
        </label>
        <label className="field"><span>Specialty</span>
          <select className="input" value={specialty} onChange={(e) => setSpecialty(e.target.value)}>
            <option value="">All specialties</option>
            {SPECIALTIES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
      </div>

      {shown.length ? (
        <div className="grid grid-2" style={{ marginTop: 14 }}>
          {shown.map((p) => (
            <article key={p.id} className="card provider">
              <span className="chip chip-xs">{p.type}</span>
              <h3 className="card-title" style={{ fontSize: "1.05rem", marginTop: 8 }}>{p.name}</h3>
              {p.qualification && <p className="small">{p.qualification}</p>}
              {p.organization && <p className="small">{p.organization}</p>}
              <p className="muted small" style={{ marginTop: 4 }}>📍 {[p.city, p.region, p.country].filter(Boolean).join(", ")}</p>
              {p.specialties.length > 0 && (
                <div className="row" style={{ gap: 6, marginTop: 8 }}>{p.specialties.map((s) => <span key={s} className="chip chip-xs">{s}</span>)}</div>
              )}
              {p.consultation && <p className="small" style={{ marginTop: 8 }}>{p.consultation}</p>}
              <div className="row" style={{ justifyContent: "space-between", marginTop: 12 }}>
                <a href={p.sourceUrl} target="_blank" rel="noopener noreferrer" className="btn btn-sm">Official website ↗</a>
                <span className="muted small">Verified {fmtDate(p.verifiedOn)}</span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div style={{ marginTop: 14 }}>
          <EmptyState icon="🔎" title={filtered ? "No verified providers match these filters" : "No verified providers listed yet"}
                      text="We only list providers checked against an official source. Tele-MANAS (14416) can guide you to services near you, and the registers below help you check any professional you find.">
            {filtered && <button className="btn" onClick={() => { setLocation(""); setType(""); setSpecialty(""); }}>Clear filters</button>}
          </EmptyState>
        </div>
      )}
      <p className="muted small" style={{ marginTop: 10 }}>
        This directory is still small. It doesn&apos;t include individual practitioners yet, because we only add people whose
        details can be confirmed from an official source. Being listed is not an endorsement — confirm current details
        with the provider directly.
      </p>

      <div className="section"><h2>Finding someone near you</h2><p>Good places to start, and how to check a professional is registered.</p></div>
      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">Where to start</div>
          <ul className="list">
            <li>Call <strong>Tele-MANAS (14416)</strong> — trained counsellors can talk with you and refer you to services nearby.</li>
            <li>Ask your college or workplace counselling centre.</li>
            <li>Visit the psychiatry department of a government or teaching hospital in your city.</li>
            <li>Ask your family doctor (GP) for a referral.</li>
          </ul>
        </div>
        <div className="card">
          <div className="card-title">Check a professional&apos;s registration</div>
          {VERIFY_LINKS.map((v) => (
            <div key={v.title} style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 600 }}>{v.title}</div>
              <p className="muted small">{v.text}</p>
              <a href={v.url} target="_blank" rel="noopener noreferrer" className="small">{v.label} ↗</a>
            </div>
          ))}
        </div>
      </div>

      <p className="muted small" style={{ marginTop: 24 }}>
        EmotionSense reads facial expressions and can&apos;t detect or diagnose any mental-health condition. Contacts and links
        on this page were last checked on {fmtDate(SUPPORT_CHECKED_ON)}.
      </p>
    </>
  );
}
