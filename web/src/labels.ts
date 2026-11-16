// CPV divisions (the first two digits of a CPV code), as named in the CPV 2008 regulation, shortened.
export const CPV: Record<string, string> = {
  '03': 'Agriculture, farming, fishing & forestry', '09': 'Fuel, electricity & energy', '14': 'Mining & basic metals',
  '15': 'Food & beverages', '16': 'Agricultural machinery', '18': 'Clothing & footwear', '19': 'Textiles, plastics & rubber',
  '22': 'Printed matter', '24': 'Chemicals', '30': 'Office & computing equipment', '31': 'Electrical machinery',
  '32': 'Radio, TV & telecom equipment', '33': 'Medical equipment & pharmaceuticals', '34': 'Transport equipment',
  '35': 'Security, defence & emergency equipment', '37': 'Sports goods, toys & instruments', '38': 'Laboratory & precision instruments',
  '39': 'Furniture & cleaning products', '41': 'Water', '42': 'Industrial machinery', '43': 'Construction & mining machinery',
  '44': 'Construction materials', '45': 'Construction work', '48': 'Software & information systems',
  '50': 'Repair & maintenance', '51': 'Installation services', '55': 'Hotels, catering & retail', '60': 'Transport services',
  '63': 'Transport support & travel', '64': 'Postal & telecom services', '65': 'Public utilities', '66': 'Financial & insurance',
  '70': 'Real estate', '71': 'Architecture & engineering', '72': 'IT services', '73': 'Research & development',
  '75': 'Public administration & defence services', '76': 'Oil & gas services', '77': 'Agricultural & forestry services',
  '79': 'Business services', '80': 'Education & training', '85': 'Health & social work', '90': 'Waste, cleaning & environment',
  '92': 'Recreation, culture & sport', '98': 'Other community services',
}
export const cpvName = (d: string | null) => (d && CPV[d]) || (d ? `CPV ${d}` : 'Unclassified')

const sek = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
/** € with a magnitude suffix: €1.2m, €340k. */
export function eur(v: number | null | undefined): string {
  if (v === null || v === undefined || v === 0) return '—'  // senders put 0 when they don't publish the value
  const a = Math.abs(v)
  if (a >= 1e9) return `€${(v / 1e9).toFixed(1)}bn`
  if (a >= 1e6) return `€${(v / 1e6).toFixed(1)}m`
  if (a >= 1e3) return `€${Math.round(v / 1e3)}k`
  return `€${Math.round(v)}`
}
export const int = (n: number | null | undefined) => (n === null || n === undefined ? '—' : sek.format(n))
export const pct = (s: number) => `${(s * 100).toFixed(s < 0.1 ? 1 : 0)}%`

export function date(d: string | null | undefined): string {
  if (!d) return '—'
  return new Date(d + (d.length === 10 ? 'T00:00:00' : '')).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}
export function monthShort(m: string): string {
  return new Date(m + '-01T00:00:00').toLocaleDateString('en-GB', { month: 'short' })
}
/** Whole months from today until `d` (0 = this month). */
export function monthsUntil(d: string): number {
  const now = new Date(), t = new Date(d + 'T00:00:00')
  return (t.getFullYear() - now.getFullYear()) * 12 + t.getMonth() - now.getMonth()
}
export function orgnr(n: string | null): string {
  return n && n.length === 10 ? `${n.slice(0, 6)}-${n.slice(6)}` : n ?? ''
}
export const FRAMEWORK: Record<string, string> = { 'fa-w-rc': 'Framework', 'fa-wo-rc': 'Framework', 'fa-mix': 'Framework' }
export const tedUrl = (pub: string) => `https://ted.europa.eu/en/notice/-/detail/${pub}`
