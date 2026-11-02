"use client";

// Small dependency-free SVG charts for History & Insights (the Streamlit app's Altair charts).
// One y-axis per chart, recessive grid, categories always labelled by name (never colour alone),
// and a hover/focus tooltip on every mark.
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

const PAD = { top: 10, right: 14, bottom: 26 };

function useWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(560);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(240, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return { ref, width };
}

type Tip = { x: number; y: number; text: ReactNode } | null;

function ChartFrame({ title, caption, children, tip, height, frameRef }:
  { title: string; caption?: string; children: ReactNode; tip: Tip; height: number; frameRef: React.Ref<HTMLDivElement> }) {
  return (
    <div className="chart">
      <div className="chart-title">{title}</div>
      <div ref={frameRef} style={{ position: "relative", height }}>
        {children}
        {tip && <div className="chart-tip" style={{ left: tip.x, top: tip.y }} role="tooltip">{tip.text}</div>}
      </div>
      {caption && <p className="muted small" style={{ marginTop: 6 }}>{caption}</p>}
    </div>
  );
}

const dayFmt = (t: number) => new Date(t).toLocaleDateString(undefined, { day: "2-digit", month: "short" });

function timeTicks(min: number, max: number, width: number): number[] {
  const n = Math.max(2, Math.min(6, Math.floor(width / 110)));
  if (max <= min) return [min];
  return Array.from({ length: n }, (_, i) => min + ((max - min) * i) / (n - 1));
}

/** Horizontal count bars in a fixed category order. */
export function CountBars({ title, items, max: fixedMax, format = String, caption }: {
  title: string; items: { key: string; label: ReactNode; color: string; value: number }[];
  max?: number; format?: (v: number) => string; caption?: string;
}) {
  const max = fixedMax ?? Math.max(1, ...items.map((i) => i.value));
  return (
    <div className="chart">
      <div className="chart-title">{title}</div>
      {items.map((i) => (
        <div key={i.key} className="bar-row" style={{ "--c": i.color } as CSSProperties} title={`${i.key}: ${format(i.value)}`}>
          <div className="bar-name">{i.label}</div>
          <div className="bar-track"><div className="bar-fill" style={{ width: `${(i.value / max) * 100}%` }} /></div>
          <div className="bar-value">{format(i.value)}</div>
        </div>
      ))}
      {caption && <p className="muted small" style={{ marginTop: 6 }}>{caption}</p>}
    </div>
  );
}

export type Point = { t: number; y: number; color: string; tip: ReactNode };

