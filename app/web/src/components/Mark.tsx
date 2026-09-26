/** Wordmark glyph: a signal-orange plate with an ink core. */
export function Mark({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden>
      <rect x="0" y="0" width="16" height="16" rx="2" fill="#FF4F00" />
      <rect x="4" y="4" width="8" height="8" rx="0.5" fill="#111111" />
    </svg>
  );
}
