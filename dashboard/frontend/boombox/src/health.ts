import type { Endpoint } from './types'

/**
 * How a client's health is judged. Thresholds live here so they're easy to
 * tune once the endpoint agent's heartbeat interval is settled.
 */
export const STALE_AFTER_MS = 5 * 60_000 // no check-in for 5 min → degraded
export const OFFLINE_AFTER_MS = 15 * 60_000 // no check-in for 15 min → offline

export type Health = 'at_risk' | 'offline' | 'degraded' | 'healthy'

/** Worst first — used for sorting and for picking the overall status. */
export const HEALTH_ORDER: Health[] = ['at_risk', 'offline', 'degraded', 'healthy']

export const HEALTH_LABEL: Record<Health, string> = {
  at_risk: 'At risk',
  offline: 'Offline',
  degraded: 'Degraded',
  healthy: 'Healthy',
}

export interface HealthResult {
  health: Health
  reasons: string[]
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

export function assess(e: Endpoint, now = Date.now()): HealthResult {
  const found: { health: Health; reason: string }[] = []

  const seenAgo = e.last_seen ? now - new Date(e.last_seen).getTime() : Infinity
  if (!Number.isFinite(seenAgo) || seenAgo > OFFLINE_AFTER_MS) {
    found.push({ health: 'offline', reason: e.last_seen ? 'Agent not reporting' : 'Agent has never checked in' })
  } else if (seenAgo > STALE_AFTER_MS) {
    found.push({ health: 'degraded', reason: 'Check-ins are late' })
  }

  const severe = e.pending_critical + e.pending_high
  if (e.pending_critical) found.push({ health: 'at_risk', reason: `${plural(e.pending_critical, 'critical alert')} unresolved` })
  if (e.pending_high) found.push({ health: 'at_risk', reason: `${plural(e.pending_high, 'high alert')} unresolved` })
  const minor = e.pending_medium + e.pending_low
  if (minor && !severe) found.push({ health: 'degraded', reason: `${plural(minor, 'lower-severity alert')} unresolved` })
  else if (minor) found.push({ health: 'at_risk', reason: `+${plural(minor, 'lower-severity alert')}` })

  if (found.length === 0) return { health: 'healthy', reasons: ['Reporting normally, no open alerts'] }
  const health = HEALTH_ORDER.find((h) => found.some((f) => f.health === h))!
  return { health, reasons: found.map((f) => f.reason) }
}
