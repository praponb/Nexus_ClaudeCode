<script setup lang="ts">
import type { ApprovalDecisionAction, ApprovalRequest } from '~/types/control'
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import AppIcon from '~/components/AppIcon.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'

// Approval decision dialog (FR-024): approve / reject / return with comments.
// Decisions are immutable after the confirmed response; separation of duties
// (requester ≠ approver) is enforced by the backend and shown via the error.
const props = withDefaults(
  defineProps<{
    open?: boolean
    request?: ApprovalRequest | null
  }>(),
  { open: false, request: null },
)

const emit = defineEmits<{ (e: 'close' | 'decided'): void }>()

const service = useApprovalsService()

const action = ref<ApprovalDecisionAction>('approve')
const comments = ref('')
const submitting = ref(false)
const error = ref<ApiError | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const titleId = useId()

const DECISIONS: Array<{ value: ApprovalDecisionAction; label: string; hint: string }> = [
  { value: 'approve', label: 'Approve', hint: 'The requested change proceeds.' },
  { value: 'reject', label: 'Reject', hint: 'The request is declined permanently.' },
  { value: 'return', label: 'Return for changes', hint: 'Sent back to the requester to revise.' },
]

const payloadRows = computed(() => {
  const payload = props.request?.payload
  if (!payload || typeof payload !== 'object') return []
  return Object.entries(payload)
    .filter(([, v]) => v !== null && v !== undefined && typeof v !== 'object')
    .slice(0, 12)
    .map(([key, value]) => ({ key: codeToLabel(key), value: String(value) }))
})

watch(
  () => props.open,
  async (open) => {
    if (open) {
      action.value = 'approve'
      comments.value = ''
      error.value = null
      await nextTick()
      panelRef.value?.querySelector<HTMLElement>('input')?.focus()
    }
  },
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') emit('close')
}

async function submit(): Promise<void> {
  if (!props.request || submitting.value) return
  if (action.value !== 'approve' && !comments.value.trim()) {
    error.value = new ApiError('Add a comment explaining the decision.', {
      code: 'VALIDATION_FAILED',
      status: 400,
    })
    return
  }
  submitting.value = true
  error.value = null
  try {
    await service.decide(props.request.uuid, action.value, comments.value.trim())
    emit('decided')
    emit('close')
  } catch (e) {
    error.value = ApiError.fromUnknown(e)
  } finally {
    submitting.value = false
  }
}

const submitLabel = computed(() => {
  if (submitting.value) return 'Submitting…'
  return action.value === 'approve'
    ? 'Approve request'
    : action.value === 'reject'
      ? 'Reject request'
      : 'Return to requester'
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && request"
      class="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6"
      @keydown="onKeydown"
    >
      <div class="absolute inset-0 bg-canvas/80" aria-hidden="true" @click="emit('close')" />
      <div
        ref="panelRef"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        class="relative w-full max-w-lg rounded-t-2xl border border-border bg-raised p-6 sm:rounded-2xl"
      >
        <h2 :id="titleId" class="text-lg font-semibold text-ink">
          Decide — {{ codeToLabel(request.type) }}
        </h2>
        <p class="mt-1 text-sm text-muted">
          <template v-if="request.asset">
            Asset <span class="font-mono text-accent">{{ request.asset.tag }}</span> ·
          </template>
          Requested by {{ request.requester?.display_name || 'unknown' }}
        </p>
        <p v-if="request.reason" class="mt-2 rounded-lg bg-input p-3 text-sm text-ink-secondary">
          “{{ request.reason }}”
        </p>
        <dl v-if="payloadRows.length" class="mt-3 grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
          <div v-for="row in payloadRows" :key="row.key">
            <dt class="text-muted">{{ row.key }}</dt>
            <dd class="break-words text-ink">{{ row.value }}</dd>
          </div>
        </dl>

        <InlineAlert v-if="error" tone="error" class="mt-4" :message="error.message" :correlation-id="error.correlationId" />

        <form class="mt-4 space-y-4" novalidate @submit.prevent="submit">
          <fieldset>
            <legend class="mb-2 text-sm font-medium text-ink-secondary">Decision</legend>
            <div class="space-y-1">
              <label
                v-for="option in DECISIONS"
                :key="option.value"
                class="flex min-h-11 cursor-pointer items-start gap-2 rounded-lg border px-3 py-2"
                :class="action === option.value ? 'border-accent bg-accent/10' : 'border-border bg-input'"
              >
                <input v-model="action" type="radio" name="decision" :value="option.value" class="mt-1 accent-accent" >
                <span>
                  <span class="block text-sm font-medium text-ink">{{ option.label }}</span>
                  <span class="block text-xs text-muted">{{ option.hint }}</span>
                </span>
              </label>
            </div>
          </fieldset>

          <FormField
            v-slot="{ inputId }"
            label="Comments"
            :required="action !== 'approve'"
            :hint="action === 'approve' ? 'Optional for approvals.' : 'Required — explain the decision to the requester.'"
          >
            <textarea
              :id="inputId"
              v-model="comments"
              rows="3"
              class="w-full rounded-lg border border-border bg-input px-3 py-2 text-sm text-ink focus:border-accent"
            />
          </FormField>

          <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              class="inline-flex min-h-11 items-center justify-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
              :disabled="submitting"
              @click="emit('close')"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-60"
              :class="action === 'approve'
                ? 'bg-accent text-on-accent hover:bg-accent-hover'
                : action === 'reject'
                  ? 'bg-danger text-canvas hover:bg-danger/90'
                  : 'bg-warning text-canvas hover:bg-warning/90'"
              :disabled="submitting"
            >
              <AppIcon v-if="!submitting" :name="action === 'reject' ? 'close' : 'check'" size="sm" />
              {{ submitLabel }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
