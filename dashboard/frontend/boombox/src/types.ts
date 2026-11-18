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
}
