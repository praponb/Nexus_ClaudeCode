<script setup lang="ts">
import { ApiError, isNotFoundError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDateTime } from '~/utils/format'
import PageHeader from '~/components/PageHeader.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import { useImportsService } from '~/services/api/imports'

definePageMeta({ title: 'Import detail' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const service = useImportsService()

const { data: job, pending, error, refresh } = await useAsyncData(
  `import-${uuid.value}`,
  () => service.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

// Poll while the job is active.
let pollTimer: ReturnType<typeof setInterval> | undefined
watch(
  () => job.value?.status,
  (status) => {
    const active = status && ['queued', 'validating', 'processing'].includes(status)
    if (active && !pollTimer) {
      pollTimer = setInterval(() => void refresh(), 2500)
    } else if (!active && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = undefined
    }
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})

useHead(() => ({ title: job.value?.filename ? `Import · ${job.value.filename}` : 'Import detail' }))

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
</script>

<template>
  <div class="max-w-3xl">
    <PageHeader title="Import detail" :description="job?.filename || ''">
      <template #breadcrumbs>
        <ol class="flex items-center gap-1">
          <li><NuxtLink to="/imports" class="rounded hover:text-ink">Imports</NuxtLink></li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" class="text-ink-secondary">Detail</li>
        </ol>
      </template>
    </PageHeader>

    <LoadingSkeleton v-if="pending && !job" :lines="3" label="Loading import…" />
    <EmptyState
      v-else-if="apiError && isNotFoundError(apiError)"
      icon="search"
      title="Import not found"
      message="This import job does not exist or is outside your scope."
      action-to="/imports"
      action-label="Back to imports"
    />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Import could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />

    <div v-else-if="job" class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <StatusBadge :label="codeToLabel(job.status)" :code="job.status" />
        <p class="text-xs text-muted">Started {{ formatDateTime(job.created_at) }}</p>
      </div>

      <InlineAlert
        v-if="job.status === 'failed'"
        tone="error"
        title="Import failed"
        :message="job.error || 'The import could not be completed.'"
        :correlation-id="job.correlation_id"
      />

      <dl v-if="job.counts" class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div class="rounded-lg bg-input p-3 text-center">
          <dt class="text-xs text-success">Created</dt>
          <dd class="text-xl font-bold text-ink">{{ job.counts.created }}</dd>
        </div>
        <div class="rounded-lg bg-input p-3 text-center">
          <dt class="text-xs text-info">Updated</dt>
          <dd class="text-xl font-bold text-ink">{{ job.counts.updated }}</dd>
        </div>
        <div class="rounded-lg bg-input p-3 text-center">
          <dt class="text-xs text-muted">Skipped</dt>
          <dd class="text-xl font-bold text-ink">{{ job.counts.skipped }}</dd>
        </div>
        <div class="rounded-lg bg-input p-3 text-center">
          <dt class="text-xs text-danger">Failed</dt>
          <dd class="text-xl font-bold text-ink">{{ job.counts.failed }}</dd>
        </div>
      </dl>

      <p v-if="['queued', 'validating', 'processing'].includes(job.status)" class="text-sm text-muted" role="status">
        This import is still running — the page refreshes automatically.
      </p>

      <NuxtLink
        to="/imports"
        class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-raised px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
      >
        Back to imports
      </NuxtLink>
    </div>
  </div>
</template>
