<script setup lang="ts">
import { computed } from 'vue'
import type { Remediation, Severity } from '../types'

const props = defineProps<{ items: Remediation[] }>()

const ORDER: Severity[] = ['critical', 'high', 'medium', 'low']

const rows = computed(() => {
  const max = Math.max(1, ...ORDER.map((s) => count(s)))
  return ORDER.map((s) => ({
    severity: s,
    count: count(s),
    pct: (count(s) / max) * 100,
  }))
})

function count(s: Severity): number {
  return props.items.filter((r) => r.severity === s).length
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Alerts by severity</h2>
    <div class="bars">
      <div v-for="row in rows" :key="row.severity" class="bar-row">
        <span class="bar-label" :class="`c--${row.severity}`">{{ row.severity }}</span>
        <div class="track">
          <div class="fill" :class="`b--${row.severity}`" :style="{ width: row.pct + '%' }" />
        </div>
        <span class="bar-count">{{ row.count }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 20px;
}
.panel__title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 16px;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bar-row {
  display: grid;
  grid-template-columns: 64px 1fr 24px;
  align-items: center;
  gap: 12px;
}
.bar-label {
  font-size: 0.75rem;
  text-transform: capitalize;
  font-weight: 600;
}
.track {
  height: 8px;
  background: color-mix(in srgb, var(--border) 60%, transparent);
  border-radius: 999px;
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}
.bar-count {
  font-size: 0.8rem;
  color: var(--muted);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.c--critical,
.b--critical {
  color: var(--sev-critical);
}
.c--high,
.b--high {
  color: var(--sev-high);
}
.c--medium,
.b--medium {
  color: var(--sev-medium);
}
.c--low,
.b--low {
  color: var(--sev-low);
}
.b--critical {
  background: var(--sev-critical);
}
.b--high {
  background: var(--sev-high);
}
.b--medium {
  background: var(--sev-medium);
}
.b--low {
  background: var(--sev-low);
}
</style>
