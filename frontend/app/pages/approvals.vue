<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDateTime } from '~/utils/format'
import type { ApprovalRequest } from '~/types/control'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import PaginationControls from '~/components/PaginationControls.vue'
import ApprovalDecisionDialog from '~/components/approval/ApprovalDecisionDialog.vue'

// Approval inbox (FR-024): pending requests by default, full history
// available via the status filter. Decisions open a confirmation dialog.
definePageMeta({ title: 'Approvals' })
useHead({ title: 'Approvals' })

const service = useApprovalsService()
const toast = useToast()
const { canApprove } = usePermissions()
const { loaded, user } = useAuth()

const page = ref(1)
const statusFilter = ref('pending')

const { data, pending, error, refresh } = await useAsyncData(
  'approvals-list',
  () =>
    service.list({
      page: page.value,
      page_size: 25,
      ...(statusFilter.value ? { status: statusFilter.value } : {}),
    }),
  { server: false, watch: [page, statusFilter] },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const items = computed(() => data.value?.results ?? [])

const STATUS_OPTIONS = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'returned', label: 'Returned' },
  { value: '', label: 'All statuses' },
]

const dialogOpen = ref(false)
const selected = ref<ApprovalRequest | null>(null)

function openDecision(request: ApprovalRequest): void {
  selected.value = request
  dialogOpen.value = true
}

function onDecided(): void {
  toast.success('Decision recorded')
  void refresh()
}

/** Separation-of-duties hint (backend still enforces when configured). */
function isOwnRequest(request: ApprovalRequest): boolean {
  return Boolean(user.value && request.requester && request.requester.uuid === user.value.uuid)
}

const inputClass =
  'h-11 rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent'
</script>

<template>
  <div>
    <PageHeader title="Approvals" description="Requests waiting for your decision, and their history." />

    <InlineAlert
      v-if="loaded && !canApprove"
      tone="warning"
      title="Restricted module"
      message="Your role does not include the approval inbox."
    />

    <template v-else>
      <div class="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4">
        <div>
          <label for="appr-status" class="mb-1 block text-sm font-medium text-ink-secondary">Status</label>
          <select id="appr-status" v-model="statusFilter" :class="inputClass" @change="page = 1">
            <option v-for="option in STATUS_OPTIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
      </div>

      <LoadingSkeleton v-if="pending && !items.length" :lines="4" label="Loading approvals…" />
      <InlineAlert
        v-else-if="apiError"
        tone="error"
        title="Approvals could not be loaded"
        :message="apiError.message"
        :correlation-id="apiError.correlationId"
        retry-label="Retry"
        @retry="refresh()"
      />
      <EmptyState
        v-else-if="!items.length"
        icon="success"
        :title="statusFilter === 'pending' ? 'Nothing waiting for approval' : 'No approvals found'"
        :message="statusFilter === 'pending'
          ? 'Transfers, disposals, and sensitive changes that require your decision will appear here.'
          : 'No approval requests match the selected status.'"
      />

      <template v-else>
        <ul class="space-y-3">
          <li v-for="request in items" :key="request.uuid" class="rounded-xl border border-border bg-surface p-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <h2 class="font-semibold text-ink">{{ codeToLabel(request.type) }}</h2>
                  <StatusBadge :label="codeToLabel(request.status)" :code="request.status" size="sm" />
                </div>
                <p class="mt-1 text-sm text-ink-secondary">
                  <NuxtLink
                    v-if="request.asset"
                    :to="`/assets/${request.asset.uuid}`"
                    class="rounded font-mono text-accent hover:text-accent-hover"
                  >
                    {{ request.asset.tag }}
                  </NuxtLink>
                  <span v-if="request.asset"> · {{ request.asset.name }} · </span>
                  Requested by {{ request.requester?.display_name || 'unknown' }}
                  · {{ formatDateTime(request.created_at) }}
                </p>
                <p v-if="request.reason" class="mt-1 max-w-2xl text-sm text-muted">“{{ request.reason }}”</p>
                <p v-if="request.status !== 'pending' && request.approver" class="mt-1 text-xs text-faint">
                  Decided by {{ request.approver.display_name }}
                  <span v-if="request.decided_at"> · {{ formatDateTime(request.decided_at) }}</span>
                  <span v-if="request.comments"> · “{{ request.comments }}”</span>
                </p>
                <p v-if="request.status === 'pending' && isOwnRequest(request)" class="mt-1 flex items-center gap-1 text-xs text-warning">
                  <AppIcon name="warning" size="sm" />
                  You raised this request. Where separation of duties is enabled, another approver must decide it.
                </p>
              </div>
              <button
                v-if="request.status === 'pending'"
                type="button"
                class="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
                @click="openDecision(request)"
              >
                <AppIcon name="check" size="sm" />
                Decide
              </button>
            </div>
          </li>
        </ul>

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

    <ApprovalDecisionDialog
      :open="dialogOpen"
      :request="selected"
      @close="dialogOpen = false"
      @decided="onDecided"
    />
  </div>
</template>
