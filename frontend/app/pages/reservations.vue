<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDateTime, isPastDate } from '~/utils/format'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import PaginationControls from '~/components/PaginationControls.vue'

// Reservations list (FR-010 completion, Rev 1.2): scoped list with status and
// overdue filters so overdue checkouts are identifiable at a glance.
definePageMeta({ title: 'Reservations' })
useHead({ title: 'Reservations' })

const service = useReservationsService()
const { canManageAssets, authResolved } = usePermissions()

const page = ref(1)
const statusFilter = ref('')
const overdueOnly = ref(false)

const queryParams = computed(() => {
  const params: Record<string, string | number | boolean> = { page: page.value, page_size: 25 }
  if (statusFilter.value) params.status = statusFilter.value
  if (overdueOnly.value) params.overdue = true
  return params
})

const { data, pending, error, refresh } = await useAsyncData(
  'reservations-list',
  () => service.list(queryParams.value),
  { server: false, watch: [queryParams] },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const items = computed(() => data.value?.results ?? [])

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'requested', label: 'Requested' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'checked_out', label: 'Checked out' },
  { value: 'returned', label: 'Returned' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'expired', label: 'Expired' },
]

function isOverdue(item: { status: string; end_at: string; is_overdue?: boolean }): boolean {
  if (typeof item.is_overdue === 'boolean') return item.is_overdue
  return ['confirmed', 'checked_out', 'requested'].includes(item.status) && isPastDate(item.end_at)
}

function applyFilters(): void {
  page.value = 1
}

const inputClass =
  'h-11 rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent'
</script>

<template>
  <div>
    <PageHeader
      title="Reservations"
      description="Reserved assets and checkouts in your scope, including overdue returns."
    />

    <InlineAlert
      v-if="authResolved && !canManageAssets"
      tone="warning"
      title="Restricted module"
      message="Your role does not include the reservations list."
    />

    <template v-else>
      <form
        class="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4"
        aria-label="Reservation filters"
        @submit.prevent="applyFilters"
      >
        <div>
          <label for="res-status" class="mb-1 block text-sm font-medium text-ink-secondary">Status</label>
          <select id="res-status" v-model="statusFilter" :class="inputClass" @change="applyFilters">
            <option v-for="option in STATUS_OPTIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <label class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-ink-secondary">
          <input v-model="overdueOnly" type="checkbox" class="h-4 w-4 accent-accent" @change="applyFilters" >
          Overdue only
        </label>
        <button
          type="button"
          class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
          @click="statusFilter = ''; overdueOnly = false; applyFilters()"
        >
          Clear
        </button>
      </form>

      <LoadingSkeleton v-if="pending && !items.length" :lines="4" label="Loading reservations…" />
      <InlineAlert
        v-else-if="apiError"
        tone="error"
        title="Reservations could not be loaded"
        :message="apiError.message"
        :correlation-id="apiError.correlationId"
        retry-label="Retry"
        @retry="refresh()"
      />
      <EmptyState
        v-else-if="!items.length"
        icon="clock"
        title="No reservations found"
        :message="overdueOnly || statusFilter
          ? 'No reservations match the current filters.'
          : 'Reserve an asset from its detail page to plan future use.'"
      />

      <template v-else>
        <div class="overflow-x-auto rounded-xl border border-border bg-surface">
          <table class="min-w-full divide-y divide-border text-sm">
            <caption class="sr-only">Reservations in your scope</caption>
            <thead class="bg-raised">
              <tr>
                <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Asset</th>
                <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Requester</th>
                <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Window</th>
                <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Status</th>
                <th scope="col" class="hidden px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted xl:table-cell">Purpose</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border">
              <tr v-for="item in items" :key="item.uuid" class="hover:bg-hover">
                <td class="whitespace-nowrap px-3 py-3">
                  <NuxtLink
                    v-if="item.asset"
                    :to="`/assets/${item.asset.uuid}`"
                    class="rounded font-mono text-sm font-medium text-accent hover:text-accent-hover"
                  >
                    {{ item.asset.tag }}
                  </NuxtLink>
                  <span v-else class="text-muted">—</span>
                  <p v-if="item.asset" class="max-w-48 truncate text-xs text-muted">{{ item.asset.name }}</p>
                </td>
                <td class="whitespace-nowrap px-3 py-3 text-ink-secondary">
                  {{ item.requester?.display_name || '—' }}
                </td>
                <td class="whitespace-nowrap px-3 py-3 text-ink-secondary">
                  {{ formatDateTime(item.start_at) }}<br >
                  <span class="text-muted">→ {{ formatDateTime(item.end_at) }}</span>
                </td>
                <td class="whitespace-nowrap px-3 py-3">
                  <StatusBadge :label="codeToLabel(item.status)" :code="item.status" size="sm" />
                  <p v-if="isOverdue(item)" class="mt-1 flex items-center gap-1 text-xs text-warning">
                    <AppIcon name="warning" size="sm" />
                    Overdue
                  </p>
                </td>
                <td class="hidden max-w-56 px-3 py-3 xl:table-cell">
                  <span class="block truncate text-ink-secondary">{{ item.purpose || '—' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-4">
          <PaginationControls
            :page="page"
            :page-size="25"
            :total="data?.count ?? 0"
            :pending="pending"
            @change="page = $event"
          />
        </div>
      </template>
    </template>
  </div>
</template>
