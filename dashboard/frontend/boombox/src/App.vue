<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { load, store } from './store'
import ReviewView from './views/ReviewView.vue'
import BacklogView from './views/BacklogView.vue'
import DashboardView from './views/DashboardView.vue'

type Page = 'review' | 'backlog' | 'dashboard'

const PAGES: { key: Page; label: string }[] = [
  { key: 'review', label: 'Review' },
  { key: 'backlog', label: 'Backlog' },
  { key: 'dashboard', label: 'Dashboard' },
]

// Tiny hash router (#/review, #/backlog, #/dashboard) so pages are linkable
// and the back button works, without pulling in vue-router.
function fromHash(): Page {
  const h = window.location.hash.replace(/^#\/?/, '')
  return PAGES.some((p) => p.key === h) ? (h as Page) : 'review'
}
const page = ref<Page>(fromHash())
const onHash = () => (page.value = fromHash())

onMounted(() => {
  window.addEventListener('hashchange', onHash)
  load()
})
onBeforeUnmount(() => window.removeEventListener('hashchange', onHash))

const pendingCount = computed(
  () => store.items.filter((r) => r.status === 'pending_review').length,
)

const SUBTITLES: Record<Page, string> = {
  review: 'Approve or deny proposed fixes for recent alerts',
  backlog: 'Every fix that has been approved or denied',
  dashboard: 'System activity and review metrics',
}
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <span class="brand__mark">◈</span>
        <div>
          <h1 class="brand__name">Boombox</h1>
          <p class="brand__tag">{{ SUBTITLES[page] }}</p>
        </div>
      </div>

      <nav class="nav" aria-label="Pages">
        <a
          v-for="p in PAGES"
          :key="p.key"
          :href="`#/${p.key}`"
          class="nav__link"
          :class="{ 'nav__link--active': page === p.key }"
          :aria-current="page === p.key ? 'page' : undefined"
        >
          {{ p.label }}
          <span v-if="p.key === 'review' && pendingCount" class="nav__badge">{{ pendingCount }}</span>
        </a>
      </nav>

      <div class="topbar__right">
        <label class="reviewer">
          <span>Analyst</span>
          <input v-model="store.reviewer" type="text" spellcheck="false" />
        </label>

        <label class="toggle" :class="{ 'toggle--on': store.autoApprove }">
          <input v-model="store.autoApprove" type="checkbox" />
          <span class="toggle__track"><span class="toggle__thumb" /></span>
          <span class="toggle__label">
            Auto-approve
            <small>LLM-as-judge</small>
          </span>
        </label>

        <button class="refresh" :disabled="store.loading" title="Refresh" @click="load">⟳</button>
      </div>
    </header>

    <div v-if="store.usingMock" class="banner banner--info">
      Showing demo data — the Boombox API isn't reachable at
      <code>/api/v1</code>. Approve/deny are simulated locally.
    </div>
    <div v-if="store.error" class="banner banner--error">{{ store.error }}</div>
    <div v-if="store.autoApprove" class="banner banner--warn">
      Auto-approve is on. New remediations rated low-risk by the LLM judge will be
      deployed without manual review.
    </div>

    <main>
      <ReviewView v-if="page === 'review'" />
      <BacklogView v-else-if="page === 'backlog'" />
      <DashboardView v-else />
    </main>
  </div>
</template>

<style scoped>
.app {
  max-width: 1320px;
  margin: 0 auto;
  padding: 20px;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 16px 24px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand__mark {
  font-size: 1.6rem;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent);
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 10px;
}
.brand__name {
  font-size: 1.25rem;
  margin: 0;
  line-height: 1.1;
}
.brand__tag {
  margin: 2px 0 0;
  font-size: 0.78rem;
  color: var(--muted);
}
.nav {
  display: flex;
  gap: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 4px;
  border-radius: 10px;
}
.nav__link {
  color: var(--muted);
  text-decoration: none;
  padding: 7px 16px;
  border-radius: 7px;
  font-size: 0.88rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 7px;
}
.nav__link:hover {
  color: var(--text);
}
.nav__link--active {
  background: color-mix(in srgb, var(--accent) 16%, transparent);
  color: var(--text);
}
.nav__badge {
  font-size: 0.7rem;
  font-weight: 600;
  background: color-mix(in srgb, var(--status-pending) 22%, transparent);
  color: var(--status-pending);
  padding: 0 7px;
  border-radius: 999px;
}
.topbar__right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.reviewer {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 0.7rem;
  color: var(--muted);
}
.reviewer input {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 6px 10px;
  color: var(--text);
  font: inherit;
  font-size: 0.85rem;
  width: 120px;
}
.reviewer input:focus {
  outline: none;
  border-color: var(--accent);
}
.toggle {
  display: flex;
  align-items: center;
  gap: 9px;
  cursor: pointer;
  user-select: none;
}
.toggle input {
  display: none;
}
.toggle__track {
  width: 38px;
  height: 22px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--border) 80%, transparent);
  border: 1px solid var(--border);
  position: relative;
  transition: background 0.15s ease;
  flex-shrink: 0;
}
.toggle__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--muted);
  transition: transform 0.15s ease, background 0.15s ease;
}
.toggle--on .toggle__track {
  background: color-mix(in srgb, var(--status-pending) 55%, transparent);
}
.toggle--on .toggle__thumb {
  transform: translateX(16px);
  background: #fff;
}
.toggle__label {
  font-size: 0.82rem;
  font-weight: 500;
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}
.toggle__label small {
  color: var(--muted);
  font-size: 0.68rem;
}
.refresh {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  width: 38px;
  height: 38px;
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
}
.refresh:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.banner {
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.82rem;
  margin-bottom: 12px;
}
.banner code {
  font-family: var(--mono);
}
.banner--info {
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
}
.banner--warn {
  background: color-mix(in srgb, var(--status-pending) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--status-pending) 35%, transparent);
  color: var(--status-pending);
}
.banner--error {
  background: color-mix(in srgb, var(--status-denied) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--status-denied) 35%, transparent);
  color: var(--status-denied);
}
@media (max-width: 720px) {
  .topbar__right {
    margin-left: 0;
  }
}
</style>
