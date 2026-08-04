<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDateTime } from '~/utils/format'
import type { ImportJob } from '~/types/workflow'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import WizardSteps from '~/components/WizardSteps.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import { useImportsService } from '~/services/api/imports'

// Bulk CSV import wizard (FR-018, layout §17.1):
// template → upload → validate/preview → policy → commit (async, idempotent)
// → result report. Cells are treated as text; no formula execution.
definePageMeta({ title: 'Imports' })
useHead({ title: 'Imports' })

const STEPS = ['Upload', 'Validate & preview', 'Commit', 'Result']

const service = useImportsService()
const { canManageAssets, authResolved } = usePermissions()

const step = ref(0)
const job = ref<ImportJob | null>(null)
const busy = ref(false)
const error = ref<ApiError | null>(null)

const policy = ref<'reject' | 'update' | 'create'>('reject')
const allowPartial = ref(false)

let pollTimer: ReturnType<typeof setInterval> | undefined

function stopPolling(): void {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = undefined
}

function pollUntil(activeStatuses: string[]): void {
  stopPolling()
  pollTimer = setInterval(() => {
    void (async () => {
      if (!job.value) return stopPolling()
      try {
        job.value = await service.retrieve(job.value.uuid)
        if (!activeStatuses.includes(job.value.status)) stopPolling()
      } catch {
        stopPolling()
      }
    })()
  }, 2000)
}

onBeforeUnmount(stopPolling)

async function onFileSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  error.value = null
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.csv')) {
    error.value = new ApiError('Choose a CSV file. Download the template below for the expected format.', { status: 415 })
    input.value = ''
    return
  }
  busy.value = true
  try {
    job.value = await service.upload(file)
    step.value = 1
    pollUntil(['queued', 'validating'])
  } catch (e) {
    error.value = ApiError.fromUnknown(e)
  } finally {
    busy.value = false
    input.value = ''
  }
}

watch(
  () => job.value?.status,
  (status) => {
    if (status === 'completed' || status === 'failed') step.value = 3
  },
)

async function commit(): Promise<void> {
  if (!job.value || busy.value) return
  busy.value = true
  error.value = null
  try {
    job.value = await service.commit(job.value.uuid, {
      duplicate_policy: policy.value,
      allow_partial: allowPartial.value,
    })
    step.value = 2
    pollUntil(['queued', 'processing'])
  } catch (e) {
    error.value = ApiError.fromUnknown(e)
  } finally {
    busy.value = false
  }
}

function reset(): void {
  stopPolling()
  job.value = null
  step.value = 0
  error.value = null
  policy.value = 'reject'
  allowPartial.value = false
}

/* Recent import jobs */
const { data: recent, refresh: refreshRecent } = await useAsyncData(
  'imports-recent',
  () => service.list({ page_size: 10, ordering: '-created_at' }),
  { server: false },
)

const previewRows = computed(() => job.value?.preview?.rows?.slice(0, 50) ?? [])
const preview = computed(() => job.value?.preview ?? null)

const rowStatusClass: Record<string, string> = {
  valid: 'text-success',
  warning: 'text-warning',
  error: 'text-danger',
  duplicate: 'text-warning',
}

const inputFileClass =
  'block w-full text-sm text-ink-secondary file:mr-3 file:min-h-11 file:rounded-lg file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-semibold file:text-on-accent hover:file:bg-accent-hover'
</script>

