<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import FilterControls from '~/components/filters/FilterControls.vue'
import { DEFAULT_FILTERS, type AssetListFilters } from '~/utils/filters'

const props = withDefaults(
  defineProps<{ open?: boolean; filters: AssetListFilters }>(),
  { open: false },
)
const emit = defineEmits<{
  (e: 'apply', patch: Partial<AssetListFilters>): void
  (e: 'close' | 'clear'): void
}>()

const draft = ref<AssetListFilters>({ ...props.filters })
const panelRef = ref<HTMLElement | null>(null)
const titleId = useId()

watch(
  () => props.open,
  async (open) => {
    if (open) {
      draft.value = { ...props.filters }
      await nextTick()
      panelRef.value?.querySelector<HTMLElement>('select, button')?.focus()
    }
  },
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') emit('close')
}

function updateDraft(patch: Partial<AssetListFilters>): void {
  draft.value = { ...draft.value, ...patch }
}

function apply(): void {
  emit('apply', {
    status: draft.value.status,
    condition: draft.value.condition,
    category: draft.value.category,
    department: draft.value.department,
    location: draft.value.location,
  })
  emit('close')
}

function clearDraft(): void {
  draft.value = { ...DEFAULT_FILTERS, q: props.filters.q }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-end justify-center lg:hidden" @keydown="onKeydown">
      <div class="absolute inset-0 bg-canvas/80" aria-hidden="true" @click="emit('close')" />
      <div
        ref="panelRef"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        class="relative flex max-h-[85dvh] w-full flex-col rounded-t-2xl border border-border bg-raised"
      >
        <div class="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 :id="titleId" class="text-base font-semibold text-ink">Filters</h2>
          <button
            type="button"
            class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-ink-secondary hover:bg-hover"
            aria-label="Close filters"
            @click="emit('close')"
          >
            <AppIcon name="close" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-4 py-4">
          <FilterControls :filters="draft" @update="updateDraft" />
        </div>

        <div class="flex gap-2 border-t border-border p-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
          <button
            type="button"
            class="inline-flex min-h-11 flex-1 items-center justify-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
            @click="clearDraft"
          >
            Clear
          </button>
          <button
            type="button"
            class="inline-flex min-h-11 flex-1 items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
            @click="apply"
          >
            Apply filters
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
