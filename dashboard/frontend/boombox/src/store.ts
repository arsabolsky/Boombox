import { reactive } from 'vue'
import type { Endpoint, Remediation } from './types'
import {
  approveRemediation,
  denyRemediation,
  listEndpoints,
  listRemediations,
  saveRemediationScript,
  state as apiState,
} from './api'

/**
 * Shared app state. All pages read from the
 * same list so an approval on one page shows up immediately on the others.
 */
export const store = reactive({
  items: [] as Remediation[],
  endpoints: [] as Endpoint[],
  loading: true,
  busy: false,
  error: null as string | null,
  usingMock: false,
  reviewer: 'awhitby',
  autoApprove: false,
  lastLoaded: null as Date | null,
})

export async function load() {
  store.loading = true
  store.error = null
  try {
    const [items, endpoints] = await Promise.all([listRemediations(), listEndpoints()])
    store.items = items
    store.endpoints = endpoints
    store.usingMock = apiState.usingMock
    store.lastLoaded = new Date()
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  } finally {
    store.loading = false
  }
}

function applyReview(updated: Remediation, fallbackStatus: string) {
  const idx = store.items.findIndex((r) => r.id === updated.id)
  if (idx !== -1) {
    store.items[idx] = {
      ...store.items[idx]!,
      status: updated.status ?? fallbackStatus,
      reviewed_at: updated.reviewed_at ?? new Date().toISOString(),
      reviewed_by: updated.reviewed_by ?? store.reviewer,
    }
  }
}

async function review(id: number, action: 'approve' | 'deny') {
  store.busy = true
  store.error = null
  try {
    const res =
      action === 'approve'
        ? await approveRemediation(id, store.reviewer)
        : await denyRemediation(id, store.reviewer)
    applyReview(res, action === 'approve' ? 'approved' : 'denied')
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
  } finally {
    store.busy = false
  }
}

export const approve = (id: number) => review(id, 'approve')
export const deny = (id: number) => review(id, 'deny')

/**
 * Save an edited remediation script back to the server and update the shared
 * list so every page reflects the new script. Returns true on success.
 */
export async function saveScript(id: number, script: string): Promise<boolean> {
  store.busy = true
  store.error = null
  try {
    const res = await saveRemediationScript(id, script)
    const idx = store.items.findIndex((r) => r.id === id)
    if (idx !== -1) {
      store.items[idx] = {
        ...store.items[idx]!,
        proposed_script: res.proposed_script ?? script,
      }
    }
    return true
  } catch (e) {
    store.error = e instanceof Error ? e.message : String(e)
    return false
  } finally {
    store.busy = false
  }
}

export const SEVERITY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}
