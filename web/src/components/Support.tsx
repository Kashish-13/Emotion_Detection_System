// "Need immediate help?": verified urgent-support contacts (src/lib/support.ts). Shown because the user looks for
// it, never triggered by the model — a facial expression can't tell whether someone is safe.
import { INTERNATIONAL_DIRECTORY, URGENT_INDIA } from "@/lib/support";

const tel = (n: string) => `tel:${n.replace(/[^\d+]/g, "")}`;

export function UrgentHelp({ id }: { id?: string }) {
  return (
    <section id={id} className="card help-card" aria-labelledby="urgent-h" style={{ scrollMarginTop: 80 }}>
      <div className="eyebrow">Need immediate help?</div>
      <h2 id="urgent-h" style={{ fontSize: "1.2rem", margin: "6px 0 4px" }}>You don&apos;t have to handle it alone.</h2>
      <p className="muted small">
        EmotionSense is not an emergency or medical service, and it can&apos;t tell whether someone is safe. If you or someone
        else might be in danger, contact emergency services now.
      </p>
      <div className="grid grid-2" style={{ marginTop: 14 }}>
        {URGENT_INDIA.map((h) => (
          <div key={h.name} className="resource">
            <div className="card-title">{h.name}</div>
            <div className="row" style={{ margin: "6px 0" }}>
              {h.numbers.map((n) => <a key={n} href={tel(n)} className="btn btn-sm tel">📞 {n}</a>)}
            </div>
            <p className="muted small">{h.detail}</p>
            <a href={h.sourceUrl} target="_blank" rel="noopener noreferrer" className="small">Source: {h.sourceLabel} ↗</a>
          </div>
        ))}
      </div>
      <p className="small" style={{ marginTop: 12 }}>
        {INTERNATIONAL_DIRECTORY.detail}{" "}
        <a href={INTERNATIONAL_DIRECTORY.url} target="_blank" rel="noopener noreferrer">{INTERNATIONAL_DIRECTORY.name} ↗</a>
        {" "}Or call your local emergency number.
      </p>
    </section>
  );
}
