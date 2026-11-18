<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Remediation } from '../types'
import { fullTime } from '../time'
import SeverityBadge from './SeverityBadge.vue'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{
  item: Remediation | null
  busy: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'approve', payload: { id: number; script: string }): void
  (e: 'deny', id: number): void
}>()

const editing = ref(false)
const draftScript = ref('')

watch(
  () => props.item,
  (item) => {
    editing.value = false
    draftScript.value = item?.proposed_script ?? ''
  },
  { immediate: true },
)

function toggleEdit() {
  editing.value = !editing.value
  if (!editing.value) {
    draftScript.value = props.item?.proposed_script ?? ''
  }
}

async function copyScript() {
  try {
    await navigator.clipboard.writeText(draftScript.value)
  } catch {
    /* clipboard may be unavailable; ignore */
  }
}
</script>

<template>
  <aside class="detail" :class="{ 'detail--open': item }">
    <template v-if="item">
      <header class="detail__head">
        <div class="detail__head-top">
          <SeverityBadge :severity="item.severity" />
          <StatusBadge :status="item.status" />
          <button class="icon-btn" title="Close" @click="emit('close')">✕</button>
        </div>
        <h2 class="detail__title">{{ item.title }}</h2>
        <div class="detail__meta">
          <span>Remediation #{{ item.id }}</span>
          <span>·</span>
          <span>Event #{{ item.event_id }}</span>
          <span>·</span>
          <span>{{ fullTime(item.created_at) }}</span>
        </div>
      </header>

      <section class="section">
        <h3 class="section__label">LLM analysis</h3>
        <p class="analysis">{{ item.summary || 'No summary provided.' }}</p>
      </section>

      <section class="section">
        <div class="section__row">
          <h3 class="section__label">Proposed remediation script</h3>
          <div class="script-actions">
            <button class="link-btn" @click="copyScript">Copy</button>
            <button class="link-btn" @click="toggleEdit">
              {{ editing ? 'Cancel edit' : 'Modify' }}
            </button>
          </div>
        </div>

        <textarea
          v-if="editing"
          v-model="draftScript"
          class="script-edit"
          spellcheck="false"
          rows="10"
        />
        <pre v-else class="script"><code>{{ draftScript || '# (no script proposed)' }}</code></pre>
        <p v-if="editing" class="edit-note">
          The modified script will be sent to the endpoint when you approve.
        </p>
      </section>

      <section v-if="item.status !== 'pending_review'" class="review-note">
        <StatusBadge :status="item.status" />
        by <strong>{{ item.reviewed_by || 'unknown' }}</strong> · {{ fullTime(item.reviewed_at) }}
      </section>

      <footer v-if="item.status === 'pending_review'" class="actions">
        <button class="btn btn--deny" :disabled="busy" @click="emit('deny', item.id)">
          Deny
        </button>
        <button
          class="btn btn--approve"
          :disabled="busy"
          @click="emit('approve', { id: item.id, script: draftScript })"
        >
          {{ busy ? 'Working…' : 'Approve & deploy' }}
        </button>
      </footer>
    </template>

    <div v-else class="placeholder">
      <div class="placeholder__icon">🛡️</div>
      <p>Select an alert to review the analysis and proposed fix.</p>
    </div>
  </aside>
</template>

<style scoped>
.detail {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  position: sticky;
  top: 20px;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
}
.detail__head-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.icon-btn {
  margin-left: auto;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--muted);
  border-radius: 6px;
  width: 28px;
  height: 28px;
  cursor: pointer;
  font-size: 0.8rem;
}
.icon-btn:hover {
  color: var(--text);
  border-color: var(--muted);
}
.detail__title {
  font-size: 1.15rem;
  margin: 12px 0 6px;
  line-height: 1.3;
}
.detail__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 0.78rem;
  color: var(--muted);
  font-family: var(--mono);
}
.section__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.section__label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  margin: 0 0 8px;
  font-weight: 600;
}
.analysis {
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.55;
  color: var(--text);
}
.script-actions {
  display: flex;
  gap: 12px;
}
.link-btn {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font: inherit;
  font-size: 0.8rem;
  padding: 0;
}
.link-btn:hover {
  text-decoration: underline;
}
.script,
.script-edit {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  font-family: var(--mono);
  font-size: 0.82rem;
  line-height: 1.5;
  color: #d6e2f0;
  overflow-x: auto;
  margin: 0;
}
.script-edit {
  width: 100%;
  resize: vertical;
  box-sizing: border-box;
}
.script-edit:focus {
  outline: none;
  border-color: var(--accent);
}
.edit-note {
  font-size: 0.75rem;
  color: var(--status-pending);
  margin: 8px 0 0;
}
.review-note {
  font-size: 0.82rem;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.actions {
  display: flex;
  gap: 12px;
  margin-top: auto;
  padding-top: 8px;
}
.btn {
  flex: 1;
  padding: 11px 16px;
  border-radius: 8px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: filter 0.12s ease;
}
.btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.btn:not(:disabled):hover {
  filter: brightness(1.1);
}
.btn--approve {
  background: var(--status-approved);
  color: #05140a;
}
.btn--deny {
  background: transparent;
  border-color: color-mix(in srgb, var(--status-denied) 55%, transparent);
  color: var(--status-denied);
}
.placeholder {
  text-align: center;
  color: var(--muted);
  padding: 60px 20px;
}
.placeholder__icon {
  font-size: 2.4rem;
  margin-bottom: 12px;
}
</style>
