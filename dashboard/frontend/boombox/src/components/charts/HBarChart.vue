<script setup lang="ts">
import { computed } from 'vue'

export interface HBarRow {
  label: string
  value: number
  /** Formatted value shown at the bar end; defaults to the raw value. */
  display?: string
  /** Extra line shown on hover. */
  detail?: string
}

const props = defineProps<{
  rows: HBarRow[]
  color?: string
  emptyText?: string
  /** Capitalize labels (for enum-like values such as severities). */
  capitalize?: boolean
}>()

const max = computed(() => Math.max(1e-9, ...props.rows.map((r) => r.value)))
</script>

<template>
  <div class="hbars">
    <p v-if="rows.length === 0" class="empty">{{ emptyText ?? 'No data yet.' }}</p>
    <div
      v-for="r in rows"
      :key="r.label"
      class="row"
      :title="r.detail ? `${r.label}: ${r.display ?? r.value} — ${r.detail}` : `${r.label}: ${r.display ?? r.value}`"
    >
      <span class="label" :class="{ 'label--cap': capitalize }">{{ r.label }}</span>
      <div class="track">
        <div
          class="fill"
          :style="{ width: `${(r.value / max) * 100}%`, background: color ?? 'var(--chart-1)' }"
        />
      </div>
      <span class="value">{{ r.display ?? r.value }}</span>
    </div>
  </div>
</template>

<style scoped>
.hbars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.row {
  display: grid;
  grid-template-columns: minmax(64px, 30%) 1fr 52px;
  align-items: center;
  gap: 12px;
  padding: 5px 6px;
  border-radius: 6px;
}
.row:hover {
  background: color-mix(in srgb, var(--border) 45%, transparent);
}
.label {
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.label--cap {
  text-transform: capitalize;
}
.track {
  height: 10px;
}
.fill {
  height: 100%;
  min-width: 2px;
  border-radius: 0 4px 4px 0;
  transition: width 0.4s ease;
}
.value {
  font-size: 0.8rem;
  color: var(--text);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.empty {
  color: var(--muted);
  font-size: 0.82rem;
  margin: 8px 0;
}
</style>
