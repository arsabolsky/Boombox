<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export interface Series {
  key: string
  label: string
  color: string
}

const props = defineProps<{
  data: Record<string, unknown>[]
  series: Series[]
  labelKey: string
  height?: number
}>()

const wrap = ref<HTMLElement | null>(null)
const width = ref(600)
const hover = ref<number | null>(null)
let ro: ResizeObserver | null = null

onMounted(() => {
  if (!wrap.value) return
  width.value = wrap.value.clientWidth
  ro = new ResizeObserver(([entry]) => {
    if (entry) width.value = entry.contentRect.width
  })
  ro.observe(wrap.value)
})
onBeforeUnmount(() => ro?.disconnect())

const H = computed(() => props.height ?? 220)
const PAD = { top: 10, right: 8, bottom: 26, left: 30 }

const val = (row: Record<string, unknown>, key: string) => Number(row[key] ?? 0)
const total = (row: Record<string, unknown>) =>
  props.series.reduce((s, ser) => s + val(row, ser.key), 0)

// "Nice" integer step so ticks are evenly spaced whole numbers.
const step = computed(() => {
  const m = Math.max(1, ...props.data.map(total))
  return m <= 5 ? 1 : m <= 10 ? 2 : m <= 25 ? 5 : m <= 50 ? 10 : Math.ceil(m / 50) * 10
})
const yMax = computed(() => {
  const m = Math.max(1, ...props.data.map(total))
  return Math.ceil(m / step.value) * step.value
})
const ticks = computed(() =>
  Array.from({ length: yMax.value / step.value + 1 }, (_, i) => i * step.value),
)

const plotW = computed(() => Math.max(10, width.value - PAD.left - PAD.right))
const plotH = computed(() => H.value - PAD.top - PAD.bottom)
const band = computed(() => plotW.value / Math.max(1, props.data.length))
const barW = computed(() => Math.min(28, band.value * 0.62))
const y = (v: number) => PAD.top + plotH.value - (v / yMax.value) * plotH.value

const GAP = 2 // surface gap between stacked segments
const R = 4 // rounded data-end

/** Rect with only the top corners rounded (the data end); bottom sits on the baseline. */
function topRounded(x: number, yTop: number, w: number, h: number, r: number) {
  const rr = Math.min(r, h, w / 2)
  return `M${x},${yTop + h}V${yTop + rr}Q${x},${yTop} ${x + rr},${yTop}H${x + w - rr}Q${x + w},${yTop} ${x + w},${yTop + rr}V${yTop + h}Z`
}

const bars = computed(() =>
  props.data.map((row, i) => {
    const cx = PAD.left + band.value * i + band.value / 2
    const x = cx - barW.value / 2
    let acc = 0
    const nonZero = props.series.filter((s) => val(row, s.key) > 0)
    const segs = nonZero.map((s, j) => {
      const v = val(row, s.key)
      const y0 = y(acc)
      const y1 = y(acc + v)
      acc += v
      const isTop = j === nonZero.length - 1
      const h = Math.max(0, y0 - y1 - (j > 0 ? GAP : 0))
      const top = y1
      return {
        key: s.key,
        color: s.color,
        d: isTop ? topRounded(x, top, barW.value, h, R) : `M${x},${top}h${barW.value}v${h}h${-barW.value}Z`,
      }
    })
    return { i, cx, x, segs, label: String(row[props.labelKey] ?? ''), total: total(row) }
  }),
)

// Thin out x-axis labels so they never collide.
const labelEvery = computed(() => Math.max(1, Math.ceil(56 / band.value)))

const tooltip = computed(() => {
  if (hover.value === null) return null
  const row = props.data[hover.value]
  const bar = bars.value[hover.value]
  if (!row || !bar) return null
  const left = Math.min(Math.max(bar.cx, 80), width.value - 80)
  return {
    left,
    label: bar.label,
    total: bar.total,
    rows: [...props.series].reverse().map((s) => ({ ...s, value: val(row, s.key) })),
  }
})
</script>

<template>
  <div class="chart">
    <ul class="legend">
      <li v-for="s in series" :key="s.key">
        <span class="swatch" :style="{ background: s.color }" />{{ s.label }}
      </li>
    </ul>

    <div ref="wrap" class="plot" @mouseleave="hover = null">
      <svg :width="width" :height="H" role="img" :aria-label="`Stacked bar chart of ${series.map((s) => s.label).join(', ')}`">
        <g class="grid">
          <line
            v-for="t in ticks"
            :key="t"
            :x1="PAD.left"
            :x2="width - PAD.right"
            :y1="y(t)"
            :y2="y(t)"
            :class="{ baseline: t === 0 }"
          />
          <text v-for="t in ticks" :key="`l${t}`" :x="PAD.left - 8" :y="y(t)" dy="0.32em" text-anchor="end">
            {{ t }}
          </text>
        </g>

        <g v-for="b in bars" :key="b.i" :class="{ dim: hover !== null && hover !== b.i }" class="bar">
          <path v-for="s in b.segs" :key="s.key" :d="s.d" :fill="s.color" />
        </g>

        <g class="xlabels">
          <text
            v-for="b in bars"
            v-show="b.i % labelEvery === (bars.length - 1) % labelEvery"
            :key="`x${b.i}`"
            :x="b.cx"
            :y="H - 8"
            text-anchor="middle"
          >
            {{ b.label }}
          </text>
        </g>

        <!-- hit targets: full column, wider than the mark -->
        <rect
          v-for="b in bars"
          :key="`h${b.i}`"
          :x="b.cx - band / 2"
          :y="PAD.top"
          :width="band"
          :height="plotH"
          fill="transparent"
          @mouseenter="hover = b.i"
        />
      </svg>

      <div v-if="tooltip" class="tooltip" :style="{ left: tooltip.left + 'px' }">
        <div class="tooltip__title">{{ tooltip.label }}</div>
        <div v-for="r in tooltip.rows" :key="r.key" class="tooltip__row">
          <span class="swatch" :style="{ background: r.color }" />
          <span>{{ r.label }}</span>
          <strong>{{ r.value }}</strong>
        </div>
        <div class="tooltip__row tooltip__total">
          <span />
          <span>Total</span>
          <strong>{{ tooltip.total }}</strong>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.legend {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  gap: 16px;
  font-size: 0.76rem;
  color: var(--muted);
}
.legend li {
  display: flex;
  align-items: center;
  gap: 6px;
}
.swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
}
.plot {
  position: relative;
  width: 100%;
}
svg {
  display: block;
  overflow: visible;
}
.grid line {
  stroke: var(--chart-grid);
  stroke-width: 1;
}
.grid line.baseline {
  stroke: var(--chart-axis);
}
.grid text,
.xlabels text {
  fill: var(--muted);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}
.bar {
  transition: opacity 0.12s ease;
}
.bar.dim {
  opacity: 0.4;
}
.tooltip {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 0.76rem;
  pointer-events: none;
  min-width: 140px;
  box-shadow: 0 6px 20px rgb(0 0 0 / 0.35);
}
.tooltip__title {
  font-weight: 600;
  margin-bottom: 4px;
}
.tooltip__row {
  display: grid;
  grid-template-columns: 10px 1fr auto;
  gap: 8px;
  align-items: center;
  color: var(--muted);
}
.tooltip__row strong {
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.tooltip__total {
  border-top: 1px solid var(--border);
  margin-top: 4px;
  padding-top: 4px;
}
</style>
