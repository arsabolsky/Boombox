<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { store } from '../store'
import { fullTime, timeAgo } from '../time'
import { assess, HEALTH_LABEL, HEALTH_ORDER, OFFLINE_AFTER_MS, STALE_AFTER_MS, type Health } from '../health'

const filter = ref<Health | 'all'>('all')
const query = ref('')

// Re-evaluate "last seen" based health every 30s even without a reload.
const now = ref(Date.now())
let timer: number | undefined
onMounted(() => (timer = window.setInterval(() => (now.value = Date.now()), 30_000)))
onBeforeUnmount(() => window.clearInterval(timer))

const assessed = computed(() =>
  store.endpoints
    .map((e) => ({ ...e, ...assess(e, now.value) }))
    .sort(
      (a, b) =>
        HEALTH_ORDER.indexOf(a.health) - HEALTH_ORDER.indexOf(b.health) ||
        a.hostname.localeCompare(b.hostname),
    ),
)

const counts = computed(() => {
  const c = { all: assessed.value.length } as Record<Health | 'all', number>
  for (const h of HEALTH_ORDER) c[h] = assessed.value.filter((e) => e.health === h).length
  return c
})

const rows = computed(() => {
  const q = query.value.trim().toLowerCase()
  return assessed.value
    .filter((e) => filter.value === 'all' || e.health === filter.value)
    .filter((e) => !q || e.hostname.toLowerCase().includes(q) || (e.os ?? '').toLowerCase().includes(q))
})

const ICON: Record<Health, string> = { at_risk: '✕', offline: '○', degraded: '▲', healthy: '●' }
const SEVS = ['critical', 'high', 'medium', 'low'] as const
const mins = (ms: number) => Math.round(ms / 60_000)
</script>

<template>
  <div class="clients">
    <div class="summary">
      <button
        class="chip chip--all"
        :class="{ 'chip--active': filter === 'all' }"
        @click="filter = 'all'"
      >
        <span class="chip__value">{{ counts.all }}</span>
        <span class="chip__label">All clients</span>
      </button>
      <button
        v-for="h in HEALTH_ORDER"
        :key="h"
        class="chip"
        :class="[`h--${h}`, { 'chip--active': filter === h }]"
        @click="filter = filter === h ? 'all' : h"
      >
        <span class="chip__value">{{ counts[h] }}</span>
        <span class="chip__label"><span aria-hidden="true">{{ ICON[h] }}</span> {{ HEALTH_LABEL[h] }}</span>
      </button>
    </div>

    <div class="toolbar">
      <input
        v-model="query"
        class="control"
        type="search"
        placeholder="Search hostname or OS…"
        aria-label="Search clients"
      />
      <span class="muted">
        Degraded after {{ mins(STALE_AFTER_MS) }} min without a check-in, offline after
        {{ mins(OFFLINE_AFTER_MS) }} min. Unresolved high/critical alerts mark a client at risk.
      </span>
    </div>

    <p v-if="store.loading && !store.endpoints.length" class="empty">Loading clients…</p>

    <div v-else class="table">
      <div class="table__head">
        <span>Health</span>
        <span>Client</span>
        <span class="col-why">Why</span>
        <span>Open alerts</span>
        <span class="col-seen">Last seen</span>
        <span class="col-ev num">Events 24h</span>
      </div>

      <p v-if="rows.length === 0" class="empty">
        {{ store.endpoints.length ? 'No clients match these filters.' : 'No clients have registered yet.' }}
      </p>

      <div v-for="e in rows" :key="e.client_id" class="row" :class="`row--${e.health}`">
        <span>
          <span class="badge" :class="`h--${e.health}`">
            <span aria-hidden="true">{{ ICON[e.health] }}</span> {{ HEALTH_LABEL[e.health] }}
          </span>
        </span>
        <span class="host">
          <span class="host__name mono">{{ e.hostname }}</span>
          <span class="host__sub">{{ e.os || 'Unknown OS' }} · {{ e.client_id }}</span>
        </span>
        <span class="col-why why">
          <span v-for="r in e.reasons" :key="r">{{ r }}</span>
        </span>
        <span class="alerts">
          <template v-for="s in SEVS" :key="s">
            <span v-if="e[`pending_${s}`]" class="pill" :class="`sev--${s}`" :title="`${s} pending review`">
              {{ e[`pending_${s}`] }} {{ s }}
            </span>
          </template>
          <span
            v-if="!e.pending_critical && !e.pending_high && !e.pending_medium && !e.pending_low"
            class="muted"
          >None</span>
        </span>
        <span class="col-seen muted" :title="fullTime(e.last_seen)">{{ e.last_seen ? timeAgo(e.last_seen) : 'Never' }}</span>
        <span class="col-ev num muted" :title="`${e.event_count} events total`">{{ e.events_24h }}</span>
      </div>
    </div>
    <p class="footnote">Showing {{ rows.length }} of {{ assessed.length }} clients, worst first</p>
  </div>
