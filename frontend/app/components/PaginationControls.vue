<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '~/components/AppIcon.vue'

const props = withDefaults(
  defineProps<{
    page: number
    pageSize: number
    total: number
    pending?: boolean
  }>(),
  { pending: false },
)

const emit = defineEmits<{ (e: 'change', page: number): void }>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

/** Compact numbered window for desktop; prev/next only on mobile. */
const pageWindow = computed<(number | 'gap')[]>(() => {
  const pages = totalPages.value
  const current = props.page
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1)
  const set = new Set<number>([1, pages, current - 1, current, current + 1])
  const sorted = [...set].filter((p) => p >= 1 && p <= pages).sort((a, b) => a - b)
  const out: (number | 'gap')[] = []
  let prev = 0
  for (const p of sorted) {
    if (prev && p - prev > 1) out.push('gap')
    out.push(p)
    prev = p
  }
  return out
})

function go(page: number): void {
  if (page < 1 || page > totalPages.value || page === props.page || props.pending) return
  emit('change', page)
}

const btnClass =
  'inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-border bg-surface px-2 text-sm text-ink-secondary hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-9 sm:min-w-9'
</script>

<template>
  <nav v-if="total > 0" class="flex items-center justify-between gap-2" aria-label="Pagination">
    <button type="button" :class="btnClass" :disabled="page <= 1 || pending" aria-label="Previous page" @click="go(page - 1)">
      <AppIcon name="chevron-left" size="sm" />
      <span class="ml-1 sm:hidden">Previous</span>
    </button>

    <div class="hidden items-center gap-1 sm:flex">
      <template v-for="(p, i) in pageWindow" :key="i">
        <span v-if="p === 'gap'" class="px-1 text-muted" aria-hidden="true">…</span>
        <button
          v-else
          type="button"
          :class="[btnClass, p === page ? 'border-accent bg-accent/10 text-accent' : '']"
          :aria-current="p === page ? 'page' : undefined"
          :aria-label="`Page ${p}`"
          :disabled="pending"
          @click="go(p)"
        >
          {{ p }}
        </button>
      </template>
    </div>
    <p class="text-sm text-muted sm:hidden" aria-hidden="true">Page {{ page }} of {{ totalPages }}</p>

    <button
      type="button"
      :class="btnClass"
      :disabled="page >= totalPages || pending"
      aria-label="Next page"
      @click="go(page + 1)"
    >
      <span class="mr-1 sm:hidden">Next</span>
      <AppIcon name="chevron-right" size="sm" />
    </button>
  </nav>
</template>
