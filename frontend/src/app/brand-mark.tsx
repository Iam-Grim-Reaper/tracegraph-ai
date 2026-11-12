/** Small geometric mark: a path with three documented points. */
export function BrandMark({ className = "" }: { className?: string }) {
  return (
    <svg className={`brand-mark ${className}`} viewBox="0 0 32 32" fill="none" aria-hidden="true" focusable="false">
      <path d="M6 8H17V17H26" stroke="currentColor" strokeWidth="1.65" strokeLinejoin="miter" />
      <path d="M6 8V24H16" stroke="currentColor" strokeWidth="1.65" strokeLinejoin="miter" />
      <rect x="3.5" y="5.5" width="5" height="5" fill="currentColor" />
      <rect x="23.5" y="14.5" width="5" height="5" fill="currentColor" />
      <rect x="13.5" y="21.5" width="5" height="5" fill="currentColor" />
    </svg>
  );
}