/** Points over time on one y-axis: a line (numeric y) or dots (categorical y). */
export function TimeChart({ title, caption, points, yMin, yMax, yTicks, labelWidth = 44, line = false, color = "var(--primary)",
  refs = [], height = 210 }: {
  title: string; caption?: string; points: Point[]; yMin: number; yMax: number; yTicks: { v: number; label: string }[];
  labelWidth?: number; line?: boolean; color?: string; refs?: { v: number; label: string }[]; height?: number;
}) {
  const { ref, width } = useWidth();
  const [tip, setTip] = useState<Tip>(null);
  const sorted = [...points].sort((a, b) => a.t - b.t);
  const tMin = sorted[0]?.t ?? 0;
  const tMax = sorted.at(-1)?.t ?? 1;
  const span = tMax - tMin || 3600_000;
  const left = labelWidth;
  const x = (t: number) => left + 8 + ((t - (tMax === tMin ? tMin - span / 2 : tMin)) / span) * (width - left - 8 - PAD.right - 8);
  const y = (v: number) => PAD.top + (1 - (v - yMin) / (yMax - yMin || 1)) * (height - PAD.top - PAD.bottom);
  const path = sorted.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.y).toFixed(1)}`).join("");
  return (
    <ChartFrame title={title} caption={caption} tip={tip} height={height} frameRef={ref}>
      <svg width={width} height={height} role="img" aria-label={title} onMouseLeave={() => setTip(null)}>
        {yTicks.map((tk) => (
          <g key={tk.v}>
            <line x1={left} x2={width - PAD.right} y1={y(tk.v)} y2={y(tk.v)} className="chart-grid" />
            <text x={left - 6} y={y(tk.v)} className="chart-axis" textAnchor="end" dominantBaseline="middle">{tk.label}</text>
          </g>
        ))}
        {refs.map((r) => (
          <line key={r.v} x1={left} x2={width - PAD.right} y1={y(r.v)} y2={y(r.v)} className="chart-ref"><title>{r.label}</title></line>
        ))}
        {timeTicks(tMin, tMax, width - left).map((t) => (
          <text key={t} x={x(t)} y={height - 6} className="chart-axis" textAnchor="middle">{dayFmt(t)}</text>
        ))}
        {line && sorted.length > 1 && <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />}
        {sorted.map((p, i) => (
          <g key={i} tabIndex={0} className="chart-mark"
             onMouseEnter={() => setTip({ x: x(p.t), y: y(p.y), text: p.tip })}
             onFocus={() => setTip({ x: x(p.t), y: y(p.y), text: p.tip })} onBlur={() => setTip(null)}>
            <circle cx={x(p.t)} cy={y(p.y)} r={12} fill="transparent" />
            <circle cx={x(p.t)} cy={y(p.y)} r={line ? 4.5 : 6} fill={p.color} stroke="var(--surface)" strokeWidth={2} />
          </g>
        ))}
      </svg>
    </ChartFrame>
  );
}

/** Entries per local day as columns. days: [["YYYY-MM-DD", count], ...] in date order. */
export function DayColumns({ title, days, height = 180 }: { title: string; days: [string, number][]; height?: number }) {
  const { ref, width } = useWidth();
  const [tip, setTip] = useState<Tip>(null);
  const max = Math.max(1, ...days.map(([, n]) => n));
  const left = 30;
  const plotW = width - left - PAD.right;
  const slot = plotW / Math.max(days.length, 1);
  const barW = Math.max(4, Math.min(28, slot - 2));
  const y = (v: number) => PAD.top + (1 - v / max) * (height - PAD.top - PAD.bottom);
  const ticks = [...new Set([0, Math.round(max / 2), max])];
  const every = Math.ceil(days.length / Math.max(1, Math.floor(plotW / 60)));
  const label = (d: string) => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { day: "2-digit", month: "short" });
  return (
    <ChartFrame title={title} tip={tip} height={height} frameRef={ref}>
      <svg width={width} height={height} role="img" aria-label={title} onMouseLeave={() => setTip(null)}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={left} x2={width - PAD.right} y1={y(v)} y2={y(v)} className="chart-grid" />
            <text x={left - 6} y={y(v)} className="chart-axis" textAnchor="end" dominantBaseline="middle">{v}</text>
          </g>
        ))}
        {days.map(([d, n], i) => {
          const cx = left + slot * i + slot / 2;
          const show = () => setTip({ x: cx, y: y(n), text: <><strong>{label(d)}</strong> · {n} entr{n === 1 ? "y" : "ies"}</> });
          return (
            <g key={d} tabIndex={0} className="chart-mark" onMouseEnter={show} onFocus={show} onBlur={() => setTip(null)}>
              <rect x={cx - slot / 2} y={PAD.top} width={slot} height={height - PAD.top - PAD.bottom} fill="transparent" />
              <path d={`M${cx - barW / 2},${y(0)}V${y(n) + 3}q0,-3 3,-3h${barW - 6}q3,0 3,3V${y(0)}Z`} fill="var(--primary)" />
              {i % every === 0 && <text x={cx} y={height - 6} className="chart-axis" textAnchor="middle">{label(d)}</text>}
            </g>
          );
        })}
      </svg>
    </ChartFrame>
  );
}
