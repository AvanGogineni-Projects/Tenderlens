// Typed client for the Tenderlens API (read-only, no auth).

export interface Award {
  award_id: string
  publication_number: string
  award_date: string
  title: string | null
  cpv: string | null
  cpv_division: string | null
  contract_nature: string | null
  procedure_type: string | null
  framework: string | null
  value: string | null
  currency: string | null
  value_eur: number | null
  value_suspect: boolean
  tenders_received: number | null
  expected_end: string | null
  buyer_key: string
  buyer_name: string
  supplier_key: string | null
  supplier_name: string | null
}

export interface Stats {
  awards: number
  buyers: number
  suppliers: number
  expiring_12m: number
  since: string | null
  expiring_by_month: { month: string; contracts: number; value_eur: number | null }[]
  expiring_by_division: { cpv_division: string; contracts: number }[]
}

export interface Party { key: string; name: string; awards: number; value_eur: number | null; orgnr?: string | null }

export interface Supplier {
  supplier_key: string; name: string; country: string | null; orgnr: string | null; size: string | null
  awards: number; buyers: number; value_eur: number | null; first_award: string | null; last_award: string | null
  registered_name: string | null; legal_form: string | null; deregistered_on: string | null
  deregistration_reason: string | null
}

export interface Buyer {
  buyer_key: string; name: string; awards: number; suppliers: number; value_eur: number | null
  avg_tenders_received: number | null; first_award: string | null; last_award: string | null
}

export interface MarketRow { key: string; name: string; awards: number; value_eur: number; share: number; rank: number }
export interface Position { cpv_division: string; year: number; share: number; rank: number; value_eur: number }

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const qs = params
    ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]))
    : ''
  const res = await fetch(path + qs)
  if (!res.ok) throw new Error(res.status === 404 ? 'Not found' : `Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export const api = {
  health: () => get<{ ok: boolean; last_export: { finished_at: string } | null }>('/health'),
  stats: () => get<Stats>('/v1/stats'),
  search: (q: string) => get<{ buyers: Party[]; suppliers: Party[] }>('/v1/search', { q }),
  supplier: (key: string) =>
    get<{ supplier: Supplier; awards: Award[]; buyers: Party[]; markets: Position[] }>(`/v1/suppliers/${encodeURIComponent(key)}`),
  buyer: (key: string) =>
    get<{ buyer: Buyer; awards: Award[]; suppliers: Party[]; expiring: Award[]; expiring_count: number }>(`/v1/buyers/${encodeURIComponent(key)}`),
  expiring: (cpv?: string, months = 12, offset = 0) =>
    get<{ contracts: Award[] }>('/v1/expiring', { cpv, months, offset, limit: 50 }),
  market: (cpv: string, year?: number) =>
    get<{ cpv_division: string; year: number | null; suppliers: MarketRow[] }>(`/v1/markets/${cpv}`, { year }),
}
