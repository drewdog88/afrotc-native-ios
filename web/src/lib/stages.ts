/* Recruitment pipeline as an ASCENT — each stage is an altitude band the recruit
   climbs from first contact to commissioning. Order, labels, and colors here are
   the single source of truth for the funnel viz, trend legend, and stage chips. */

export interface StageMeta {
  key: string;
  label: string;
  /** Short label for tight spaces (chips, axis). */
  short: string;
  color: string;
  /** One-line description of what this altitude band means. */
  blurb: string;
}

export const STAGES: StageMeta[] = [
  { key: "lead", label: "Lead", short: "Lead", color: "var(--stage-lead)", blurb: "On the radar — not yet contacted" },
  { key: "contacted", label: "Contacted", short: "Contact", color: "var(--stage-contacted)", blurb: "First conversation made" },
  { key: "applied", label: "Applied", short: "Applied", color: "var(--stage-applied)", blurb: "Application in motion" },
  { key: "enrolled", label: "Enrolled", short: "Enrolled", color: "var(--stage-enrolled)", blurb: "Enrolled in the program" },
  { key: "commissioned", label: "Commissioned", short: "Comm.", color: "var(--stage-commissioned)", blurb: "Reached the apex" },
];

export const DECLINED: StageMeta = {
  key: "declined",
  label: "Declined",
  short: "Declined",
  color: "var(--stage-declined)",
  blurb: "Left the pipeline",
};

const BY_KEY: Record<string, StageMeta> = Object.fromEntries(
  [...STAGES, DECLINED].map((s) => [s.key, s]),
);

export function stageMeta(key: string): StageMeta {
  return BY_KEY[key] ?? { key, label: key, short: key, color: "var(--muted)", blurb: "" };
}
