import { useParams } from 'react-router-dom'
import { api } from '../api'
import { date, eur, int } from '../labels'
import { AwardTable, Bars, Failed, Loading, Panel, Stat } from '../ui'
import { useLoad } from '../useLoad'

export default function Buyer() {
  const { key = '' } = useParams()
  const { data, error } = useLoad(() => api.buyer(key), [key])
  if (error) return <div className="py-12"><Failed error={error === 'Not found' ? 'No buyer with that id.' : error} /></div>
  if (!data) return <Loading />
  const { buyer: b, awards, suppliers, expiring, expiring_count } = data

  return (
    <div className="space-y-6 pt-10">
      <header>
        <p className="label">Public buyer</p>
        <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">{b.name}</h1>
        <div className="mt-8 grid grid-cols-2 gap-6 sm:grid-cols-4">
          <Stat label="Contracts awarded" value={int(b.awards)} />
          <Stat label="Value awarded" value={eur(b.value_eur)} accent="amber" />
          <Stat label="Avg bids per contract" value={b.avg_tenders_received ? b.avg_tenders_received.toFixed(1) : '—'} />
          <Stat label="Contracts still running" value={int(expiring_count)} accent="signal" />
        </div>
      </header>

      <Panel title="Contracts ending next" aside={expiring_count > expiring.length ? `soonest ${expiring.length} of ${int(expiring_count)}` : 'soonest first'}>
        <AwardTable awards={expiring} show="supplier" empty="Nothing ending — no contracts with a known end date ahead." />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <Panel title="Main suppliers" aside="by contracts">
          <Bars rows={suppliers.map((s) => ({ key: s.key, label: s.name, value: s.awards, text: `${s.awards} · ${eur(s.value_eur)}`, to: `/suppliers/${encodeURIComponent(s.key)}` }))} />
        </Panel>
        <Panel title="Award history" aside={`since ${date(b.first_award)}`}>
          <AwardTable awards={awards} show="supplier" empty="No contracts." />
        </Panel>
      </div>
    </div>
  )
}
