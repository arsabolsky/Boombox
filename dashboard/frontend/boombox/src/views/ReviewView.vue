<script setup lang="ts">
import { computed, ref } from 'vue'
import { approve, deny, saveScript, SEVERITY_RANK, store } from '../store'
import SummaryCards from '../components/SummaryCards.vue'
import RemediationList from '../components/RemediationList.vue'
import RemediationDetail from '../components/RemediationDetail.vue'

const selectedId = ref<number | null>(null)

// Pending fixes, worst severity first, then newest.
const pending = computed(() =>
  store.items
    .filter((r) => r.status === 'pending_review')
    .sort((a, b) => {
      const s = (SEVERITY_RANK[a.severity] ?? 9) - (SEVERITY_RANK[b.severity] ?? 9)
      if (s !== 0) return s
      return (b.created_at ?? '').localeCompare(a.created_at ?? '')
    }),
)

// Keep the just-reviewed item visible in the detail panel (showing its new
// status) even though it has dropped out of the pending list.
const selected = computed(
  () => store.items.find((r) => r.id === selectedId.value) ?? null,
)

async function onApprove({ id, script }: { id: number; script: string }) {
  // Persist any inline edit to the script before approving so the deployed fix
  // matches what the analyst sees.
  const current = store.items.find((r) => r.id === id)
  if (current && script !== (current.proposed_script ?? '')) {
    const ok = await saveScript(id, script)
    if (!ok) return
  }
  await approve(id)
}
async function onDeny(id: number) {
  await deny(id)
}
async function onSave({ id, script }: { id: number; script: string }) {
  await saveScript(id, script)
}
</script>

<template>
  <div class="grid">
    <section class="left">
      <SummaryCards :items="store.items" />

      <div class="section-head">
        <h2>Awaiting review</h2>
        <span class="count">{{ pending.length }}</span>
        <span class="hint">Sorted by severity, then newest</span>
      </div>

      <p v-if="store.loading" class="loading">Loading alerts…</p>
      <div v-else-if="pending.length === 0" class="empty">
        <strong>Queue is clear.</strong>
        <span>Every proposed fix has been reviewed. Past decisions are in the Backlog.</span>
      </div>
      <RemediationList
        v-else
        :items="pending"
        :selected-id="selectedId"
        @select="(item) => (selectedId = item.id)"
      />
    </section>

    <section class="right">
      <RemediationDetail
        :item="selected"
        :busy="store.busy"
        @close="selectedId = null"
        @approve="onApprove"
        @deny="onDeny"
        @save="onSave"
      />
    </section>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 20px;
  align-items: start;
}
.left,
.right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.section-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.section-head h2 {
  font-size: 1rem;
  margin: 0;
}
.count {
  font-size: 0.72rem;
  background: color-mix(in srgb, var(--status-pending) 18%, transparent);
  color: var(--status-pending);
  padding: 1px 8px;
  border-radius: 999px;
  font-weight: 600;
}
.hint {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--muted);
}
.loading {
  color: var(--muted);
  padding: 40px;
  text-align: center;
}
.empty {
  background: var(--surface);
  border: 1px dashed var(--border);
  border-radius: 12px;
  padding: 36px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--muted);
  font-size: 0.88rem;
}
.empty strong {
  color: var(--text);
}
@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
