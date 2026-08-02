<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import type { AssetListFilters, FilterDimension } from '~/utils/filters'

const props = defineProps<{ filters: AssetListFilters }>()
const emit = defineEmits<{
  (e: 'remove', key: FilterDimension): void
  (e: 'clear'): void
}>()

const { categories, statuses, conditions, departments, locations } = useReferenceData()

interface Chip {
  key: FilterDimension
  label: string
}

const chips = computed<Chip[]>(() => {
  const f = props.filters
  const out: Chip[] = []
  if (f.q) out.push({ key: 'q', label: `Search: “${f.q}”` })
  if (f.status) {
    const found = statuses.value.find((s) => s.uuid === f.status || s.code === f.status)
    out.push({ key: 'status', label: `Status: ${found?.label ?? f.status}` })
  }
  if (f.condition) {
    const found = conditions.value.find((c) => c.uuid === f.condition || c.code === f.condition)
    out.push({ key: 'condition', label: `Condition: ${found?.label ?? f.condition}` })
  }
  if (f.category) {
    const found = categories.value.find((c) => c.uuid === f.category || c.code === f.category)
    out.push({ key: 'category', label: `Category: ${found?.name ?? f.category}` })
  }
  if (f.department) {
    const found = departments.value.find((d) => d.uuid === f.department || d.code === f.department)
    out.push({ key: 'department', label: `Department: ${found?.name ?? f.department}` })
  }
  if (f.location) {
    const found = locations.value.find((l) => l.uuid === f.location || l.code === f.location)
    out.push({ key: 'location', label: `Location: ${found?.name ?? f.location}` })
  }
  return out
})
</script>

<template>
  <div v-if="chips.length" class="flex flex-wrap items-center gap-2" aria-label="Active filters">
    <span
      v-for="chip in chips"
      :key="chip.key"
      class="inline-flex items-center gap-1 rounded-full border border-border-strong bg-raised py-1 pl-3 pr-1 text-sm text-ink-secondary"
    >
      {{ chip.label }}
      <button
        type="button"
        class="inline-flex min-h-8 min-w-8 items-center justify-center rounded-full text-muted hover:bg-hover hover:text-ink"
        :aria-label="`Remove filter ${chip.label}`"
        @click="emit('remove', chip.key)"
      >
        <AppIcon name="close" size="sm" />
      </button>
    </span>
    <button
      type="button"
      class="min-h-8 rounded-lg px-2 text-sm font-medium text-accent hover:text-accent-hover"
      @click="emit('clear')"
    >
      Clear all
    </button>
  </div>
</template>
