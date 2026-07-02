/* Single-series area chart for "new recruits over time" — the mandatory
   change-over-time view. One hue (brand blue stroke, sky gradient fill), no legend
   (title names the series), recessive grid, and a crosshair+tooltip on hover per
   the dataviz interaction spec. Pure SVG; no chart dependency. */
import { useMemo, useState } from "react";
import type { TrendPoint } from "../lib/api";
import styles from "../pages/Dashboard.module.css";

interface Props {
  points: TrendPoint[];
  /** Formats the x bucket key (e.g. "2026-W27") for the tooltip/axis. */
  formatLabel?: (period: string) => string;
}

const W = 560;
const H = 220;
const PAD = { top: 16, right: 12, bottom: 26, left: 30 };

export function TrendArea({ points, formatLabel = (p) => p }: Props) {
  const [hover, setHover] = useState<number | null>(null);

  const geo = useMemo(() => {
    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;
    const max = Math.max(1, ...points.map((p) => p.count));
    const n = points.length;
    const x = (i: number) => PAD.left + (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW);
    const y = (v: number) => PAD.top + innerH - (v / max) * innerH;
    const coords = points.map((p, i) => ({ x: x(i), y: y(p.count), ...p }));
    const line = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
    const area =
      coords.length > 0
        ? `${line} L${coords[coords.length - 1].x.toFixed(1)},${(PAD.top + innerH).toFixed(1)} ` +
          `L${coords[0].x.toFixed(1)},${(PAD.top + innerH).toFixed(1)} Z`
        : "";
    // y gridlines at 0, mid, max
    const ticks = [0, Math.round(max / 2), max];
    return { coords, line, area, y, ticks, baseline: PAD.top + innerH };
  }, [points]);

  if (points.length === 0) {
    return <div className={styles.empty}>No stage activity recorded yet.</div>;
  }

  const active = hover != null ? geo.coords[hover] : null;

  return (
    <div className={styles.chartWrap}>
      <svg
        className={styles.svg}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        role="img"
        aria-label="New recruits over time"
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const px = ((e.clientX - rect.left) / rect.width) * W;
          let best = 0;
          let bestD = Infinity;
          geo.coords.forEach((c, i) => {
            const d = Math.abs(c.x - px);
            if (d < bestD) {
              bestD = d;
              best = i;
            }
          });
          setHover(best);
        }}
      >
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--sky)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--sky)" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* recessive gridlines */}
        {geo.ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={geo.y(t)} y2={geo.y(t)} stroke="var(--border)" strokeWidth="1" />
            <text className={styles.axisLabel} x={PAD.left - 6} y={geo.y(t) + 3} textAnchor="end">
              {t}
            </text>
          </g>
        ))}

        <path d={geo.area} fill="url(#trendFill)" />
        <path d={geo.line} fill="none" stroke="var(--brand)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />

        {/* x labels: first, middle, last to avoid crowding */}
        {[0, Math.floor(geo.coords.length / 2), geo.coords.length - 1]
          .filter((i, idx, arr) => arr.indexOf(i) === idx)
          .map((i) => (
            <text key={i} className={styles.axisLabel} x={geo.coords[i].x} y={H - 8} textAnchor="middle">
              {formatLabel(geo.coords[i].period)}
            </text>
          ))}

        {active && (
          <>
            <line x1={active.x} x2={active.x} y1={PAD.top} y2={geo.baseline} stroke="var(--sky)" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx={active.x} cy={active.y} r="5" fill="var(--surface)" stroke="var(--brand)" strokeWidth="2" />
          </>
        )}
      </svg>

      {active && (
        <div className={styles.tooltip} style={{ left: `${(active.x / W) * 100}%`, top: `${(active.y / H) * 100}%` }}>
          {formatLabel(active.period)} · <b>{active.count}</b>
        </div>
      )}
    </div>
  );
}
