<script setup lang="ts">
import type { Remediation } from '../types'
import { timeAgo } from '../time'
import SeverityBadge from './SeverityBadge.vue'
import StatusBadge from './StatusBadge.vue'

defineProps<{
  items: Remediation[]
  selectedId: number | null
}>()

defineEmits<{ (e: 'select', item: Remediation): void }>()

/** Short form of a client UUID for when no hostname is known. */
function shortId(id: string | null): string {
  return id ? id.slice(0, 8) : '—'
}
</script>

<template>
  <div class="list">
    <div class="list__head">
      <span>Severity</span>
      <span>Alert</span>
      <span class="col-client">Client</span>
      <span class="col-event">Event</span>
      <span class="col-time">Age</span>
      <span class="col-status">Status</span>
    </div>

    <p v-if="items.length === 0" class="empty">No alerts match this filter.</p>

    <button
      v-for="item in items"
      :key="item.id"
      class="row"
      :class="{ 'row--active': item.id === selectedId }"
      @click="$emit('select', item)"
    >
      <span><SeverityBadge :severity="item.severity" /></span>
      <span class="title">
        <span class="title__text">{{ item.title }}</span>
        <span class="title__sub">{{ item.summary }}</span>
      </span>
      <span class="col-client">
        <span v-if="item.hostname || item.client_id" class="client" :title="item.client_id ?? ''">
          {{ item.hostname ?? shortId(item.client_id) }}
        </span>
        <span v-else class="muted">—</span>
      </span>
      <span class="col-event mono">#{{ item.event_id }}</span>
      <span class="col-time muted">{{ timeAgo(item.created_at) }}</span>
      <span class="col-status"><StatusBadge :status="item.status" /></span>
    </button>
  </div>
</template>

<style scoped>
.list {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}
.list__head,
.row {
  display: grid;
  grid-template-columns: 110px 1fr 130px 70px 80px 120px;
  gap: 12px;
  align-items: center;
  padding: 12px 18px;
  text-align: left;
}
.list__head {
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
  transition: background 0.12s ease;
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
  gap: 2px;
  min-width: 0;
}
.title__text {
  font-weight: 600;
  font-size: 0.9rem;
}
.title__sub {
  font-size: 0.78rem;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mono {
  font-family: var(--mono);
  font-size: 0.82rem;
  color: var(--muted);
}
.col-client {
  min-width: 0;
}
.client {
  font-size: 0.82rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}
.muted {
  color: var(--muted);
  font-size: 0.82rem;
}
.empty {
  padding: 40px;
  text-align: center;
  color: var(--muted);
}
@media (max-width: 720px) {
  .list__head {
    display: none;
  }
  .row {
    grid-template-columns: 1fr auto;
    grid-template-areas:
      'sev status'
      'title title'
      'client event';
    row-gap: 6px;
  }
  .row > :nth-child(1) {
    grid-area: sev;
  }
  .title {
    grid-area: title;
  }
  .col-client {
    grid-area: client;
  }
  .col-event {
    grid-area: event;
    justify-self: end;
  }
  .col-time {
    display: none;
  }
  .col-status {
    grid-area: status;
    justify-self: end;
  }
  .title__sub {
    white-space: normal;
  }
}
</style>
