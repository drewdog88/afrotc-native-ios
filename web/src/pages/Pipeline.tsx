/* Pipeline analytics — the recruitment-change-over-time deep dive. A Week/Month
   interval toggle drives a hand-rolled multi-series SVG trend chart: one thin line
   per stage in its identity color (from stageMeta), a single shared y-axis,
   recessive gridlines, a crosshair + hover tooltip that reads every series at the
   hovered period, and an always-on legend. Below the chart, the current funnel
   snapshot with stage-to-stage conversion. No charting library — pure SVG. */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { STAGES, stageMeta } from "../lib/stages";
import type { components } from "../api/schema";
import styles from "./Pipeline.module.css";

type TrendsResponse = components["schemas"]["TrendsResponse"];
type FunnelResponse = components["schemas"]["FunnelResponse"];

type Interval = "week" | "month";

const W = 700;
const H = 300;
const PAD = { top: 18, right: 18, bottom: 30, left: 36 };

function formatPeriod(period: string, interval: Interval): string {
  if (interval === "week") {
    const m = period.match(/W(\d+)$/);
    return m ? `W${m[1]}` : period;
  }
  // "2026-07" -> "Jul"
  const m = period.match(/^(\d{4})-(\d{2})/);
  if (m) {
    const d = new Date(Number(m[1]), Number(m[2]) - 1, 1);
    if (!Number.isNaN(d.getTime())) return d.toLocaleString("en-US", { month: "short" });
  }
  return period;
}

interface SeriesGeo {
  key: string;
  label: string;
  color: string;
  line: string;
  coords: { x: number; y: number; count: number; period: string }[];
  /** count keyed by period, for the hover tooltip. */
  byPeriod: Map<string, number>;
  last: { x: number; y: number } | null;
}

