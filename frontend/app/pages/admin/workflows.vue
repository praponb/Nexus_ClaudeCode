<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatReportCell } from '~/utils/report'
import PageHeader from '~/components/PageHeader.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'

// Status transition rules (FR-026; configurable per A-05). Read-only view of
// the effective rules; rule authoring is a backend configuration concern.
definePageMeta({ title: 'Workflow rules' })
useHead({ title: 'Workflow rules' })

const service = useAdminService()

const { data, pending, error, refresh } = await useAsyncData(
  'admin-transition-rules',
  () => service.transitionRules(),
  { server: false },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const rules = computed(() => (data.value ?? []) as Array<Record<string, unknown>>)

interface RuleView {
  key: string
  from: string
  to: string
  requiresReason: boolean
  requiresEvidence: boolean
  requiresApproval: boolean
  roles: string
}

function refName(value: unknown): string {
  if (value && typeof value === 'object') {
    const v = value as Record<string, unknown>
    if (typeof v.label === 'string') return v.label
    if (typeof v.name === 'string') return v.name
    if (typeof v.code === 'string') return codeToLabel(v.code)
  }
  return formatReportCell(value)
}

const rows = computed<RuleView[]>(() =>
  rules.value.map((rule, i) => ({
    key: String(rule.uuid ?? i),
    from: refName(rule.from_status ?? rule.from),
    to: refName(rule.to_status ?? rule.to),
    requiresReason: Boolean(rule.requires_reason),
    requiresEvidence: Boolean(rule.requires_evidence),
    requiresApproval: Boolean(rule.requires_approval),
    roles: Array.isArray(rule.allowed_roles)
      ? (rule.allowed_roles as string[]).map(codeToLabel).join(', ')
      : formatReportCell(rule.allowed_roles),
  })),
)
</script>

<template>
  <div>
    <PageHeader
      title="Workflow rules"
      description="The status transitions allowed for each role, and what each transition requires. Changes are applied through backend configuration."
    />

    <LoadingSkeleton v-if="pending && !rows.length" :lines="5" label="Loading workflow rules…" />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Workflow rules could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <EmptyState
      v-else-if="!rows.length"
      icon="refresh"
      title="No transition rules"
      message="The server did not return any status transition rules."
    />

    <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
      <table class="min-w-full divide-y divide-border text-sm">
        <caption class="sr-only">Status transition rules</caption>
        <thead class="bg-raised">
          <tr>
            <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">From status</th>
            <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">To status</th>
            <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Requirements</th>
            <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Allowed roles</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="row in rows" :key="row.key" class="hover:bg-hover">
            <td class="whitespace-nowrap px-3 py-3"><StatusBadge :label="row.from" :code="row.from" size="sm" /></td>
            <td class="whitespace-nowrap px-3 py-3"><StatusBadge :label="row.to" :code="row.to" size="sm" /></td>
            <td class="px-3 py-3 text-ink-secondary">
              <ul class="flex flex-wrap gap-1">
                <li v-if="row.requiresReason" class="rounded-full border border-border-strong px-2 py-0.5 text-xs">Reason</li>
                <li v-if="row.requiresEvidence" class="rounded-full border border-border-strong px-2 py-0.5 text-xs">Evidence</li>
                <li v-if="row.requiresApproval" class="rounded-full border border-warning/40 bg-warning/10 px-2 py-0.5 text-xs text-warning">Approval</li>
                <li v-if="!row.requiresReason && !row.requiresEvidence && !row.requiresApproval" class="text-xs text-muted">None</li>
              </ul>
            </td>
            <td class="px-3 py-3 text-ink-secondary">{{ row.roles || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
