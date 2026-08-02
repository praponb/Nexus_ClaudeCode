<script setup lang="ts">
import { codeToLabel } from '~/utils/status'
import { formatCount } from '~/utils/format'
import type { StocktakeSession } from '~/types/workflow'

const props = defineProps<{ session: StocktakeSession }>()

interface ProgressEntry {
  key: string
  count: number
}

const entries = computed<ProgressEntry[]>(() =>
  Object.entries(props.session.progress ?? {}).map(([key, count]) => ({ key, count })),
)

const expected = computed(
  () => props.session.progress?.expected ?? props.session.progress?.total ?? 0,
)
const observed = computed(
  () =>
    props.session.progress?.observed ??
    props.session.progress?.found ??
    props.session.observations?.length ??
    0,
)
const percent = computed(() =>
  expected.value > 0 ? Math.min(100, Math.round((observed.value / expected.value) * 100)) : 0,
)
</script>

<template>
  <div class="rounded-xl border border-border bg-surface p-4 sm:p-6">
    <div class="flex items-center justify-between text-sm">
      <span class="font-medium text-ink">Progress</span>
      <span class="text-muted">
        {{ formatCount(observed) }} of {{ formatCount(expected) }} observed ({{ percent }}%)
      </span>
    </div>
    <div
      class="mt-2 h-3 rounded-full bg-input"
      role="progressbar"
      :aria-valuenow="percent"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="`Stocktake progress: ${percent} percent observed`"
    >
      <div class="h-3 rounded-full bg-accent transition-[width]" :style="{ width: `${percent}%` }" />
    </div>

    <dl v-if="entries.length" class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
      <div v-for="entry in entries" :key="entry.key" class="rounded-lg bg-input p-2 text-center">
        <dt class="text-xs text-muted">{{ codeToLabel(entry.key) }}</dt>
        <dd class="text-lg font-bold text-ink">{{ formatCount(entry.count) }}</dd>
      </div>
    </dl>
  </div>
</template>
