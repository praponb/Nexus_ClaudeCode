<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDateTime } from '~/utils/format'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import PaginationControls from '~/components/PaginationControls.vue'

// Audit log (FR-025): restricted read for administrators. Append-only and
// hash-chained server-side; there is deliberately no edit/delete surface.
definePageMeta({ title: 'Audit log' })
useHead({ title: 'Audit log' })

const service = useAdminService()

const page = ref(1)
const actionFilter = ref('')
const targetType = ref('')
const correlationId = ref('')
const applied = ref<Record<string, string>>({})

const { data, pending, error, refresh } = await useAsyncData(
  'admin-audit-events',
  () => service.auditEvents({ page: page.value, page_size: 25, ...applied.value }),
  { server: false, watch: [page, applied] },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const events = computed(() => data.value?.results ?? [])

function applyFilters(): void {
  const next: Record<string, string> = {}
  if (actionFilter.value.trim()) next.action = actionFilter.value.trim()
  if (targetType.value.trim()) next.target_type = targetType.value.trim()
  if (correlationId.value.trim()) next.correlation_id = correlationId.value.trim()
  applied.value = next
  page.value = 1
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent'
</script>

<template>
  <div>
    <PageHeader
      title="Audit log"
      description="Tamper-evident record of security and lifecycle events. Entries cannot be edited or deleted."
    />

    <form class="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4" aria-label="Audit filters" @submit.prevent="applyFilters">
      <div>
        <label for="audit-action" class="mb-1 block text-sm font-medium text-ink-secondary">Action</label>
        <input id="audit-action" v-model="actionFilter" type="text" placeholder="asset.update" :class="inputClass" autocomplete="off" >
      </div>
      <div>
        <label for="audit-target" class="mb-1 block text-sm font-medium text-ink-secondary">Target type</label>
        <input id="audit-target" v-model="targetType" type="text" placeholder="asset" :class="inputClass" autocomplete="off" >
      </div>
      <div>
        <label for="audit-correlation" class="mb-1 block text-sm font-medium text-ink-secondary">Correlation ID</label>
        <input id="audit-correlation" v-model="correlationId" type="text" placeholder="UUID" class="font-mono" :class="inputClass" autocomplete="off" >
      </div>
      <button
        type="submit"
        class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
      >
        <AppIcon name="filter" size="sm" />
        Apply
      </button>
    </form>

    <LoadingSkeleton v-if="pending && !events.length" :lines="5" label="Loading audit events…" />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Audit events could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <EmptyState
      v-else-if="!events.length"
      icon="tasks"
      title="No audit events"
      message="No events match the current filters."
    />

    <template v-else>
      <div class="overflow-x-auto rounded-xl border border-border bg-surface">
        <table class="min-w-full divide-y divide-border text-sm">
          <caption class="sr-only">Audit events</caption>
          <thead class="bg-raised">
            <tr>
              <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Time (UTC)</th>
              <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Actor</th>
              <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Action</th>
              <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Target</th>
              <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Outcome</th>
              <th scope="col" class="hidden px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted xl:table-cell">Correlation ID</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="event in events" :key="event.uuid ?? `${event.created_at}-${event.action}`" class="hover:bg-hover">
              <td class="whitespace-nowrap px-3 py-3 text-muted">{{ formatDateTime(event.created_at) }}</td>
              <td class="whitespace-nowrap px-3 py-3 text-ink-secondary">
                {{ event.actor }}
                <span v-if="event.actor_type && event.actor_type !== 'user'" class="ml-1 rounded-full border border-border-strong px-1.5 py-0.5 text-[10px] uppercase text-faint">
                  {{ codeToLabel(event.actor_type) }}
                </span>
              </td>
              <td class="whitespace-nowrap px-3 py-3 font-mono text-xs text-ink">{{ event.action }}</td>
              <td class="whitespace-nowrap px-3 py-3 text-ink-secondary">
                {{ event.target_type || '—' }}<span v-if="event.target_uuid" class="font-mono text-xs text-muted"> · {{ event.target_uuid.slice(0, 8) }}…</span>
              </td>
              <td class="whitespace-nowrap px-3 py-3" :class="event.outcome === 'failure' ? 'text-danger' : 'text-ink-secondary'">
                {{ codeToLabel(event.outcome || 'success') }}
              </td>
              <td class="hidden whitespace-nowrap px-3 py-3 font-mono text-xs text-muted xl:table-cell">
                {{ event.correlation_id || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-4">
        <PaginationControls :page="page" :page-size="25" :total="data?.count ?? 0" :pending="pending" @change="page = $event" />
      </div>
    </template>
  </div>
</template>
