<script setup lang="ts">
import type { HistoryEvent } from '~/types/api'
import AppIcon from '~/components/AppIcon.vue'
import type { IconName } from '~/utils/icons'
import { formatDateTime } from '~/utils/format'

const props = defineProps<{
  events: HistoryEvent[]
}>()

/** Reverse chronological order (layout.md §12.3). */
const sorted = computed(() =>
  [...props.events].sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()),
)

function iconFor(type: string | undefined | null): IconName {
  const t = (type ?? '').toLowerCase()
  if (t.includes('creat') || t.includes('regist')) return 'plus'
  if (t.includes('updat') || t.includes('edit')) return 'pencil'
  if (t.includes('assign')) return 'user-circle'
  if (t.includes('transfer')) return 'refresh'
  if (t.includes('return')) return 'back'
  if (t.includes('status')) return 'tag'
  if (t.includes('audit') || t.includes('login')) return 'info'
  return 'clock'
}

function hasDetails(event: HistoryEvent): boolean {
  return Boolean(event.details && Object.keys(event.details).length)
}
</script>

<template>
  <ol v-if="sorted.length" class="relative space-y-4 border-l border-border pl-6">
    <li v-for="event in sorted" :key="event.uuid" class="relative">
      <span class="absolute -left-[31px] flex h-6 w-6 items-center justify-center rounded-full border border-border bg-raised text-muted">
        <AppIcon :name="iconFor(event.type)" size="sm" />
      </span>
      <div class="rounded-lg border border-border bg-surface p-3">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <p class="text-sm font-semibold capitalize text-ink">{{ (event.type ?? '').replace(/_/g, ' ') }}</p>
          <time :datetime="event.occurred_at" class="text-xs text-muted">{{ formatDateTime(event.occurred_at) }}</time>
        </div>
        <p class="mt-1 text-sm text-ink-secondary">{{ event.summary }}</p>
        <p class="mt-1 text-xs text-muted">By {{ event.actor }}</p>
        <details v-if="hasDetails(event)" class="mt-2">
          <summary class="cursor-pointer rounded text-xs font-medium text-accent hover:text-accent-hover">
            Show details
          </summary>
          <dl class="mt-2 space-y-1 rounded-lg bg-input p-3 text-xs">
            <div v-for="(value, key) in event.details" :key="key" class="flex gap-2">
              <dt class="shrink-0 font-medium capitalize text-muted">{{ String(key).replace(/_/g, ' ') }}</dt>
              <dd class="break-words text-ink-secondary">{{ value }}</dd>
            </div>
          </dl>
        </details>
      </div>
    </li>
  </ol>
</template>
