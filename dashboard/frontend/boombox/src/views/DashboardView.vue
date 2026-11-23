<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { store } from '../store'
import { checkHealth } from '../api'
import { dailyBuckets, duration, median, reviewMs } from '../stats'
import StackedBarChart, { type Series } from '../components/charts/StackedBarChart.vue'
import HBarChart from '../components/charts/HBarChart.vue'
import SeverityBadge from '../components/SeverityBadge.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { fullTime, timeAgo } from '../time'

const DAY = 86_400_000
const range = ref<7 | 14 | 30>(14)

// ---- API health -----------------------------------------------------------
const latency = ref<number | null>(null)
const healthChecked = ref(false)
let timer: number | undefined

async function ping() {
  latency.value = await checkHealth()
  healthChecked.value = true
}
onMounted(() => {
  ping()
  timer = window.setInterval(ping, 30_000)
})
onBeforeUnmount(() => window.clearInterval(timer))

// ---- derived data ---------------------------------------------------------
const now = () => Date.now()
const createdMs = (iso: string | null) => (iso ? new Date(iso).getTime() : NaN)

const inRange = computed(() =>
  store.items.filter((r) => now() - createdMs(r.created_at) <= range.value * DAY),
)
const prevRange = computed(() =>
  store.items.filter((r) => {
    const age = now() - createdMs(r.created_at)
    return age > range.value * DAY && age <= 2 * range.value * DAY
  }),
)

const pending = computed(() => store.items.filter((r) => r.status === 'pending_review'))
const pendingCritical = computed(
  () => pending.value.filter((r) => r.severity === 'critical' || r.severity === 'high').length,
)

const reviewed = computed(() =>
  inRange.value.filter((r) => r.status === 'approved' || r.status === 'denied'),
)
const approvalRate = computed(() => {
  if (reviewed.value.length === 0) return null
  return reviewed.value.filter((r) => r.status === 'approved').length / reviewed.value.length
})

const medianDecision = computed(() =>
  median(reviewed.value.map(reviewMs).filter((v): v is number => v !== null)),
)

const alertDelta = computed(() => {
  const cur = inRange.value.length
  const prev = prevRange.value.length
  if (prev === 0) return null
  return (cur - prev) / prev
})

const oldestPending = computed(() => {
  const ages = pending.value.map((r) => now() - createdMs(r.created_at)).filter(Number.isFinite)
  return ages.length ? Math.max(...ages) : null
})

// ---- charts ---------------------------------------------------------------
const SERIES: Series[] = [
  { key: 'approved', label: 'Approved', color: 'var(--chart-approved)' },
  { key: 'denied', label: 'Denied', color: 'var(--chart-denied)' },
  { key: 'pending_review', label: 'Pending', color: 'var(--chart-pending)' },
]
const perDay = computed(() => dailyBuckets(store.items, range.value))

const SEVERITIES = ['critical', 'high', 'medium', 'low']

const severityRows = computed(() =>
  SEVERITIES.map((s) => {
    const n = inRange.value.filter((r) => r.severity === s).length
    const pct = inRange.value.length ? Math.round((n / inRange.value.length) * 100) : 0
    return { label: s, value: n, display: String(n), detail: `${pct}% of alerts` }
  }),
)

const ttdRows = computed(() =>
  SEVERITIES.map((s) => {
    const ms = reviewed.value
      .filter((r) => r.severity === s)
      .map(reviewMs)
      .filter((v): v is number => v !== null)
    const m = median(ms)
    return { label: s, value: m ?? 0, display: m === null ? '—' : duration(m), detail: `${ms.length} reviewed` }
  }),
)

const topAlerts = computed(() => {
  const counts = new Map<string, number>()
  for (const r of inRange.value) counts.set(r.title, (counts.get(r.title) ?? 0) + 1)
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([label, value]) => ({ label, value }))
})