<template>
  <div>
    <PageHeader title="Import assets" description="Bulk-register or update assets from a CSV file.">
      <template #actions>
        <NuxtLink
          to="/exports"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
        >
          Export center
        </NuxtLink>
      </template>
    </PageHeader>

    <InlineAlert
      v-if="authResolved && !canManageAssets"
      tone="warning"
      title="Restricted module"
      message="Your role does not include CSV imports."
    />

    <div v-else class="max-w-4xl space-y-6">
      <WizardSteps :steps="STEPS" :current="step" />

      <InlineAlert v-if="error" tone="error" :message="error.message" :correlation-id="error.correlationId" />

      <!-- Step 1: template + upload -->
      <section v-if="step === 0" aria-labelledby="import-upload" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="import-upload" class="text-base font-semibold text-ink">1. Download the template and upload your CSV</h2>
        <p class="mt-1 text-sm text-muted">
          Values are imported as text — spreadsheet formulas are never executed. Cells starting with
          <code class="font-mono text-xs">= + - @</code> are sanitized or flagged.
        </p>
        <a
          :href="service.templateUrl()"
          class="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-raised px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
          download
        >
          <AppIcon name="archive" size="sm" />
          Download CSV template
        </a>
        <div class="mt-4">
          <label for="import-file" class="mb-1 block text-sm font-medium text-ink-secondary">CSV file</label>
          <input id="import-file" type="file" accept=".csv,text/csv" :class="inputFileClass" :disabled="busy" @change="onFileSelected" >
          <p v-if="busy" class="mt-2 text-sm text-muted" role="status">Uploading and validating…</p>
        </div>
      </section>

      <!-- Step 2: validation preview -->
      <section v-if="step === 1" aria-labelledby="import-preview" class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="import-preview" class="text-base font-semibold text-ink">2. Review validation results</h2>

        <p v-if="job && ['queued', 'validating'].includes(job.status)" class="flex items-center gap-2 text-sm text-muted" role="status">
          <AppIcon name="refresh" class="animate-spin" />
          Validating {{ job.filename || 'your file' }}…
        </p>

        <template v-else-if="preview">
          <dl class="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <div class="rounded-lg bg-input p-3 text-center">
              <dt class="text-xs text-muted">Total rows</dt>
              <dd class="text-xl font-bold text-ink">{{ preview.total }}</dd>
            </div>
            <div class="rounded-lg bg-input p-3 text-center">
              <dt class="text-xs text-success">Valid</dt>
              <dd class="text-xl font-bold text-ink">{{ preview.valid }}</dd>
            </div>
            <div class="rounded-lg bg-input p-3 text-center">
              <dt class="text-xs text-warning">Warnings</dt>
              <dd class="text-xl font-bold text-ink">{{ preview.warnings }}</dd>
            </div>
            <div class="rounded-lg bg-input p-3 text-center">
              <dt class="text-xs text-danger">Errors</dt>
              <dd class="text-xl font-bold text-ink">{{ preview.errors }}</dd>
            </div>
            <div class="rounded-lg bg-input p-3 text-center">
              <dt class="text-xs text-warning">Duplicates</dt>
              <dd class="text-xl font-bold text-ink">{{ preview.duplicates }}</dd>
            </div>
          </dl>

          <div v-if="previewRows.length" class="overflow-x-auto rounded-lg border border-border">
            <table class="min-w-full divide-y divide-border text-sm">
              <caption class="sr-only">Row-level validation results (first 50 rows)</caption>
              <thead class="bg-raised">
                <tr>
                  <th scope="col" class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted">Row</th>
                  <th scope="col" class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted">Result</th>
                  <th scope="col" class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted">Messages</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border">
                <tr v-for="row in previewRows" :key="row.row">
                  <td class="px-3 py-2 font-mono text-ink-secondary">{{ row.row }}</td>
                  <td class="px-3 py-2 font-medium" :class="rowStatusClass[row.status] ?? 'text-muted'">
                    {{ codeToLabel(row.status) }}
                  </td>
                  <td class="px-3 py-2 text-ink-secondary">{{ row.messages.join('; ') || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="(preview.rows?.length ?? 0) > 50" class="text-xs text-muted">
            Showing the first 50 rows. The full result report is available after the import.
          </p>
        </template>

        <InlineAlert
          v-else-if="job?.status === 'failed'"
          tone="error"
          title="Validation failed"
          :message="job.error || 'The file could not be processed. Check the format against the template and try again.'"
        />

        <!-- Policy + commit -->
        <fieldset v-if="preview && job?.status !== 'failed'" class="space-y-3 rounded-lg border border-border p-4">
          <legend class="px-1 text-sm font-semibold text-ink">3. Duplicate policy and commit</legend>
          <div role="radiogroup" aria-label="Duplicate policy" class="flex flex-wrap gap-2">
            <label
              v-for="option in [
                { value: 'reject', label: 'Reject duplicates' },
                { value: 'update', label: 'Update existing' },
                { value: 'create', label: 'Create anyway' },
              ]"
              :key="option.value"
              class="flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm"
              :class="policy === option.value ? 'border-accent bg-accent/10 text-ink' : 'border-border bg-input text-ink-secondary'"
            >
              <input v-model="policy" type="radio" name="duplicate-policy" :value="option.value" class="accent-accent" >
              {{ option.label }}
            </label>
          </div>
          <label class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-ink-secondary">
            <input v-model="allowPartial" type="checkbox" class="h-4 w-4 accent-accent" >
            Allow partial success (import valid rows even if some rows fail)
          </label>
          <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              class="inline-flex min-h-11 items-center justify-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
              @click="reset"
            >
              Start over
            </button>
            <button
              type="button"
              class="inline-flex min-h-11 items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
              :disabled="busy || (preview.errors > 0 && !allowPartial)"
              @click="commit"
            >
              {{ busy ? 'Committing…' : `Commit import of ${preview.total} rows` }}
            </button>
          </div>
        </fieldset>
      </section>

      <!-- Step 3: processing -->
      <section v-if="step === 2" aria-labelledby="import-processing" class="rounded-xl border border-border bg-surface p-6 text-center">
        <h2 id="import-processing" class="text-base font-semibold text-ink">Import in progress</h2>
        <p class="mt-2 flex items-center justify-center gap-2 text-sm text-muted" role="status">
          <AppIcon name="refresh" class="animate-spin" />
          Processing rows in the background. This page updates automatically.
        </p>
      </section>

      <!-- Step 4: result -->
      <section v-if="step === 3 && job" aria-labelledby="import-result" class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="import-result" class="text-base font-semibold text-ink">4. Result report</h2>
        <InlineAlert
          v-if="job.status === 'failed'"
          tone="error"
          title="Import failed"
          :message="job.error || 'The import could not be completed. No partial success was claimed.'"
          :correlation-id="job.correlation_id"
        />
        <template v-else>
          <dl class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="rounded-lg bg-input p-3 text-center">
              <dt class="text-xs text-success">Created</dt>
              <dd class="text-xl font-bold text-ink">{{ job.counts?.created ?? 0 }}</dd>
            </div>
            <div class="rounded-lg bg-input p-3 text-center">
              <dt class="text-xs text-info">Updated</dt>
              <dd class="text-xl font-bold text-ink">{{ job.counts?.updated ?? 0 }}</dd>
            </div>
            <div class="rounded-lg bg-input p-3 text-center">
              <dt class="text-xs text-muted">Skipped</dt>
              <dd class="text-xl font-bold text-ink">{{ job.counts?.skipped ?? 0 }}</dd>
            </div>
            <div class="rounded-lg bg-input p-3 text-center">
              <dt class="text-xs text-danger">Failed</dt>
              <dd class="text-xl font-bold text-ink">{{ job.counts?.failed ?? 0 }}</dd>
            </div>
          </dl>
          <p v-if="(job.counts?.failed ?? 0) > 0" class="text-sm text-warning">
            Some rows failed. The import completed partially — the counts above are the confirmed
            backend result, not an estimate.
          </p>
        </template>
        <div class="flex flex-wrap gap-2">
          <NuxtLink
            to="/assets"
            class="inline-flex min-h-11 items-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
          >
            Open asset register
          </NuxtLink>
          <button
            type="button"
            class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
            @click="reset(); refreshRecent()"
          >
            Import another file
          </button>
        </div>
      </section>

      <!-- Recent jobs -->
      <section aria-labelledby="import-recent" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="import-recent" class="text-base font-semibold text-ink">Recent imports</h2>
        <EmptyState
          v-if="!recent?.results.length"
          icon="archive"
          title="No imports yet"
          message="Completed and in-progress imports will appear here."
        />
        <ul v-else class="mt-3 space-y-2">
          <li v-for="item in recent.results" :key="item.uuid" class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2">
            <div class="min-w-0">
              <NuxtLink :to="`/imports/${item.uuid}`" class="rounded text-sm font-medium text-accent hover:text-accent-hover">
                {{ item.filename || `Import ${item.uuid.slice(0, 8)}` }}
              </NuxtLink>
              <p class="text-xs text-muted">{{ formatDateTime(item.created_at) }}</p>
            </div>
            <StatusBadge :label="codeToLabel(item.status)" :code="item.status" size="sm" />
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
