/* Det 695 mark: three ascending chevrons (the ascent motif) rising toward a
   beacon point. Used in the rail header and on the login screen. */
export function Insignia({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <path d="M20 3 L33 13 L27 13 L20 8 L13 13 L7 13 Z" fill="var(--accent)" />
      <path d="M20 14 L33 24 L27 24 L20 19 L13 24 L7 24 Z" fill="var(--brand)" opacity="0.85" />
      <path d="M20 25 L33 35 L27 35 L20 30 L13 35 L7 35 Z" fill="var(--brand)" opacity="0.55" />
    </svg>
  );
}
