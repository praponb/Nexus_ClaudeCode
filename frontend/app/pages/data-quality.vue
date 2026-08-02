<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDateTime } from '~/utils/format'
import type { DataQualityIssue } from '~/types/control'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import PaginationControls from '~/components/PaginationControls.vue'

// Data-quality work queue (FR-028): rule-engine findings as errors vs
// warnings. Resolving an issue preserves the audit history — nothing is
// deleted. Resolved items stay visible via the status filter.
definePageMeta({ title: 'Data quality' })
useHead({ title: 'Data quality' })

const service = useDataQualityService()
const toast = useToast()
const { canManageAssets } = usePermissions()
const { loaded } = useAuth()

const page = ref(1)
const severity = ref('')
const includeResolved = ref(false)
const resolving = ref<string | null>(null)

const { data, pending, error, refresh } = await useAsyncData(
  'data-quality-issues',
  () =>
    service.issues({
      page: page.value,
      page_size: 25,
      ...(severity.value ? { severity: severity.value } : {}),
      ...(includeResolved.value ? { resolved: 'all' } : {}),
    }),
  { server: false, watch: [page, severity, includeResolved] },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const issues = computed(() => data.value?.results ?? [])

async function resolve(issue: DataQualityIssue): Promise<void> {
  if (resolving.value) return
  resolving.value = issue.uuid
  try {
    await service.resolve(issue.uuid)
    toast.success('Issue marked resolved')
    await refresh()
  } catch (e) {
    toast.error('Could not resolve the issue', ApiError.fromUnknown(e).message)
  } finally {
    resolving.value = null
  }
}

const inputClass =
  'h-11 rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent'
</script>

<template>
  <div>
    <PageHeader
      title="Data quality"
      description="Missing data, invalid references, and possible duplicates flagged by the rule engine."
    />

    <InlineAlert
      v-if="loaded && !canManageAssets"
      tone="warning"
      title="Restricted work queue"
      message="Your role does not include the data-quality queue."
    />

    <template v-else>
      <div class="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4">
        <div>
          <label for="dq-severity" class="mb-1 block text-sm font-medium text-ink-secondary">Severity</label>
          <select id="dq-severity" v-model="severity" :class="inputClass" @change="page = 1">
            <option value="">Errors and warnings</option>
            <option value="error">Errors only</option>
            <option value="warning">Warnings only</option>
          </select>
        </div>
        <label class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-ink-secondary">
          <input v-model="includeResolved" type="checkbox" class="h-4 w-4 accent-accent" @change="page = 1" >
          Include resolved
        </label>
      </div>

      <LoadingSkeleton v-if="pending && !issues.length" :lines="4" label="Checking data quality…" />
      <InlineAlert
        v-else-if="apiError"
        tone="error"
        title="Data-quality issues could not be loaded"
        :message="apiError.message"
        :correlation-id="apiError.correlationId"
        retry-label="Retry"
        @retry="refresh()"
      />
      <EmptyState
        v-else-if="!issues.length"
        icon="success"
        title="No open data-quality issues"
        message="The rule engine has not flagged any records in your scope."
      />

      <template v-else>
        <ul class="space-y-3">
          <li v-for="issue in issues" :key="issue.uuid" class="rounded-xl border bg-surface p-4" :class="issue.severity === 'error' ? 'border-danger/40' : 'border-border'">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="flex items-center gap-2 font-medium text-ink">
                  <AppIcon :name="issue.severity === 'error' ? 'error' : 'warning'" size="sm" :class="issue.severity === 'error' ? 'text-danger' : 'text-warning'" />
                  {{ issue.severity === 'error' ? 'Error' : 'Warning' }}
                  <span v-if="issue.rule" class="text-xs font-normal text-muted">· {{ codeToLabel(issue.rule) }}</span>
                </p>
                <p class="mt-1 text-sm text-ink-secondary">{{ issue.message }}</p>
                <p class="mt-1 text-xs text-faint">
                  <NuxtLink
                    v-if="issue.asset"
                    :to="`/assets/${issue.asset.uuid}`"
                    class="rounded font-mono text-accent hover:text-accent-hover"
                  >
                    {{ issue.asset.tag }}
                  </NuxtLink>
                  <span v-if="issue.asset"> · {{ issue.asset.name }} · </span>
                  <span v-if="issue.created_at">Flagged {{ formatDateTime(issue.created_at) }}</span>
                  <span v-if="issue.resolved_at" class="text-success"> · Resolved {{ formatDateTime(issue.resolved_at) }}</span>
                </p>
              </div>
              <button
                v-if="!issue.resolved_at"
                type="button"
                class="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-hover disabled:opacity-60"
                :disabled="resolving === issue.uuid"
                @click="resolve(issue)"
              >
                <AppIcon name="check" size="sm" />
                {{ resolving === issue.uuid ? 'Resolving…' : 'Mark resolved' }}
              </button>
            </div>
          </li>
        </ul>

        <div class="mt-4">
          <PaginationControls :page="page" :page-size="25" :total="data?.count ?? 0" :pending="pending" @change="page = $event" />
        </div>
      </template>
    </template>
  </div>
</template>
