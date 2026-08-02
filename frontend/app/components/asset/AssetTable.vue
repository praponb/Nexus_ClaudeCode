<script setup lang="ts">
import type { AssetSummary } from '~/types/api'
import AppIcon from '~/components/AppIcon.vue'
import AssetStatusBadge from '~/components/asset/AssetStatusBadge.vue'
import AssetConditionBadge from '~/components/asset/AssetConditionBadge.vue'
import { formatDate } from '~/utils/format'

const props = withDefaults(
  defineProps<{
    items: AssetSummary[]
    ordering?: string
    caption?: string
  }>(),
  { ordering: '', caption: 'Asset register results' },
)

const emit = defineEmits<{ (e: 'sort', ordering: string): void }>()

interface Column {
  key: string
  label: string
  sortable?: boolean
  class?: string
}

const columns: Column[] = [
  { key: 'tag', label: 'Asset tag', sortable: true },
  { key: 'name', label: 'Name', sortable: true },
  { key: 'category', label: 'Category' },
  { key: 'status', label: 'Status' },
  { key: 'condition', label: 'Condition' },
  { key: 'custodian', label: 'Custodian' },
  { key: 'department', label: 'Department', class: 'hidden xl:table-cell' },
  { key: 'location', label: 'Location', class: 'hidden xl:table-cell' },
  { key: 'updated_at', label: 'Updated', sortable: true },
]

function ariaSort(key: string): 'ascending' | 'descending' | 'none' {
  if (props.ordering === key) return 'ascending'
  if (props.ordering === `-${key}`) return 'descending'
  return 'none'
}

function toggleSort(key: string): void {
  emit('sort', props.ordering === key ? `-${key}` : key)
}
</script>

<template>
  <div class="overflow-x-auto rounded-xl border border-border bg-surface">
    <table class="min-w-full divide-y divide-border text-sm">
      <caption class="sr-only">{{ caption }}</caption>
      <thead class="sticky top-0 bg-raised">
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            scope="col"
            class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted"
            :class="col.class"
            :aria-sort="col.sortable ? ariaSort(col.key) : undefined"
          >
            <button
              v-if="col.sortable"
              type="button"
              class="inline-flex items-center gap-1 rounded hover:text-ink"
              @click="toggleSort(col.key)"
            >
              {{ col.label }}
              <AppIcon
                v-if="ariaSort(col.key) !== 'none'"
                :name="ariaSort(col.key) === 'ascending' ? 'chevron-down' : 'chevron-right'"
                size="sm"
                class="text-accent"
              />
              <span v-if="ariaSort(col.key) !== 'none'" class="sr-only">
                (sorted {{ ariaSort(col.key) }})
              </span>
            </button>
            <template v-else>{{ col.label }}</template>
          </th>
          <th scope="col" class="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">
            <span class="sr-only">Row actions</span>
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr v-for="asset in items" :key="asset.uuid" class="hover:bg-hover">
          <td class="whitespace-nowrap px-3 py-3">
            <NuxtLink
              :to="`/assets/${asset.uuid}`"
              class="rounded font-mono text-sm font-medium text-accent hover:text-accent-hover"
            >
              {{ asset.tag }}
            </NuxtLink>
          </td>
          <td class="max-w-56 px-3 py-3">
            <NuxtLink :to="`/assets/${asset.uuid}`" class="block truncate rounded font-medium text-ink hover:text-accent">
              {{ asset.name }}
            </NuxtLink>
            <p v-if="asset.warnings?.length" class="mt-0.5 flex items-center gap-1 text-xs text-warning">
              <AppIcon name="warning" size="sm" />
              {{ asset.warnings[0] }}
            </p>
          </td>
          <td class="whitespace-nowrap px-3 py-3 text-ink-secondary">{{ asset.category?.name || '—' }}</td>
          <td class="whitespace-nowrap px-3 py-3"><AssetStatusBadge :status="asset.status" /></td>
          <td class="whitespace-nowrap px-3 py-3"><AssetConditionBadge :condition="asset.condition" /></td>
          <td class="whitespace-nowrap px-3 py-3 text-ink-secondary">{{ asset.custodian?.display_name || '—' }}</td>
          <td class="hidden whitespace-nowrap px-3 py-3 text-ink-secondary xl:table-cell">{{ asset.department?.name || '—' }}</td>
          <td class="hidden whitespace-nowrap px-3 py-3 text-ink-secondary xl:table-cell">{{ asset.location?.name || '—' }}</td>
          <td class="whitespace-nowrap px-3 py-3 text-muted">{{ formatDate(asset.updated_at) }}</td>
          <td class="whitespace-nowrap px-3 py-3 text-right">
            <NuxtLink
              :to="`/assets/${asset.uuid}`"
              class="inline-flex min-h-11 items-center rounded-lg px-3 py-1 text-sm font-medium text-accent hover:bg-hover sm:min-h-0"
              :aria-label="`View asset ${asset.tag}`"
            >
              View
            </NuxtLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
