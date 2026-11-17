import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { cpvName, eur, int, monthShort } from '../labels'
import { AwardTable, Failed, Loading, Panel, Stat } from '../ui'
import { useLoad } from '../useLoad'

/** The signature: how many Swedish public contracts end in each of the next 12 months. */
function ContractClock({ months, active, onPick }: {
  months: { month: string; contracts: number; value_eur: number | null }[]; active: string | null; onPick: (m: string | null) => void
}) {
  const max = Math.max(...months.map((m) => m.contracts), 1)
  return (
    <div className="flex h-44 items-end gap-1.5 sm:gap-2.5" role="list" aria-label="Contracts ending per month">
      {months.map((m, i) => {
        const on = active === m.month
        return (
          <button key={m.month} role="listitem" onClick={() => onPick(on ? null : m.month)}
            className="group flex h-full flex-1 flex-col items-center justify-end gap-2" aria-pressed={on}
            title={`${int(m.contracts)} contracts ending, ${eur(m.value_eur)}`}>
            <span className={`num text-[0.65rem] ${on ? 'text-signal' : 'text-muted group-hover:text-ink'}`}>{int(m.contracts)}</span>
            <span className={`w-full rounded-t-sm transition-all ${on ? 'bg-signal' : i < 3 ? 'bg-signal/80' : 'bg-signal/35 group-hover:bg-signal/60'}`}
              style={{ height: `${Math.max(4, (m.contracts / max) * 100)}%` }} />
            <span className={`label !tracking-normal ${on ? '!text-signal' : ''}`}>{monthShort(m.month)}</span>
          </button>
        )
      })}
    </div>
  )
}

export default function Home() {
  const stats = useLoad(() => api.stats(), [])
  const [cpv, setCpv] = useState<string | undefined>()
  const [month, setMonth] = useState<string | null>(null)
  const expiring = useLoad(() => api.expiring(cpv, 12), [cpv])

  if (stats.error) return <div className="py-12"><Failed error={stats.error} /></div>
  const s = stats.data
  const contracts = (expiring.data?.contracts ?? []).filter((c) => !month || c.expected_end?.startsWith(month))

  return (
    <>
      <section className="relative -mx-4 overflow-hidden px-4 pt-16 pb-12 sm:-mx-6 sm:px-6">
        <div className="grid-bg absolute inset-0 -z-10 opacity-60" />
        <p className="label !text-signal">Swedish public procurement · live from EU TED</p>
        <h1 className="mt-4 max-w-3xl font-display text-4xl leading-[1.05] font-semibold tracking-tight sm:text-6xl">
          See the next tender <span className="text-signal">before it's announced.</span>
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-muted">
          Every contract a Swedish public body awards has an end date. Tenderlens tracks who won it, for how much,
          and when it runs out — so you can prepare for the re-tender while competitors wait for the notice.
        </p>
        {s && (
          <div className="mt-10 grid grid-cols-2 gap-6 sm:grid-cols-4">
            <Stat label="Ending in 12 months" value={int(s.expiring_12m)} accent="signal" />
            <Stat label="Contracts awarded" value={int(s.awards)} />
            <Stat label="Public buyers" value={int(s.buyers)} />
            <Stat label="Winning suppliers" value={int(s.suppliers)} />
          </div>
        )}
      </section>

      {!s ? <Loading /> : (
        <div className="space-y-6">
          <Panel title="Contracts ending, next 12 months" aside={month ? <button onClick={() => setMonth(null)} className="hover:text-ink">clear month ×</button> : 'tap a month'}>
            <ContractClock months={s.expiring_by_month} active={month} onPick={setMonth} />
          </Panel>

          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by category">
            <button onClick={() => setCpv(undefined)}
              className={`rounded-full border px-3 py-1.5 text-sm ${!cpv ? 'border-signal bg-signal text-on-signal' : 'border-line hover:border-muted'}`}>
              All categories
            </button>
            {s.expiring_by_division.map((d) => (
              <button key={d.cpv_division} onClick={() => setCpv(d.cpv_division)}
                className={`rounded-full border px-3 py-1.5 text-sm ${cpv === d.cpv_division ? 'border-signal bg-signal text-on-signal' : 'border-line hover:border-muted'}`}>
                {cpvName(d.cpv_division)} <span className="num opacity-60">{int(d.contracts)}</span>
              </button>
            ))}
          </div>

          <Panel title={cpv ? `Ending soon · ${cpvName(cpv)}` : 'Ending soon'}
            aside={cpv ? <Link to={`/markets/${cpv}`} className="hover:text-ink">who wins this market →</Link> : 'soonest first'}>
            {expiring.error ? <Failed error={expiring.error} /> : !expiring.data ? <Loading /> :
              <AwardTable awards={contracts} show="both" empty="No contracts ending in this window." />}
          </Panel>
        </div>
      )}
    </>
  )
}
