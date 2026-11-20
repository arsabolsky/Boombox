<script setup lang="ts">
const props = defineProps<{ severity: string }>()
const label = () => props.severity.charAt(0).toUpperCase() + props.severity.slice(1)
</script>

<template>
  <span class="sev" :class="`sev--${severity.toLowerCase()}`">
    <span class="dot" />
    {{ label() }}
  </span>
</template>

<style scoped>
.sev {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px 2px 8px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid var(--border);
  white-space: nowrap;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}
.sev--critical {
  color: var(--sev-critical);
  background: color-mix(in srgb, var(--sev-critical) 14%, transparent);
  border-color: color-mix(in srgb, var(--sev-critical) 40%, transparent);
}
.sev--high {
  color: var(--sev-high);
  background: color-mix(in srgb, var(--sev-high) 14%, transparent);
  border-color: color-mix(in srgb, var(--sev-high) 40%, transparent);
}
.sev--medium {
  color: var(--sev-medium);
  background: color-mix(in srgb, var(--sev-medium) 14%, transparent);
  border-color: color-mix(in srgb, var(--sev-medium) 40%, transparent);
}
.sev--low {
  color: var(--sev-low);
  background: color-mix(in srgb, var(--sev-low) 14%, transparent);
  border-color: color-mix(in srgb, var(--sev-low) 40%, transparent);
}
</style>
