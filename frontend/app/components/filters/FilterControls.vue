<script setup lang="ts">
import type { AssetListFilters } from '~/utils/filters'

defineProps<{ filters: AssetListFilters }>()
const emit = defineEmits<{ (e: 'update', patch: Partial<AssetListFilters>): void }>()

const { categories, statuses, conditions, departments, locations } = useReferenceData()

type SelectKey = 'status' | 'condition' | 'category' | 'department' | 'location'

function onSelect(key: SelectKey, event: Event): void {
  emit('update', { [key]: (event.target as HTMLSelectElement).value })
}

const selectClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent sm:h-10'
</script>

<template>
  <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
    <div>
      <label for="filter-status" class="mb-1 block text-xs font-medium text-muted">Status</label>
      <select id="filter-status" :value="filters.status" :class="selectClass" @change="onSelect('status', $event)">
        <option value="">All statuses</option>
        <option v-for="s in statuses" :key="s.uuid" :value="s.uuid">{{ s.label }}</option>
      </select>
    </div>
    <div>
      <label for="filter-condition" class="mb-1 block text-xs font-medium text-muted">Condition</label>
      <select id="filter-condition" :value="filters.condition" :class="selectClass" @change="onSelect('condition', $event)">
        <option value="">All conditions</option>
        <option v-for="c in conditions" :key="c.uuid" :value="c.uuid">{{ c.label }}</option>
      </select>
    </div>
    <div>
      <label for="filter-category" class="mb-1 block text-xs font-medium text-muted">Category</label>
      <select id="filter-category" :value="filters.category" :class="selectClass" @change="onSelect('category', $event)">
        <option value="">All categories</option>
        <option v-for="c in categories" :key="c.uuid" :value="c.uuid">{{ c.name }}</option>
      </select>
    </div>
    <div>
      <label for="filter-department" class="mb-1 block text-xs font-medium text-muted">Department</label>
      <select id="filter-department" :value="filters.department" :class="selectClass" @change="onSelect('department', $event)">
        <option value="">All departments</option>
        <option v-for="d in departments" :key="d.uuid" :value="d.uuid">{{ d.name }}</option>
      </select>
    </div>
    <div>
      <label for="filter-location" class="mb-1 block text-xs font-medium text-muted">Location</label>
      <select id="filter-location" :value="filters.location" :class="selectClass" @change="onSelect('location', $event)">
        <option value="">All locations</option>
        <option v-for="l in locations" :key="l.uuid" :value="l.uuid">{{ l.name }}</option>
      </select>
    </div>
  </div>
</template>
