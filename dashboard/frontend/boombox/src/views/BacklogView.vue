<script setup lang="ts">
import { computed, ref } from 'vue'
import { store } from '../store'
import { fullTime, timeAgo } from '../time'
import { duration } from '../stats'
import SeverityBadge from '../components/SeverityBadge.vue'
import StatusBadge from '../components/StatusBadge.vue'
import RemediationDetail from '../components/RemediationDetail.vue'

type Decision = 'all' | 'approved' | 'denied'

const decision = ref<Decision>('all')
const severity = ref<string>('all')
const reviewer = ref<string>('all')
const query = ref('')
const selectedId = ref<number | null>(null)

const reviewed = computed(() =>
  store.items.filter((r) => r.status === 'approved' || r.status === 'denied'),
)

const reviewers = computed(() =>
  [...new Set(reviewed.value.map((r) => r.reviewed_by).filter(Boolean))].sort() as string[],
)

const rows = computed(() => {
  const q = query.value.trim().toLowerCase()
  return reviewed.value
    .filter((r) => decision.value === 'all' || r.status === decision.value)
    .filter((r) => severity.value === 'all' || r.severity === severity.value)
    .filter((r) => reviewer.value === 'all' || r.reviewed_by === reviewer.value)
    .filter(
      (r) =>
        !q ||
        r.title.toLowerCase().includes(q) ||
        String(r.event_id).includes(q) ||
        String(r.id).includes(q),
    )
    .sort((a, b) => (b.reviewed_at ?? '').localeCompare(a.reviewed_at ?? ''))
})

const counts = computed(() => ({
  all: reviewed.value.length,
  approved: reviewed.value.filter((r) => r.status === 'approved').length,
  denied: reviewed.value.filter((r) => r.status === 'denied').length,
}))

const selected = computed(
  () => store.items.find((r) => r.id === selectedId.value) ?? null,
)

const DECISIONS: { key: Decision; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'approved', label: 'Approved' },
  { key: 'denied', label: 'Denied' },
]

function reviewTime(created: string | null, reviewedAt: string | null) {
  if (!created || !reviewedAt) return '—'
  return duration(new Date(reviewedAt).getTime() - new Date(created).getTime())
}

function exportCsv() {
  const header = ['id', 'event_id', 'title', 'severity', 'status', 'created_at', 'reviewed_at', 'reviewed_by']
  const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines = [
    header.join(','),
    ...rows.value.map((r) => header.map((h) => esc(r[h as keyof typeof r])).join(',')),
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'boombox-review-backlog.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}
</script>

<template>
  <div class="grid">
    <section class="left">
      <div class="filters">
        <div class="tabs">
          <button
            v-for="d in DECISIONS"
            :key="d.key"
            class="tab"
            :class="{ 'tab--active': decision === d.key }"
            @click="decision = d.key"
          >
            {{ d.label }}
            <span class="tab__count">{{ counts[d.key] }}</span>
          </button>
        </div>

        <select v-model="severity" class="control" aria-label="Severity">
          <option value="all">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select v-model="reviewer" class="control" aria-label="Reviewer">
          <option value="all">All analysts</option>
          <option v-for="r in reviewers" :key="r" :value="r">{{ r }}</option>
        </select>

        <input
          v-model="query"
          class="control control--search"
          type="search"
          placeholder="Search title or ID…"
        />

        <button class="control control--btn" :disabled="rows.length === 0" @click="exportCsv">
          Export CSV
        </button>
      </div>

      <p v-if="store.loading" class="loading">Loading history…</p>

      <div v-else class="table">
        <div class="table__head">
          <span>Decision</span>
          <span>Severity</span>
          <span>Alert</span>
          <span class="col-who">Analyst</span>
          <span class="col-when">Decided</span>
          <span class="col-ttr num">Time to decide</span>
        </div>

        <p v-if="rows.length === 0" class="empty">No reviewed alerts match these filters.</p>

        <button
          v-for="r in rows"
          :key="r.id"
          class="row"
          :class="{ 'row--active': r.id === selectedId }"
          @click="selectedId = r.id"
        >
          <span><StatusBadge :status="r.status" /></span>
          <span><SeverityBadge :severity="r.severity" /></span>
          <span class="title">
            <span class="title__text">{{ r.title }}</span>
            <span class="title__sub mono">#{{ r.id }} · event #{{ r.event_id }}</span>
          </span>
          <span class="col-who">{{ r.reviewed_by || '—' }}</span>
          <span class="col-when muted" :title="fullTime(r.reviewed_at)">{{ timeAgo(r.reviewed_at) }}</span>
          <span class="col-ttr muted num">{{ reviewTime(r.created_at, r.reviewed_at) }}</span>
        </button>
      </div>
      <p class="footnote">Showing {{ rows.length }} of {{ reviewed.length }} reviewed alerts</p>
    </section>

    <section class="right">
      <RemediationDetail
        :item="selected"
        :busy="store.busy"
        @close="selectedId = null"
      />
    </section>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 20px;
  align-items: start;
}
.left,
.right {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}
.filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.tabs {
  display: flex;
  gap: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 4px;
  border-radius: 10px;
}
.tab {
  background: transparent;
  border: none;
  color: var(--muted);
  padding: 6px 12px;
  border-radius: 7px;
  cursor: pointer;
  font: inherit;
  font-size: 0.84rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 7px;
}
.tab--active {
  background: color-mix(in srgb, var(--accent) 16%, transparent);
  color: var(--text);
}
.tab__count {
  font-size: 0.7rem;
  background: color-mix(in srgb, var(--border) 80%, transparent);
  padding: 1px 7px;
  border-radius: 999px;
}
.control {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font: inherit;
  font-size: 0.84rem;
  padding: 8px 10px;
}
.control:focus {
  outline: none;
  border-color: var(--accent);
}
.control--search {
  flex: 1;
  min-width: 160px;
}
.control--btn {
  cursor: pointer;
}
.control--btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.control--btn:disabled {
  opacity: 0.5;
  cursor: default;
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
  grid-template-columns: 112px 104px 1fr 90px 80px 110px;
  gap: 12px;
  align-items: center;
  padding: 11px 18px;
  text-align: left;
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
  width: 100%;
  background: transparent;
  border: none;
  border-bottom: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
  color: var(--text);
  cursor: pointer;
  font: inherit;
  font-size: 0.85rem;
}
.row:last-child {
  border-bottom: none;
}
.row:hover {
  background: color-mix(in srgb, var(--accent) 7%, transparent);
}
.row--active {
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  box-shadow: inset 3px 0 0 var(--accent);
}
.title {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.title__text {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.title__sub {
  font-size: 0.74rem;
  color: var(--muted);
}
.mono {
  font-family: var(--mono);
}
.muted {
  color: var(--muted);
}
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.empty,
.loading {
  padding: 40px;
  text-align: center;
  color: var(--muted);
}
.footnote {
  margin: 0;
  font-size: 0.75rem;
  color: var(--muted);
}
@media (max-width: 1100px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 720px) {
  .table__head {
    display: none;
  }
  .row {
    grid-template-columns: auto auto 1fr;
  }
  .title {
    grid-column: 1 / -1;
  }
  .col-who,
  .col-when,
  .col-ttr {
    display: none;
  }
}
</style>