export function Pipeline() {
  const [interval, setInterval] = useState<Interval>("week");
  const [hover, setHover] = useState<number | null>(null);

  const trendsQ = useQuery({
    queryKey: ["trends", interval],
    queryFn: () => api.get<TrendsResponse>(`/analytics/trends?metric=all&interval=${interval}`),
  });
  const funnelQ = useQuery({
    queryKey: ["funnel"],
    queryFn: () => api.get<FunnelResponse>("/analytics/funnel"),
  });

  const series = trendsQ.data?.series ?? [];

  // Union of all periods across series, in chronological (lexical) order.
  const periods = useMemo(() => {
    const set = new Set<string>();
    for (const s of series) for (const p of s.points) set.add(p.period);
    return [...set].sort();
  }, [series]);

  const hasData = periods.length > 0 && series.some((s) => s.points.length > 0);

  const geo = useMemo(() => {
    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;
    const n = periods.length;
    const x = (i: number) => PAD.left + (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW);

    // Cumulative reach: for each stage, the running total of recruits that have
    // entered it by each period. This is a monotonic level (it never falls), so
    // it reads as pipeline momentum instead of the sawtooth you get from plotting
    // raw per-period transition counts. Every series carries a value at every
    // period on the shared axis, so the lines are continuous edge-to-edge.
    const cumulative = series.map((s) => {
      const perPeriod = new Map(s.points.map((p) => [p.period, p.count]));
      let running = 0;
      const values = periods.map((p) => {
        running += perPeriod.get(p) ?? 0;
        return running;
      });
      return { stage: s.stage, values };
    });

    const max = Math.max(1, ...cumulative.flatMap((c) => c.values));
    const y = (v: number) => PAD.top + innerH - (v / max) * innerH;

    const seriesGeo: SeriesGeo[] = cumulative.map((c) => {
      const meta = stageMeta(c.stage);
      const byPeriod = new Map<string, number>();
      const coords = c.values.map((v, i) => {
        byPeriod.set(periods[i], v);
        return { x: x(i), y: y(v), count: v, period: periods[i] };
      });
      const line = coords
        .map((pt, i) => `${i === 0 ? "M" : "L"}${pt.x.toFixed(1)},${pt.y.toFixed(1)}`)
        .join(" ");
      return {
        key: c.stage,
        label: meta.label,
        color: meta.color,
        line,
        coords,
        byPeriod,
        last: coords.length > 0 ? coords[coords.length - 1] : null,
      };
    });

    // y gridlines at 0, mid, max (integer-friendly).
    const ticks = [0, Math.round(max / 2), max].filter((t, i, arr) => arr.indexOf(t) === i);
    return { seriesGeo, x, y, ticks, baseline: PAD.top + innerH, innerH };
  }, [series, periods]);

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Pipeline</h1>
          <p className={styles.subtitle}>
            How the recruiting pipeline is building over time — cumulative recruits to reach each stage by {interval === "week" ? "week" : "month"}.
          </p>
        </div>
        <div className={styles.toggle} role="group" aria-label="Trend interval">
          {(["week", "month"] as Interval[]).map((iv) => (
            <button
              key={iv}
              type="button"
              className={`${styles.toggleBtn} ${interval === iv ? styles.toggleBtnActive : ""}`}
              aria-pressed={interval === iv}
              onClick={() => {
                setInterval(iv);
                setHover(null);
              }}
            >
              {iv === "week" ? "Week" : "Month"}
            </button>
          ))}
        </div>
      </div>

      <section className={`card ${styles.panel}`}>
        <div className={styles.panelHead}>
          <div>
            <h2 className={styles.panelTitle}>Cumulative reach by stage</h2>
            <span className={styles.panelNote}>Running total of recruits to reach each stage · one shared scale</span>
          </div>
        </div>

        {trendsQ.isLoading ? (
          <div className={styles.skeleton} style={{ minHeight: 300 }} />
        ) : trendsQ.isError ? (
          <div className={styles.empty}>Couldn't load trend data. Check that the API is running.</div>
        ) : !hasData ? (
          <div className={styles.empty}>No trend data yet. Advance recruits through stages to build the trend.</div>
        ) : (
          <>
            <div className={styles.chartWrap}>
              <svg
                className={styles.svg}
                viewBox={`0 0 ${W} ${H}`}
                preserveAspectRatio="none"
                role="img"
                aria-label={`Cumulative recruits to reach each stage by ${interval}`}
                onMouseLeave={() => setHover(null)}
                onMouseMove={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const mx = ((e.clientX - rect.left) / rect.width) * W;
                  let best = 0;
                  let bestD = Infinity;
                  periods.forEach((_, i) => {
                    const d = Math.abs(geo.x(i) - mx);
                    if (d < bestD) {
                      bestD = d;
                      best = i;
                    }
                  });
                  setHover(best);
                }}
              >
                {/* recessive gridlines + y labels */}
                {geo.ticks.map((t) => (
                  <g key={t}>
                    <line
                      x1={PAD.left}
                      x2={W - PAD.right}
                      y1={geo.y(t)}
                      y2={geo.y(t)}
                      stroke="var(--border)"
                      strokeWidth="1"
                    />
                    <text className={styles.axisLabel} x={PAD.left - 6} y={geo.y(t) + 3} textAnchor="end">
                      {t}
                    </text>
                  </g>
                ))}

                {/* crosshair behind the lines */}
                {hover != null && (
                  <line
                    x1={geo.x(hover)}
                    x2={geo.x(hover)}
                    y1={PAD.top}
                    y2={geo.baseline}
                    stroke="var(--muted)"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                  />
                )}

                {/* one thin line per stage */}
                {geo.seriesGeo.map((s) => (
                  <path
                    key={s.key}
                    d={s.line}
                    fill="none"
                    stroke={s.color}
                    strokeWidth="2"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    opacity={hover == null ? 1 : 0.9}
                  />
                ))}

                {/* Identity comes from the always-on legend + hover tooltip below.
                   With 6 stages, direct end-labels collide, so we don't draw them. */}

                {/* hover markers */}
                {hover != null &&
                  geo.seriesGeo.map((s) => {
                    const period = periods[hover];
                    const c = s.coords.find((p) => p.period === period);
                    if (!c) return null;
                    return (
                      <circle
                        key={s.key}
                        cx={c.x}
                        cy={c.y}
                        r="4"
                        fill="var(--surface)"
                        stroke={s.color}
                        strokeWidth="2"
                      />
                    );
                  })}

                {/* x labels: first, middle, last to avoid crowding */}
                {[0, Math.floor((periods.length - 1) / 2), periods.length - 1]
                  .filter((i, idx, arr) => arr.indexOf(i) === idx && i >= 0)
                  .map((i) => (
                    <text key={i} className={styles.axisLabel} x={geo.x(i)} y={H - 8} textAnchor="middle">
                      {formatPeriod(periods[i], interval)}
                    </text>
                  ))}
              </svg>

              {hover != null && (
                <div
                  className={styles.tooltip}
                  style={{
                    left: `${(geo.x(hover) / W) * 100}%`,
                    top: `${(PAD.top / H) * 100}%`,
                  }}
                >
                  <div className={styles.tooltipHead}>{formatPeriod(periods[hover], interval)}</div>
                  {geo.seriesGeo.map((s) => (
                    <div key={s.key} className={styles.tooltipRow}>
                      <span className={styles.tooltipDot} style={{ background: s.color }} aria-hidden />
                      <span className={styles.tooltipName}>{s.label}</span>
                      <b className={styles.tooltipVal}>{s.byPeriod.get(periods[hover]) ?? 0}</b>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* always render a legend for >= 2 series */}
            {geo.seriesGeo.length >= 2 && (
              <ul className={styles.legend}>
                {geo.seriesGeo.map((s) => (
                  <li key={s.key} className={styles.legendItem}>
                    <span className={styles.legendDot} style={{ background: s.color }} aria-hidden />
                    {s.label}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <section className={`card ${styles.panel}`}>
        <div className={styles.panelHead}>
          <div>
            <h2 className={styles.panelTitle}>Stage conversion</h2>
            <span className={styles.panelNote}>Current count per stage · share advancing from the stage below</span>
          </div>
        </div>
        {funnelQ.isLoading ? (
          <div className={styles.skeleton} style={{ minHeight: 220 }} />
        ) : funnelQ.isError ? (
          <div className={styles.empty}>Couldn't load funnel data. Check that the API is running.</div>
        ) : (
          <ConversionSummary funnel={funnelQ.data} />
        )}
      </section>
    </div>
  );
}

function ConversionSummary({ funnel }: { funnel: FunnelResponse | undefined }) {
  const countFor = (key: string) => funnel?.stages.find((s) => s.stage === key)?.count ?? 0;
  const total = funnel?.total ?? 0;

  if (total === 0) {
    return <div className={styles.empty}>No recruits in the pipeline yet.</div>;
  }

  return (
    <table className={styles.convTable}>
      <thead>
        <tr>
          <th>Stage</th>
          <th className={styles.numCol}>Count</th>
          <th className={styles.numCol}>Conversion</th>
        </tr>
      </thead>
      <tbody>
        {STAGES.map((s, i) => {
          const count = countFor(s.key);
          const below = i > 0 ? countFor(STAGES[i - 1].key) : 0;
          const conv = i > 0 && below > 0 ? Math.round((count / below) * 100) : null;
          const meta = stageMeta(s.key);
          return (
            <tr key={s.key}>
              <td>
                <span className={styles.convStage}>
                  <span className={styles.convDot} style={{ background: meta.color }} aria-hidden />
                  <span>
                    <span className={styles.convName}>{meta.label}</span>
                    <span className={styles.convBlurb}>{meta.blurb}</span>
                  </span>
                </span>
              </td>
              <td className={`${styles.numCol} ${styles.convCount}`}>{count}</td>
              <td className={`${styles.numCol} ${styles.convPct}`}>
                {conv != null ? `${conv}%` : "—"}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
