/* Shared dashboard — the same view for everyone (per plan). Delivers the mandatory
   recruitment reporting: the Ascent funnel (current count per stage, with stage-to-
   stage conversion) and the new-recruits trend over time, plus headline stat tiles. */
import { useQuery } from "@tanstack/react-query";
import { api, type DashboardStats, type FunnelResponse } from "../lib/api";
import { STAGES, stageMeta } from "../lib/stages";
import { TrendArea } from "../components/TrendArea";
import styles from "./Dashboard.module.css";

function formatWeek(period: string): string {
  // "2026-W27" -> "W27"
  const m = period.match(/W(\d+)$/);
  return m ? `W${m[1]}` : period;
}

function StatTile({ label, value, suffix, note }: { label: string; value: number | string; suffix?: string; note?: string }) {
  return (
    <div className={`card ${styles.tile}`}>
      <span className="eyebrow">{label}</span>
      <span className={styles.tileValue}>
        {value}
        {suffix && <small> {suffix}</small>}
      </span>
      {note && <span className={styles.tileDelta}>{note}</span>}
    </div>
  );
}

export function Dashboard() {
  const statsQ = useQuery({ queryKey: ["dashboard-stats"], queryFn: () => api.get<DashboardStats>("/dashboard/stats") });
  const funnelQ = useQuery({ queryKey: ["funnel"], queryFn: () => api.get<FunnelResponse>("/analytics/funnel") });

  const stats = statsQ.data;
  const funnel = funnelQ.data;

  // Ascent funnel: count per stage in ascent order, with conversion vs the stage below.
  const countFor = (key: string) => funnel?.stages.find((s) => s.stage === key)?.count ?? 0;
  const maxCount = Math.max(1, ...STAGES.map((s) => countFor(s.key)));
  const commissioned = countFor("commissioned");
  const totalRecruits = stats?.total_recruits ?? funnel?.total ?? 0;
  const commissionRate = totalRecruits > 0 ? Math.round((commissioned / totalRecruits) * 100) : 0;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Detachment overview</h1>
          <p className={styles.subtitle}>Live recruiting pipeline and momentum across Det 695.</p>
        </div>
      </div>

      {/* Stat tiles */}
      <div className={styles.tiles}>
        {statsQ.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <div key={i} className={`${styles.tile} ${styles.skeleton}`} style={{ height: 104 }} />)
        ) : (
          <>
            <StatTile label="Recruits in pipeline" value={totalRecruits} />
            <StatTile label="Commissioned" value={commissioned} note={`${commissionRate}% of pipeline`} />
            <StatTile label="Active cadets" value={stats?.total_cadets ?? 0} />
            <StatTile label="Open follow-ups" value={stats?.open_followups ?? 0} note="needs attention" />
          </>
        )}
      </div>

      {/* Charts */}
      <div className={styles.grid}>
        <section className={`card ${styles.panel}`}>
          <div className={styles.panelHead}>
            <div>
              <h2 className={styles.panelTitle}>The Ascent</h2>
              <span className={styles.panelNote}>Recruits by stage · conversion from the stage below</span>
            </div>
          </div>
          {funnelQ.isLoading ? (
            <div className={styles.skeleton} style={{ flex: 1, minHeight: 260 }} />
          ) : (
            <div className={styles.ascent}>
              {STAGES.map((s, i) => {
                const count = countFor(s.key);
                const below = i > 0 ? countFor(STAGES[i - 1].key) : 0;
                const conv = i > 0 && below > 0 ? Math.round((count / below) * 100) : null;
                const width = Math.max(18, (count / maxCount) * 100);
                const meta = stageMeta(s.key);
                return (
                  <div key={s.key} className={styles.band} title={`${meta.label}: ${count}`}>
                    <div className={styles.bandFill} style={{ width: `${width}%`, background: meta.color }} />
                    <div className={styles.bandContent}>
                      <div className={styles.bandLabel}>
                        <span className={styles.bandName}>{meta.label}</span>
                        <span className={styles.bandBlurb}>{meta.blurb}</span>
                      </div>
                      <div className={styles.bandMetrics}>
                        <span className={styles.bandCount}>{count}</span>
                        <span className={styles.bandConv}>{conv != null ? `${conv}%` : "—"}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section className={`card ${styles.panel}`}>
          <div className={styles.panelHead}>
            <div>
              <h2 className={styles.panelTitle}>New recruits</h2>
              <span className={styles.panelNote}>Entering the pipeline · by week</span>
            </div>
          </div>
          {statsQ.isLoading ? (
            <div className={styles.skeleton} style={{ flex: 1, minHeight: 220 }} />
          ) : (
            <TrendArea points={stats?.recent_trend ?? []} formatLabel={formatWeek} />
          )}
        </section>
      </div>

      {(statsQ.isError || funnelQ.isError) && (
        <div className={styles.empty}>Couldn't load dashboard data. Check that the API is running.</div>
      )}
    </div>
  );
}
