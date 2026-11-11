export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="6" fill="rgb(var(--accent))" />
        <path d="M9 8v16M9 16h9M18 8v16M22 12h4M24 12v12" stroke="rgb(var(--surface))" strokeWidth="2.6" strokeLinecap="round" />
      </svg>
      <span className="text-md font-semibold tracking-tight text-ink">HireTrack</span>
    </div>
  )
}
