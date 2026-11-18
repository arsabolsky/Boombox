<script setup lang="ts">
import { computed } from 'vue'
import type { Remediation } from '../types'

const props = defineProps<{ items: Remediation[] }>()

const stats = computed(() => {
  const total = props.items.length
  const pending = props.items.filter((r) => r.status === 'pending_review').length
  const approved = props.items.filter((r) => r.status === 'approved').length
  const denied = props.items.filter((r) => r.status === 'denied').length
  const critical = props.items.filter(
    (r) => r.severity === 'critical' && r.status === 'pending_review',
  ).length
  return { total, pending, approved, denied, critical }
})
</script>

<template>
  <div class="cards">
    <div class="card card--accent">
      <div class="card__label">Pending review</div>
      <div class="card__value">{{ stats.pending }}</div>
      <div class="card__sub">{{ stats.critical }} critical awaiting action</div>
    </div>
    <div class="card">
      <div class="card__label">Total alerts</div>
      <div class="card__value">{{ stats.total }}</div>
      <div class="card__sub">across all endpoints</div>
    </div>
    <div class="card">
      <div class="card__label">Approved</div>
      <div class="card__value card__value--ok">{{ stats.approved }}</div>
      <div class="card__sub">fixes deployed</div>
    </div>
    <div class="card">
      <div class="card__label">Denied</div>
      <div class="card__value card__value--bad">{{ stats.denied }}</div>
      <div class="card__sub">rejected by analyst</div>
    </div>
  </div>
</template>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 20px;
}
.card--accent {
  border-color: color-mix(in srgb, var(--accent) 45%, var(--border));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 12%, transparent);
}
.card__label {
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 500;
}
.card__value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  margin-top: 4px;
}
.card__value--ok {
  color: var(--status-approved);
}
.card__value--bad {
  color: var(--status-denied);
}
.card__sub {
  font-size: 0.75rem;
  color: var(--muted);
  margin-top: 2px;
}
@media (max-width: 860px) {
  .cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 460px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
