export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Status = 'pending_review' | 'approved' | 'denied'

export interface Remediation {
  id: number
  event_id: number
  title: string
  summary: string | null
  proposed_script: string | null
  severity: Severity | string
  status: Status | string
  created_at: string | null
  reviewed_at: string | null
  reviewed_by: string | null
  /** The client this alert came from, joined from the clients table. */
  client_id: string | null
  hostname: string | null
}

/** A monitored client host, with counts used to judge its health. */
export interface Endpoint {
  client_id: string
  hostname: string
  os: string | null
  last_seen: string | null
  event_count: number
  events_24h: number
  pending_critical: number
  pending_high: number
  pending_medium: number
  pending_low: number
  last_alert_at: string | null
}