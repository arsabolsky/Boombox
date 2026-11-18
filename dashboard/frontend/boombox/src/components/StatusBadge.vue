<script setup lang="ts">
const props = defineProps<{ status: string }>()
const LABELS: Record<string, string> = {
  pending_review: 'Pending review',
  approved: 'Approved',
  denied: 'Denied',
}
const label = () => LABELS[props.status] ?? props.status
</script>

<template>
  <span class="status" :class="`status--${status.toLowerCase()}`">{{ label() }}</span>
</template>

<style scoped>
.status {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  border: 1px solid var(--border);
  white-space: nowrap;
}
.status--pending_review {
  color: var(--status-pending);
  background: color-mix(in srgb, var(--status-pending) 12%, transparent);
  border-color: color-mix(in srgb, var(--status-pending) 35%, transparent);
}
.status--approved {
  color: var(--status-approved);
  background: color-mix(in srgb, var(--status-approved) 12%, transparent);
  border-color: color-mix(in srgb, var(--status-approved) 35%, transparent);
}
.status--denied {
  color: var(--status-denied);
  background: color-mix(in srgb, var(--status-denied) 12%, transparent);
  border-color: color-mix(in srgb, var(--status-denied) 35%, transparent);
}
</style>