const analysts = computed(() => {
  const by = new Map<string, { approved: number; denied: number; ms: number[] }>()
  for (const r of reviewed.value) {
    const who = r.reviewed_by || 'unknown'
    const e = by.get(who) ?? { approved: 0, denied: 0, ms: [] }
    if (r.status === 'approved') e.approved++
    else e.denied++
    const ms = reviewMs(r)
    if (ms !== null) e.ms.push(ms)
    by.set(who, e)
  }
  return [...by.entries()]
    .map(([name, e]) => ({
      name,
      ...e,
      total: e.approved + e.denied,
      rate: Math.round((e.approved / (e.approved + e.denied)) * 100),
      median: median(e.ms),
    }))
    .sort((a, b) => b.total - a.total)
})

// ---- alerts by client ------------------------------------------------------
const clientName = (r: { hostname: string | null; client_id: string | null }) =>
  r.hostname ?? (r.client_id ? r.client_id.slice(0, 8) : 'Unknown')

const recentAlerts = computed(() =>
  [...inRange.value]
    .sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
    .slice(0, 10),
)

const clientRows = computed(() => {
  const counts = new Map<string, number>()
  for (const r of inRange.value) counts.set(clientName(r), (counts.get(clientName(r)) ?? 0) + 1)
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([label, value]) => ({ label, value }))
})

