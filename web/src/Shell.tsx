import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, type Party } from './api'
import { date, int, orgnr } from './labels'
import { ThemeToggle, Wordmark } from './ui'

function Search() {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<{ buyers: Party[]; suppliers: Party[] } | null>(null)
  const input = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') { e.preventDefault(); input.current?.focus() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (q.trim().length < 2) { setHits(null); return }
    let live = true
    const t = setTimeout(() => api.search(q.trim()).then((h) => live && setHits(h), () => live && setHits(null)), 180)
    return () => { live = false; clearTimeout(t) }
  }, [q])

  const go = (path: string) => { setQ(''); setHits(null); navigate(path) }
  const all = hits ? [...hits.suppliers.map((h) => ({ ...h, kind: 'supplier' as const })), ...hits.buyers.map((h) => ({ ...h, kind: 'buyer' as const }))] : []

  return (
    <div className="relative w-full max-w-md">
      <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Company or buyer"
        aria-label="Search suppliers and buyers"
        onKeyDown={(e) => { if (e.key === 'Enter' && all[0]) go(`/${all[0].kind}s/${encodeURIComponent(all[0].key)}`); if (e.key === 'Escape') setQ('') }}
        className="w-full rounded-lg border border-line bg-panel px-3.5 py-2 text-sm placeholder:text-muted focus:border-signal focus:outline-none" />
      <kbd className="label pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 rounded border border-line px-1.5 max-sm:hidden">/</kbd>
      {hits && (
        <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-lg border border-line bg-panel shadow-2xl">
          {all.length === 0 && <div className="px-4 py-3 text-sm text-muted">No matches</div>}
          {all.map((h) => (
            <button key={h.kind + h.key} onClick={() => go(`/${h.kind}s/${encodeURIComponent(h.key)}`)}
              className="flex w-full items-baseline justify-between gap-3 border-b border-line px-4 py-2.5 text-left text-sm last:border-0 hover:bg-raised">
              <span className="truncate">{h.name}</span>
              <span className="label shrink-0">{h.kind === 'buyer' ? 'buyer' : h.orgnr ? orgnr(h.orgnr) : 'supplier'} · {int(h.awards)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Shell({ children }: { children: ReactNode }) {
  const [exported, setExported] = useState<string | null>(null)
  useEffect(() => { api.health().then((h) => setExported(h.last_export?.finished_at ?? null), () => {}) }, [])
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3 sm:px-6">
          <Wordmark />
          <div className="flex flex-1 justify-center"><Search /></div>
          <ThemeToggle />
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">{children}</main>
      <footer className="border-t border-line">
        <div className="label mx-auto flex max-w-6xl flex-wrap justify-between gap-2 px-4 py-6 !normal-case !tracking-normal sm:px-6">
          <span>Data: EU TED (eForms notices), Bolagsverket. Swedish buyers since Jan 2024. Values in EUR at ECB monthly rates.</span>
          <span>{exported ? `Updated ${date(exported.slice(0, 10))}` : ''} · <Link to="/about" className="hover:text-ink">How it works</Link></span>
        </div>
      </footer>
    </div>
  )
}
