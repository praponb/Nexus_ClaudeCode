<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDateTime } from '~/utils/format'
import type { ExportJob } from '~/types/workflow'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'

// Export center (FR-019): exports respect filters + field permissions; large
// exports run async with visible queued/processing/completed/failed/expired
// states. CSV mitigates formula injection server-side.
definePageMeta({ title: 'Exports' })
useHead({ title: 'Exports' })

const route = useRoute()
const service = useExportsService()
const toast = useToast()

const creating = ref(false)
const createError = ref<ApiError | null>(null)
const downloading = ref<string | null>(null)

const { data, pending, error, refresh } = await useAsyncData(
  'exports-list',
  () => service.list({ page_size: 25, ordering: '-created_at' }),
  { server: false },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const jobs = computed(() => data.value?.results ?? [])

// Poll while any job is active.
let pollTimer: ReturnType<typeof setInterval> | undefined
watch(
  jobs,
  (list) => {
    const active = list.some((j) => ['queued', 'processing'].includes(j.status))
    if (active && !pollTimer) {
      pollTimer = setInterval(() => void refresh(), 3000)
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

/** Filters carried over from the register view (?status=…&q=…). */
const incomingFilters = computed(() => {
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(route.query)) {
    if (typeof value === 'string' && value) out[key] = value
  }
  return out
})
const hasIncomingFilters = computed(() => Object.keys(incomingFilters.value).length > 0)

async function createExport(): Promise<void> {
  if (creating.value) return
  creating.value = true
  createError.value = null
  try {
    await service.create(incomingFilters.value)
    toast.success('Export queued')
    await refresh()
  } catch (e) {
    createError.value = ApiError.fromUnknown(e)
  } finally {
    creating.value = false
  }
}

async function download(job: ExportJob): Promise<void> {
  downloading.value = job.uuid
  try {
    const blob = await service.download(job.uuid)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `asset-export-${job.uuid.slice(0, 8)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.error('Download failed', ApiError.fromUnknown(e).message)
  } finally {
    downloading.value = null
  }
}
</script>

<template>
  <div class="max-w-3xl">
    <PageHeader title="Export center" description="CSV exports of the asset register, respecting your filters and field permissions." />

    <section aria-labelledby="export-new" class="mb-6 rounded-xl border border-border bg-surface p-4 sm:p-6">
      <h2 id="export-new" class="text-base font-semibold text-ink">New export</h2>
      <p v-if="hasIncomingFilters" class="mt-1 text-sm text-muted">
        The filters from your current register view will be applied:
        <span class="font-mono text-xs text-ink-secondary">{{ incomingFilters }}</span>
      </p>
      <p v-else class="mt-1 text-sm text-muted">
        This export covers the assets visible in your scope. Tip: apply filters in the
        <NuxtLink to="/assets" class="rounded text-accent hover:text-accent-hover">asset register</NuxtLink>
        and use “Export view” to export exactly that selection.
      </p>
      <p class="mt-1 text-xs text-muted">
        Financial fields are only included for authorized roles. Values are protected against
        spreadsheet formula injection.
      </p>
      <InlineAlert v-if="createError" tone="error" class="mt-3" :message="createError.message" :correlation-id="createError.correlationId" />
      <button
        type="button"
        class="mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
        :disabled="creating"
        @click="createExport"
      >
        <AppIcon name="archive" size="sm" />
        {{ creating ? 'Queuing…' : 'Create CSV export' }}
      </button>
    </section>

    <LoadingSkeleton v-if="pending && !jobs.length" :lines="3" label="Loading exports…" />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Exports could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <EmptyState
      v-else-if="!jobs.length"
      icon="archive"
      title="No exports yet"
      message="Exports you create will appear here with their status and download link."
    />

    <ul v-else class="space-y-3">
      <li v-for="job in jobs" :key="job.uuid" class="rounded-xl border border-border bg-surface p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <p class="font-mono text-sm text-ink">asset-export-{{ job.uuid.slice(0, 8) }}.csv</p>
              <StatusBadge :label="codeToLabel(job.status)" :code="job.status" size="sm" />
            </div>
            <p class="mt-1 text-xs text-muted">
              Requested {{ formatDateTime(job.created_at) }}
              <span v-if="job.completed_at"> · Ready since {{ formatDateTime(job.completed_at) }}</span>
            </p>
            <p v-if="job.status === 'failed' && job.error" class="mt-1 text-xs text-danger">{{ job.error }}</p>
          </div>
          <button
            v-if="job.status === 'completed'"
            type="button"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-raised px-3 py-2 text-sm font-medium text-ink hover:bg-hover"
            :disabled="downloading === job.uuid"
            @click="download(job)"
          >
            {{ downloading === job.uuid ? 'Downloading…' : 'Download' }}
          </button>
          <span v-else-if="['queued', 'processing'].includes(job.status)" class="flex items-center gap-2 text-sm text-muted" role="status">
            <AppIcon name="refresh" class="animate-spin" size="sm" />
            {{ codeToLabel(job.status) }}…
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>
