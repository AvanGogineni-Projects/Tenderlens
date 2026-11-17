import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { cpvName, eur, int, pct } from '../labels'
import { Failed, Loading, Panel } from '../ui'
import { useLoad } from '../useLoad'

const YEARS = [2026, 2025, 2024]

export default function Market() {
  const { cpv = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const year = params.get('year') ? Number(params.get('year')) : undefined
  const { data, error } = useLoad(() => api.market(cpv, year), [cpv, year])
  if (error) return <div className="py-12"><Failed error={error} /></div>
  if (!data) return <Loading />
  const top = data.suppliers
  const max = Math.max(...top.map((r) => r.share), 0.0001)

  return (
    <div className="space-y-6 pt-10">
      <header>
        <p className="label">Market · CPV {cpv}</p>
        <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">{cpvName(cpv)}</h1>
        <div className="mt-6 flex gap-2">
          {YEARS.map((y) => (
            <button key={y} onClick={() => setParams({ year: String(y) })}
              className={`num rounded-md border px-3 py-1 text-sm ${data.year === y ? 'border-signal text-signal' : 'border-line text-muted hover:text-ink'}`}>{y}</button>
          ))}
        </div>
      </header>
      <Panel title={`Who wins · ${data.year ?? ''}`} aside="share of contract value (EUR)">
        {top.length === 0 ? <p className="text-sm text-muted">No priced awards in this category and year.</p> : (
          <ol className="space-y-3">
            {top.map((r) => (
              <li key={r.key} className="grid grid-cols-[2rem_1fr] items-center gap-3">
                <span className="num text-right text-muted">{r.rank}</span>
                <div>
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <Link to={`/suppliers/${encodeURIComponent(r.key)}`} className="truncate hover:text-signal">{r.name}</Link>
                    <span className="num shrink-0 text-muted">{int(r.awards)} · {eur(r.value_eur)} · <span className="text-amber">{pct(r.share)}</span></span>
                  </div>
                  <div className="mt-1 h-1.5 rounded-full bg-raised"><div className="h-1.5 rounded-full bg-amber" style={{ width: `${(r.share / max) * 100}%` }} /></div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </Panel>
    </div>
  )
}