const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v * 100)}%`)
</script>

<template>
  <div class="dash">
    <div class="statusbar">
      <span
        class="health"
        :class="latency !== null ? 'health--up' : healthChecked ? 'health--down' : ''"
      >
        <span class="health__icon" aria-hidden="true">{{ latency !== null ? '●' : '▲' }}</span>
        <template v-if="!healthChecked">Checking API…</template>
        <template v-else-if="latency !== null">API online · {{ latency }} ms</template>
        <template v-else>API unreachable{{ store.usingMock ? ' · showing demo data' : '' }}</template>
      </span>
      <span v-if="store.lastLoaded" class="muted">
        Refreshed {{ store.lastLoaded.toLocaleTimeString() }}
      </span>

      <div class="range" role="group" aria-label="Time range">
        <button
          v-for="d in [7, 14, 30] as const"
          :key="d"
          :class="{ active: range === d }"
          @click="range = d"
        >
          {{ d }}d
        </button>
      </div>
    </div>

    <div class="tiles">
      <div class="tile">
        <div class="tile__label">Pending review</div>
        <div class="tile__value">{{ pending.length }}</div>
        <div class="tile__sub">
          {{ pendingCritical }} high/critical ·
          oldest {{ oldestPending === null ? '—' : duration(oldestPending) }}
        </div>
      </div>
      <div class="tile">
        <div class="tile__label">Alerts, last {{ range }} days</div>
        <div class="tile__value">{{ inRange.length }}</div>
        <div class="tile__sub">
          <template v-if="alertDelta === null">no prior period to compare</template>
          <template v-else>
            {{ alertDelta >= 0 ? '▲' : '▼' }} {{ Math.abs(Math.round(alertDelta * 100)) }}% vs previous {{ range }}d
          </template>
        </div>
      </div>
      <div class="tile">
        <div class="tile__label">Approval rate</div>
        <div class="tile__value">{{ pct(approvalRate) }}</div>
        <div class="tile__sub">of {{ reviewed.length }} fixes reviewed</div>
      </div>
      <div class="tile">
        <div class="tile__label">Median time to decide</div>
        <div class="tile__value">{{ medianDecision === null ? '—' : duration(medianDecision) }}</div>
        <div class="tile__sub">alert created → analyst decision</div>
      </div>
    </div>

    <div class="panels">
      <section class="panel panel--wide">
        <header class="panel__head">
          <h2>Alerts per day</h2>
          <span class="muted">by current status</span>
        </header>
        <StackedBarChart :data="perDay as unknown as Record<string, unknown>[]" :series="SERIES" label-key="label" />
      </section>

      <section class="panel panel--wide">
        <header class="panel__head">
          <h2>Recent alerts</h2>
          <span class="muted">latest 10 · which client raised each alert</span>
        </header>
        <table v-if="recentAlerts.length" class="table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Alert</th>
              <th>Client</th>
              <th>Status</th>
              <th class="num">Age</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in recentAlerts" :key="r.id">
              <td><SeverityBadge :severity="r.severity" /></td>
              <td class="alert-title">{{ r.title }}</td>
              <td :title="r.client_id ?? ''"><strong>{{ clientName(r) }}</strong></td>
              <td><StatusBadge :status="r.status" /></td>
              <td class="num muted" :title="fullTime(r.created_at)">{{ timeAgo(r.created_at) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">No alerts in this range.</p>
      </section>

      <section class="panel">
        <header class="panel__head">
          <h2>Alerts by client</h2>
          <span class="muted">top 6</span>
        </header>
        <HBarChart :rows="clientRows" empty-text="No alerts in this range." />
      </section>

      <section class="panel">
        <header class="panel__head">
          <h2>Severity mix</h2>
          <span class="muted">alerts</span>
        </header>
        <HBarChart :rows="severityRows" capitalize />
      </section>

      <section class="panel">
        <header class="panel__head">
          <h2>Time to decide</h2>
          <span class="muted">median, by severity</span>
        </header>
        <HBarChart :rows="ttdRows" capitalize empty-text="No reviewed alerts in this range." />
      </section>

      <section class="panel">
        <header class="panel__head">
          <h2>Most frequent alerts</h2>
          <span class="muted">top 6</span>
        </header>
        <HBarChart :rows="topAlerts" empty-text="No alerts in this range." />
      </section>

      <section class="panel panel--wide">
        <header class="panel__head">
          <h2>Analyst activity</h2>
          <span class="muted">reviews in range</span>
        </header>
        <table v-if="analysts.length" class="table">
          <thead>
            <tr>
              <th>Analyst</th>
              <th class="num">Approved</th>
              <th class="num">Denied</th>
              <th class="num">Rate</th>
              <th class="num">Median</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in analysts" :key="a.name">
              <td>{{ a.name }}</td>
              <td class="num">{{ a.approved }}</td>
              <td class="num">{{ a.denied }}</td>
              <td class="num">{{ a.rate }}%</td>
              <td class="num">{{ a.median === null ? '—' : duration(a.median) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">No reviews in this range.</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dash {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.statusbar {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  font-size: 0.8rem;
}
.muted {
  color: var(--muted);
  font-size: 0.78rem;
}
.muted strong {
  color: var(--text);
}
.health {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--muted);
}
.health--up .health__icon {
  color: var(--status-approved);
}
.health--down .health__icon {
  color: var(--status-pending);
}
.range {
  margin-left: auto;
  display: flex;
  gap: 2px;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 3px;
  border-radius: 8px;
}
.range button {
  background: none;
  border: none;
  color: var(--muted);
  font: inherit;
  font-size: 0.78rem;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.range button.active {
  background: color-mix(in srgb, var(--accent) 18%, transparent);
  color: var(--text);
}
.tiles {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.tile,
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 20px;
  min-width: 0;
}
.tile__label {
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 500;
}
.tile__value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  margin-top: 4px;
}
.tile__sub {
  font-size: 0.74rem;
  color: var(--muted);
  margin-top: 2px;
}
.panels {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.panel--wide {
  grid-column: 1 / -1;
}
.panel__head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
}
.panel__head h2 {
  font-size: 0.9rem;
  margin: 0;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.table th {
  text-align: left;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
  font-weight: 600;
  padding: 6px 6px;
  border-bottom: 1px solid var(--border);
}
.table td {
  padding: 7px 6px;
  border-bottom: 1px solid color-mix(in srgb, var(--border) 55%, transparent);
}
.alert-title {
  font-weight: 600;
}
.table tr:last-child td {
  border-bottom: none;
}
.num,
.table th.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
@media (max-width: 900px) {
  .tiles {
    grid-template-columns: repeat(2, 1fr);
  }
  .panels {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 460px) {
  .tiles {
    grid-template-columns: 1fr;
  }
}
</style>
