import type { Endpoint, Remediation } from './types'

const BASE = '/api/v1'

/**
 * The dashboard talks to the Boombox REST API (server/api/app.py) through a Vite
 * proxy (see vite.config.ts). When the backend isn't running on dev, we fall
 * back to local mock data so the UI still looks populated. `usingMock` lets the
 * UI show a small "demo data" banner.
 */
export const state = {
  usingMock: false,
}

function minutesAgo(min: number): string {
  return new Date(Date.now() - min * 60_000).toISOString()
}

const MOCK: Remediation[] = [
  {
    id: 1,
    event_id: 101,
    title: 'Encoded PowerShell execution',
    summary:
      'powershell.exe launched with a base64 -EncodedCommand payload from an Office process. ' +
      'The decoded command downloads and executes a remote script, consistent with a phishing-driven loader.',
    proposed_script:
      '# Kill the offending process and quarantine the parent\n' +
      'Stop-Process -Id 5124 -Force\n' +
      'Rename-Item "$env:TEMP\\update.ps1" "$env:TEMP\\update.ps1.quarantine"\n' +
      'Write-Output "Terminated PID 5124 and quarantined dropper"',
    severity: 'critical',
    status: 'pending_review',
    created_at: minutesAgo(6),
    reviewed_at: null,
    reviewed_by: null,
  },
  {
    id: 2,
    event_id: 102,
    title: 'New scheduled task persistence',
    summary:
      'A scheduled task "SystemUpdater" was registered to run a script in %APPDATA% every 10 minutes. ' +
      'Task name mimics a legitimate Windows service but points to an unsigned binary.',
    proposed_script:
      'schtasks /Delete /TN "SystemUpdater" /F\n' +
      'del "%APPDATA%\\systemupdater.exe"',
    severity: 'high',
    status: 'pending_review',
    created_at: minutesAgo(22),
    reviewed_at: null,
    reviewed_by: null,
  },
  {
    id: 3,
    event_id: 103,
    title: 'SSH brute-force from external IP',
    summary:
      '41 failed SSH auth attempts in 90 seconds from 203.0.113.9 against the "deploy" account, ' +
      'followed by one success. Source IP is not in the allowlist.',
    proposed_script:
      'iptables -A INPUT -s 203.0.113.9 -j DROP\n' +
      'pkill -u deploy\n' +
      'passwd -l deploy',
    severity: 'high',
    status: 'pending_review',
    created_at: minutesAgo(48),
    reviewed_at: null,
    reviewed_by: null,
  },
  {
    id: 4,
    event_id: 104,
    title: 'Unusual outbound DNS volume',
    summary:
      'Endpoint generated ~3x normal DNS traffic to a single rotating subdomain pattern. ' +
      'Possible DNS tunneling / C2 beaconing, though could also be a misconfigured client.',
    proposed_script:
      '# Blackhole the suspicious domain pending review\n' +
      'echo "0.0.0.0 c2.example-cdn.net" >> /etc/hosts',
    severity: 'medium',
    status: 'pending_review',
    created_at: minutesAgo(95),
    reviewed_at: null,
    reviewed_by: null,
  },
  {
    id: 5,
    event_id: 105,
    title: 'Local admin account created',
    summary:
      'Account "svc_backup" was added to the local Administrators group outside the change window. ' +
      'No matching ticket found.',
    proposed_script: 'net localgroup Administrators svc_backup /delete',
    severity: 'medium',
    status: 'approved',
    created_at: minutesAgo(240),
    reviewed_at: minutesAgo(210),
    reviewed_by: 'awhitby',
  },
  {
    id: 6,
    event_id: 106,
    title: 'World-writable cron script',
    summary:
      'A cron job references /opt/scripts/backup.sh which is world-writable (0777). ' +
      'Low immediate risk but a privilege-escalation foothold.',
    proposed_script: 'chmod 750 /opt/scripts/backup.sh\nchown root:root /opt/scripts/backup.sh',
    severity: 'low',
    status: 'denied',
    created_at: minutesAgo(600),
    reviewed_at: minutesAgo(540),
    reviewed_by: 'awhitby',
  },
]

/**
 * Generated review history so the backlog and dashboard have ~2 weeks of data
 * to show in demo mode. Deterministic (seeded) so it doesn't jump on reload.
 */
function generateHistory(startId: number): Remediation[] {
  let seed = 7
  const rand = () => {
    seed = (seed * 16807) % 2147483647
    return (seed - 1) / 2147483646
  }
  const pick = <T,>(arr: T[]) => arr[Math.floor(rand() * arr.length)]!
  const titles = [
    'Suspicious child process of winword.exe',
    'Credential dumping via LSASS access',
    'Unsigned driver loaded',
    'Outbound connection to known C2 range',
    'Persistence via Run registry key',
    'Mass file rename (possible ransomware)',
    'Sudo invoked by unexpected user',
    'Reverse shell pattern in bash history',
    'New SUID binary in /tmp',
    'Disabled Windows Defender real-time protection',
    'Port scan originating from endpoint',
    'Browser extension sideloaded',
  ]
  const severities: Remediation['severity'][] = [
    'critical', 'high', 'high', 'medium', 'medium', 'medium', 'low', 'low',
  ]
  const reviewers = ['awhitby', 'amcewan', 'awhitby', 'jdoe']
  const out: Remediation[] = []
  for (let i = 0; i < 46; i++) {
    const createdMin = 60 * 12 + Math.floor(rand() * 60 * 24 * 13.5)
    const reviewDelay = 3 + Math.floor(rand() * rand() * 240)
    const severity = pick(severities)
    const approved = rand() < (severity === 'low' ? 0.55 : 0.8)
    out.push({
      id: startId + i,
      event_id: 200 + i,
      title: pick(titles),
      summary: 'Historical alert reviewed by an analyst (demo data).',
      proposed_script: '# demo remediation\nWrite-Output "noop"',
      severity,
      status: approved ? 'approved' : 'denied',
      created_at: minutesAgo(createdMin),
      reviewed_at: minutesAgo(createdMin - reviewDelay),
      reviewed_by: pick(reviewers),
    })
  }
  return out
}

