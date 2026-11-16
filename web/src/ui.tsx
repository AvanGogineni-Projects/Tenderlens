import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { Award } from './api'
import { cpvName, date, eur, FRAMEWORK, monthsUntil, tedUrl } from './labels'

export function Wordmark() {
  return (
    <Link to="/" className="flex items-center gap-2.5 font-display text-[1.05rem] font-semibold tracking-tight text-ink">
      <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
        <circle cx="14" cy="14" r="8" fill="none" stroke="var(--signal)" strokeWidth="3" />
        <path d="M20 20l7 7" stroke="var(--signal)" strokeWidth="3" strokeLinecap="round" />
      </svg>
      Tenderlens
    </Link>
  )
}

export function ThemeToggle() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme ?? '')
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme
    try { if (theme) localStorage.setItem('tenderlens_theme', theme) } catch { /* private mode */ }
  }, [theme])
  const dark = theme ? theme === 'dark' : !window.matchMedia('(prefers-color-scheme: light)').matches
  return (
    <button onClick={() => setTheme(dark ? 'light' : 'dark')} className="label rounded-md border border-line px-2.5 py-1.5 hover:text-ink"
      aria-label={`Switch to ${dark ? 'light' : 'dark'} theme`}>
      {dark ? 'Light' : 'Dark'}
    </button>
  )
}

export function Stat({ label, value, accent }: { label: string; value: ReactNode; accent?: 'signal' | 'amber' }) {
  return (
    <div className="border-l border-line pl-4">
      <div className="label">{label}</div>
      <div className={`num mt-1 text-2xl ${accent === 'signal' ? 'text-signal' : accent === 'amber' ? 'text-amber' : 'text-ink'}`}>{value}</div>
    </div>
  )
}

export function Panel({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-panel">
      <header className="flex items-baseline justify-between gap-4 border-b border-line px-5 py-3">
        <h2 className="label !text-ink">{title}</h2>
        {aside && <div className="label">{aside}</div>}
      </header>
      <div className="p-5">{children}</div>
    </section>
  )
}

/** Horizontal share bars: who has how much of something. */
export function Bars({ rows }: { rows: { key: string; label: ReactNode; value: number; text: string; to?: string }[] }) {
  const max = Math.max(...rows.map((r) => r.value), 1)
  return (
    <ol className="space-y-2.5">
      {rows.map((r) => (
        <li key={r.key}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            {r.to ? <Link to={r.to} className="truncate hover:text-signal">{r.label}</Link> : <span className="truncate">{r.label}</span>}
            <span className="num shrink-0 text-muted">{r.text}</span>
          </div>
          <div className="mt-1 h-1.5 rounded-full bg-raised">
            <div className="h-1.5 rounded-full bg-amber" style={{ width: `${Math.max(2, (r.value / max) * 100)}%` }} />
          </div>
        </li>
      ))}
    </ol>
  )
}

function EndsIn({ d }: { d: string | null }) {
  if (!d) return <span className="text-muted">—</span>
  const m = monthsUntil(d)
  if (m < 0) return <span className="num text-muted">{date(d)}</span>
  return (
    <span className="inline-flex items-center gap-2">
      <span className={`num rounded px-1.5 py-0.5 text-xs ${m <= 3 ? 'bg-signal text-on-signal' : 'border border-signal/50 text-signal'}`}>
        {m === 0 ? 'this month' : `${m} mo`}
      </span>
      <span className="num text-muted">{date(d)}</span>
    </span>
  )
}

/** Contract rows: used for award history and expiring contracts. */
export function AwardTable({ awards, show, empty }: { awards: Award[]; show: 'buyer' | 'supplier' | 'both'; empty: string }) {
  if (!awards.length) return <p className="text-sm text-muted">{empty}</p>
  return (
    <div className="-mx-5 overflow-x-auto">
      <table className="w-full min-w-[720px] text-sm">
        <thead>
          <tr className="label text-left">
            <th className="px-5 pb-2 font-normal">Contract</th>
            {show !== 'supplier' && <th className="pb-2 font-normal">Buyer</th>}
            {show !== 'buyer' && <th className="pb-2 font-normal">Supplier</th>}
            <th className="pb-2 text-right font-normal">Value</th>
            <th className="px-5 pb-2 font-normal">Ends</th>
          </tr>
        </thead>
        <tbody>
          {awards.map((a) => (
            <tr key={a.award_id} className="border-t border-line align-top">
              <td className="max-w-[340px] px-5 py-3">
                <a href={tedUrl(a.publication_number)} target="_blank" rel="noreferrer" className="line-clamp-2 hover:text-signal">
                  {a.title ?? 'Untitled contract'}
                </a>
                <div className="label mt-1 !normal-case !tracking-normal">
                  {cpvName(a.cpv_division)} · {date(a.award_date)}
                  {a.framework && FRAMEWORK[a.framework] ? ' · framework' : ''}
                  {a.tenders_received ? ` · ${a.tenders_received} bid${a.tenders_received === 1 ? '' : 's'}` : ''}
                </div>
              </td>
              {show !== 'supplier' && (
                <td className="max-w-[220px] py-3 pr-4"><Link to={`/buyers/${encodeURIComponent(a.buyer_key)}`} className="line-clamp-2 hover:text-signal">{a.buyer_name}</Link></td>
              )}
              {show !== 'buyer' && (
                <td className="max-w-[220px] py-3 pr-4">
                  {a.supplier_key
                    ? <Link to={`/suppliers/${encodeURIComponent(a.supplier_key)}`} className="line-clamp-2 hover:text-signal">{a.supplier_name}</Link>
                    : <span className="text-muted">Private individual</span>}
                </td>
              )}
              <td className="num py-3 pr-2 text-right text-amber" title={a.value_suspect ? 'Reported value looks like a typo' : undefined}>
                {a.value_suspect ? <span className="text-muted">?</span> : eur(a.value_eur)}
              </td>
              <td className="px-5 py-3 whitespace-nowrap"><EndsIn d={a.expected_end} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Loading() {
  return <div className="label animate-pulse py-24 text-center">Loading…</div>
}

export function Failed({ error }: { error: string }) {
  return <div className="rounded-xl border border-alarm/40 bg-panel p-6 text-sm text-alarm">{error}</div>
}
