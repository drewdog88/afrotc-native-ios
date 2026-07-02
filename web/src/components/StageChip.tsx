/* A compact, always-legible stage marker: a colored dot (the stage's identity
   color) beside an ink label. Color is never load-bearing — the label is always
   present — so it stays readable in light and dark and for color-vision needs. */
import { stageMeta } from "../lib/stages";
import styles from "./StageChip.module.css";

export function StageChip({ stage, size = "md" }: { stage: string; size?: "sm" | "md" }) {
  const meta = stageMeta(stage);
  return (
    <span className={`${styles.chip} ${size === "sm" ? styles.sm : ""}`}>
      <span className={styles.dot} style={{ background: meta.color }} aria-hidden />
      {meta.label}
    </span>
  );
}