const MOCK_ALL: Remediation[] = [...MOCK, ...generateHistory(MOCK.length + 1)]

async function tryFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText} ${detail}`.trim())
  }
  return res.json() as Promise<T>
}

/** Ping the API's /health endpoint. Returns round-trip ms, or null if down. */
export async function checkHealth(): Promise<number | null> {
  const t0 = performance.now()
  try {
    const res = await fetch('/health')
    if (!res.ok) return null
    const body = await res.json()
    return body?.status === 'ok' ? Math.round(performance.now() - t0) : null
  } catch {
    return null
  }
}

export async function listRemediations(): Promise<Remediation[]> {
  try {
    const data = await tryFetch<Remediation[]>(`${BASE}/remediations`)
    state.usingMock = false
    return data
  } catch {
    state.usingMock = true
    // Return a copy so local approve/deny edits don't mutate the source array.
    return MOCK_ALL.map((r) => ({ ...r }))
  }
}

const MOCK_ENDPOINTS: Endpoint[] = [
  {
    id: 1, hostname: 'DESKTOP-01', os: 'Windows 11', last_seen: minutesAgo(1),
    event_count: 212, events_24h: 18, pending_critical: 1, pending_high: 0,
    pending_medium: 0, pending_low: 0, last_alert_at: minutesAgo(6),
  },
  {
    id: 2, hostname: 'FIN-LAPTOP-07', os: 'Windows 10', last_seen: minutesAgo(2),
    event_count: 98, events_24h: 9, pending_critical: 0, pending_high: 1,
    pending_medium: 0, pending_low: 0, last_alert_at: minutesAgo(22),
  },
  {
    id: 3, hostname: 'web-prod-01', os: 'Ubuntu 24.04', last_seen: minutesAgo(0.5),
    event_count: 340, events_24h: 41, pending_critical: 0, pending_high: 1,
    pending_medium: 0, pending_low: 0, last_alert_at: minutesAgo(48),
  },
  {
    id: 4, hostname: 'dev-ws-03', os: 'Fedora 41', last_seen: minutesAgo(3),
    event_count: 57, events_24h: 4, pending_critical: 0, pending_high: 0,
    pending_medium: 1, pending_low: 0, last_alert_at: minutesAgo(95),
  },
  {
    id: 5, hostname: 'db-prod-01', os: 'Debian 12', last_seen: minutesAgo(9),
    event_count: 120, events_24h: 2, pending_critical: 0, pending_high: 0,
    pending_medium: 0, pending_low: 0, last_alert_at: minutesAgo(600),
  },
  {
    id: 6, hostname: 'HR-DESKTOP-02', os: 'Windows 11', last_seen: minutesAgo(60 * 26),
    event_count: 33, events_24h: 0, pending_critical: 0, pending_high: 0,
    pending_medium: 0, pending_low: 0, last_alert_at: minutesAgo(60 * 50),
  },
  {
    id: 7, hostname: 'build-runner-02', os: 'Ubuntu 22.04', last_seen: minutesAgo(1),
    event_count: 410, events_24h: 27, pending_critical: 0, pending_high: 0,
    pending_medium: 0, pending_low: 0, last_alert_at: minutesAgo(240),
  },
  {
    id: 8, hostname: 'MKT-MAC-04', os: 'macOS 15', last_seen: minutesAgo(4),
    event_count: 21, events_24h: 1, pending_critical: 0, pending_high: 0,
    pending_medium: 0, pending_low: 0, last_alert_at: null,
  },
]

export async function listEndpoints(): Promise<Endpoint[]> {
  try {
    return await tryFetch<Endpoint[]>(`${BASE}/endpoints`)
  } catch {
    state.usingMock = true
    return MOCK_ENDPOINTS.map((e) => ({ ...e }))
  }
}

async function review(
  id: number,
  action: 'approve' | 'deny',
  reviewedBy: string,
): Promise<Remediation> {
  if (state.usingMock) {
    // Simulate the server response locally.
    return {
      id,
      status: action === 'approve' ? 'approved' : 'denied',
      reviewed_at: new Date().toISOString(),
      reviewed_by: reviewedBy,
    } as Remediation
  }
  return tryFetch<Remediation>(`${BASE}/remediations/${id}/${action}`, {
    method: 'POST',
    body: JSON.stringify({ reviewed_by: reviewedBy }),
  })
}

export function approveRemediation(id: number, reviewedBy: string) {
  return review(id, 'approve', reviewedBy)
}

export function denyRemediation(id: number, reviewedBy: string) {
  return review(id, 'deny', reviewedBy)
}
