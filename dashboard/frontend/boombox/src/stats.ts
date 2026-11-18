import type { Remediation } from './types'

export function duration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return '—'
  const mins = Math.round(ms / 60_000)
  if (mins < 60) return `${mins}m`
  const hours = mins / 60
  if (hours < 24) return `${hours.toFixed(hours < 10 ? 1 : 0)}h`
  return `${(hours / 24).toFixed(1)}d`
}

export function median(values: number[]): number | null {
  if (values.length === 0) return null
  const s = [...values].sort((a, b) => a - b)
  const mid = Math.floor(s.length / 2)
  return s.length % 2 ? s[mid]! : (s[mid - 1]! + s[mid]!) / 2
}

/** Minutes between creation and review, for reviewed items only. */
export function reviewMs(r: Remediation): number | null {
  if (!r.created_at || !r.reviewed_at) return null
  const ms = new Date(r.reviewed_at).getTime() - new Date(r.created_at).getTime()
  return Number.isFinite(ms) && ms >= 0 ? ms : null
}

function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

export interface DayBucket {
  label: string
  date: Date
  approved: number
  denied: number
  pending_review: number
}

/** Alerts per calendar day (by created_at) for the last `days` days, oldest first. */
export function dailyBuckets(items: Remediation[], days: number): DayBucket[] {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const buckets: DayBucket[] = []
  const index = new Map<string, DayBucket>()
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    const b: DayBucket = {
      label: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      date: d,
      approved: 0,
      denied: 0,
      pending_review: 0,
    }
    buckets.push(b)
    index.set(dayKey(d), b)
  }
  for (const r of items) {
    if (!r.created_at) continue
    const b = index.get(dayKey(new Date(r.created_at)))
    if (!b) continue
    if (r.status === 'approved') b.approved++
    else if (r.status === 'denied') b.denied++
    else b.pending_review++
  }
  return buckets
}
