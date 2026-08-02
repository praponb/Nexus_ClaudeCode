<script setup lang="ts">
import type { MaintenanceRecord } from '~/types/workflow'
import AppIcon from '~/components/AppIcon.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import EmptyState from '~/components/EmptyState.vue'
import { formatDate, formatMoney, isPastDate } from '~/utils/format'

const props = withDefaults(
  defineProps<{
    records: MaintenanceRecord[]
    showAsset?: boolean
    canComplete?: boolean
  }>(),
  { showAsset: false, canComplete: false },
)

const emit = defineEmits<{ (e: 'complete', record: MaintenanceRecord): void }>()
const { canViewFinance } = usePermissions()

function isOpen(record: MaintenanceRecord): boolean {
  return record.is_open ?? !record.completed_at
}

function isOverdue(record: MaintenanceRecord): boolean {
  return isOpen(record) && isPastDate(record.next_due)
}

function assetInfo(record: MaintenanceRecord): { uuid: string; tag: string; name: string } | null {
  return typeof record.asset === 'object' && record.asset !== null ? record.asset : null
}

const openRecords = computed(() => props.records.filter(isOpen))
const closedRecords = computed(() => props.records.filter((r) => !isOpen(r)))
</script>

<template>
  <div class="space-y-6">
    <section aria-label="Open maintenance work">
      <EmptyState
        v-if="!openRecords.length && !closedRecords.length"
        icon="wrench"
        title="No maintenance records"
        message="Maintenance and repair work recorded for this scope will appear here."
      />
      <ul v-else class="space-y-3">
        <li
          v-for="record in openRecords"
          :key="record.uuid"
          class="rounded-xl border p-4"
          :class="isOverdue(record) ? 'border-warning/50 bg-warning/5' : 'border-border bg-surface'"
        >
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <NuxtLink
                  v-if="showAsset && assetInfo(record)"
                  :to="`/assets/${assetInfo(record)!.uuid}`"
                  class="rounded font-mono text-sm text-accent hover:text-accent-hover"
                >
                  {{ assetInfo(record)!.tag }}
                </NuxtLink>
                <StatusBadge v-if="isOverdue(record)" label="Overdue" code="overdue" size="sm" />
                <StatusBadge v-else label="Open" code="in_progress" treatment-hint="info" size="sm" />
              </div>
              <p class="mt-1 text-sm font-medium text-ink">{{ record.issue }}</p>
              <p class="mt-1 text-xs text-muted">
                <span v-if="record.type">{{ record.type.name }} · </span>
                <span v-if="record.provider">{{ record.provider }} · </span>
                Started {{ formatDate(record.started_at) }}
                <span v-if="record.next_due"> · Next due {{ formatDate(record.next_due) }}</span>
                <span v-if="canViewFinance && record.cost"> · {{ formatMoney(record.cost) }}</span>
              </p>
            </div>
            <button
              v-if="canComplete"
              type="button"
              class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-raised px-3 py-2 text-sm font-medium text-ink hover:bg-hover"
              @click="emit('complete', record)"
            >
              <AppIcon name="check" size="sm" />
              Complete
            </button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="closedRecords.length" aria-label="Maintenance history">
      <h2 class="mb-3 text-sm font-semibold text-muted">Completed</h2>
      <ul class="space-y-3">
        <li v-for="record in closedRecords" :key="record.uuid" class="rounded-xl border border-border bg-surface p-4">
          <div class="flex flex-wrap items-center gap-2">
            <NuxtLink
              v-if="showAsset && assetInfo(record)"
              :to="`/assets/${assetInfo(record)!.uuid}`"
              class="rounded font-mono text-sm text-accent hover:text-accent-hover"
            >
              {{ assetInfo(record)!.tag }}
            </NuxtLink>
            <StatusBadge label="Completed" code="completed" size="sm" />
          </div>
          <p class="mt-1 text-sm text-ink">{{ record.issue }}</p>
          <p v-if="record.result" class="mt-1 text-sm text-ink-secondary">{{ record.result }}</p>
          <p class="mt-1 text-xs text-muted">
            Completed {{ formatDate(record.completed_at) }}
            <span v-if="record.next_due"> · Next due {{ formatDate(record.next_due) }}</span>
          </p>
        </li>
      </ul>
    </section>
  </div>
</template>
