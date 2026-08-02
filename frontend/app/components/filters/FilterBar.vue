<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import FilterControls from '~/components/filters/FilterControls.vue'
import FilterChips from '~/components/filters/FilterChips.vue'
import { hasActiveFilters, type AssetListFilters, type FilterDimension } from '~/utils/filters'

const props = withDefaults(
  defineProps<{
    filters: AssetListFilters
    activeCount: number
    resultCount?: number | null
    pending?: boolean
  }>(),
  { resultCount: null, pending: false },
)

const emit = defineEmits<{
  (e: 'update', patch: Partial<AssetListFilters>): void
  (e: 'clear' | 'openDrawer'): void
}>()

const searchText = ref(props.filters.q)
let debounceTimer: ReturnType<typeof setTimeout> | undefined

watch(
  () => props.filters.q,
  (value) => {
    searchText.value = value
  },
)

watch(searchText, (value) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (value === props.filters.q) return
  debounceTimer = setTimeout(() => emit('update', { q: value.trim() }), 300)
})

function removeChip(key: FilterDimension): void {
  emit('update', { [key]: '' })
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input pl-9 pr-3 text-sm text-ink placeholder:text-faint focus:border-accent'
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center gap-2">
      <div class="relative min-w-0 flex-1">
        <AppIcon name="search" size="sm" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <label for="asset-filter-search" class="sr-only">Filter assets by tag, serial, name, model, custodian, or location</label>
        <input
          id="asset-filter-search"
          v-model="searchText"
          type="search"
          placeholder="Filter by tag, serial, name…"
          :class="inputClass"
          autocomplete="off"
        >
      </div>
      <button
        type="button"
        class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-hover lg:hidden"
        :aria-label="activeCount ? `Open filters, ${activeCount} active` : 'Open filters'"
        @click="emit('openDrawer')"
      >
        <AppIcon name="filter" size="sm" />
        Filters
        <span
          v-if="activeCount"
          class="flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-xs font-bold text-on-accent"
        >
          {{ activeCount }}
        </span>
      </button>
    </div>

    <div class="hidden lg:block">
      <FilterControls :filters="filters" @update="(patch) => emit('update', patch)" />
    </div>

    <div class="flex flex-wrap items-center justify-between gap-2">
      <FilterChips :filters="filters" @remove="removeChip" @clear="emit('clear')" />
      <p v-if="!hasActiveFilters(filters) && resultCount === null" class="sr-only">No filters applied.</p>
    </div>
  </div>
</template>