</template>

<style scoped>
.clients {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.h--at_risk { --h: var(--sev-critical); }
.h--offline { --h: var(--muted); }
.h--degraded { --h: var(--sev-medium); }
.h--healthy { --h: var(--status-approved); }

.summary {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.chip {
  --h: var(--accent);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  text-align: left;
  color: var(--text);
  font: inherit;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.chip:hover {
  border-color: color-mix(in srgb, var(--h) 50%, var(--border));
}
.chip--active {
  border-color: var(--h);
  box-shadow: inset 0 0 0 1px var(--h);
}
.chip__value {
  font-size: 1.7rem;
  font-weight: 700;
  line-height: 1.1;
}
.chip:not(.chip--all) .chip__value {
  color: var(--h);
}
.chip__label {
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 500;
}
.chip:not(.chip--all) .chip__label span {
  color: var(--h);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.control {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font: inherit;
  font-size: 0.84rem;
  padding: 8px 10px;
  min-width: 220px;
}
.control:focus {
  outline: none;
  border-color: var(--accent);
}
.muted {
  color: var(--muted);
  font-size: 0.78rem;
}
.table {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}
.table__head,
.row {
  display: grid;
  grid-template-columns: 112px minmax(150px, 1.1fr) 1.4fr minmax(140px, 1fr) 90px 80px;
  gap: 12px;
  align-items: center;
  padding: 11px 18px;
}
.table__head {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--border) 25%, transparent);
}
.row {
  font-size: 0.85rem;
  border-bottom: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
}
.row:last-child {
  border-bottom: none;
}
.row--at_risk {
  box-shadow: inset 3px 0 0 var(--sev-critical);
}
.row--offline {
  box-shadow: inset 3px 0 0 var(--muted);
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--h);
  background: color-mix(in srgb, var(--h) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--h) 35%, transparent);
}
.host {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.host__name {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.host__sub {
  font-size: 0.74rem;
  color: var(--muted);
}
.why {
  display: flex;
  flex-direction: column;
  font-size: 0.8rem;
  color: var(--muted);
}
.alerts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.pill {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 999px;
  white-space: nowrap;
  color: var(--c);
  background: color-mix(in srgb, var(--c) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
}
.sev--critical { --c: var(--sev-critical); }
.sev--high { --c: var(--sev-high); }
.sev--medium { --c: var(--sev-medium); }
.sev--low { --c: var(--sev-low); }
.mono {
  font-family: var(--mono);
}
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.empty {
  padding: 40px;
  text-align: center;
  color: var(--muted);
  margin: 0;
}
.footnote {
  margin: 0;
  font-size: 0.75rem;
  color: var(--muted);
}
@media (max-width: 900px) {
  .summary {
    grid-template-columns: repeat(3, 1fr);
  }
  .table__head {
    display: none;
  }
  .row {
    grid-template-columns: auto 1fr;
  }
  .col-seen,
  .col-ev {
    display: none;
  }
  .why,
  .alerts {
    grid-column: 1 / -1;
  }
}
@media (max-width: 460px) {
  .summary {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
