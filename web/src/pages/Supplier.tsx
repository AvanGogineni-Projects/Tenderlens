import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { cpvName, date, eur, int, orgnr, pct } from '../labels'
import { AwardTable, Bars, Failed, Loading, Panel, Stat } from '../ui'
import { useLoad } from '../useLoad'

export default function Supplier() {
  const { key = '' } = useParams()
  const { data, error } = useLoad(() => api.supplier(key), [key])
  if (error) return <div className="py-12"><Failed error={error === 'Not found' ? 'No supplier with that id.' : error} /></div>
  if (!data) return <Loading />
  const { supplier: s, awards, buyers, markets } = data
  const gone = s.deregistered_on

  return (
    <div className="space-y-6 pt-10">
      <header>
        <p className="label">Supplier{s.orgnr ? ` · ${orgnr(s.orgnr)}` : ''}{s.legal_form ? ` · ${s.legal_form.split('-')[0]}` : ''}{s.size ? ` · ${s.size}` : ''}</p>
        <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">{s.name}</h1>
        {gone && (
          <p className="mt-3 inline-block rounded-md border border-alarm/50 px-2.5 py-1 text-sm text-alarm">
            Deregistered {date(gone)}{s.deregistration_reason ? ` — ${s.deregistration_reason.toLowerCase()}` : ''}
          </p>
        )}
        <div className="mt-8 grid grid-cols-2 gap-6 sm:grid-cols-4">
          <Stat label="Contracts won" value={int(s.awards)} />
          <Stat label="Value won" value={eur(s.value_eur)} accent="amber" />
          <Stat label="Public buyers" value={int(s.buyers)} />
          <Stat label="Latest award" value={<span className="text-lg">{date(s.last_award)}</span>} />
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Biggest customers" aside="by contracts">
          <Bars rows={buyers.map((b) => ({ key: b.key, label: b.name, value: b.awards, text: `${b.awards} · ${eur(b.value_eur)}`, to: `/buyers/${encodeURIComponent(b.key)}` }))} />
        </Panel>
        <Panel title="Market positions" aside="top 10 finishes">
          {markets.length === 0 ? <p className="text-sm text-muted">Not in the top 10 of any category by value.</p> : (
            <ol className="divide-y divide-line">
              {markets.map((m) => (
                <li key={`${m.cpv_division}-${m.year}`} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                  <Link to={`/markets/${m.cpv_division}?year=${m.year}`} className="truncate hover:text-signal">{cpvName(m.cpv_division)}</Link>
                  <span className="num shrink-0 text-muted">{m.year} · #{m.rank} · <span className="text-amber">{pct(m.share)}</span></span>
                </li>
              ))}
            </ol>
          )}
        </Panel>
      </div>

      <Panel title="Contracts won" aside={`latest ${awards.length}`}>
        <AwardTable awards={awards} show="buyer" empty="No contracts." />
      </Panel>
    </div>
  )
}
