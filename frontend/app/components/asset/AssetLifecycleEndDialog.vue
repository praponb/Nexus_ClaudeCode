<script setup lang="ts">
import type { AssetDetail } from '~/types/api'
import { ApiError } from '~/utils/errors'
import AppIcon from '~/components/AppIcon.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'

// Retirement / disposal / reopen dialog (FR-014, J-5).
// - Retire: recorded reason; asset leaves active service.
// - Dispose: terminal by default; BR-006 blockers (e.g. open assignment)
//   arrive as 409 DISPOSAL_BLOCKED and are listed verbatim, non-destructively.
// - Reopen: elevated permission + recorded justification, audited.
// All actions send Idempotency-Key and await the confirmed response (§14.6).
const props = withDefaults(
  defineProps<{
    open?: boolean
    asset: AssetDetail
    mode: 'retire' | 'dispose' | 'reopen'
  }>(),
  { open: false },
)

const emit = defineEmits<{ (e: 'close' | 'changed'): void }>()

const lifecycle = useLifecycleService()
const toast = useToast()

const reason = ref('')
const method = ref('')
const submitting = ref(false)
const error = ref<ApiError | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const titleId = useId()

const COPY = {
  retire: {
    title: 'Retire asset',
    intro:
      'Retiring removes the asset from active service. Its full history is preserved and it stays searchable to authorized users.',
    reasonLabel: 'Retirement reason',
    submit: 'Retire asset',
    success: 'Asset retired',
  },
  dispose: {
    title: 'Dispose of asset',
    intro:
      'Disposal is terminal by default: the asset cannot be reused. Disposal is blocked while open obligations exist (for example an active assignment) unless an authorized exception applies.',
    reasonLabel: 'Disposal reason',
    submit: 'Dispose of asset',
    success: 'Asset disposed',
  },
  reopen: {
    title: 'Reopen asset',
    intro:
      'Reopening returns a retired or disposed asset to service. This requires elevated permission and your justification is recorded in the audit log.',
    reasonLabel: 'Justification',
    submit: 'Reopen asset',
    success: 'Asset reopened',
  },
} as const

const copy = computed(() => COPY[props.mode])

/** BR-006 blockers may arrive as field errors or in the message. */
const blockers = computed(() => {
  const fe = error.value?.fieldErrors ?? {}
  return Object.entries(fe).flatMap(([field, messages]) =>
    messages.map((m) => (field === 'blockers' || field === 'detail' ? m : `${field}: ${m}`)),
  )
})

watch(
  () => props.open,
  async (open) => {
    if (open) {
      reason.value = ''
      method.value = ''
      error.value = null
      await nextTick()
      panelRef.value?.querySelector<HTMLElement>('textarea, input, select')?.focus()
    }
  },
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') emit('close')
}

async function submit(): Promise<void> {
  if (submitting.value) return
  if (!reason.value.trim()) {
    error.value = new ApiError(
      props.mode === 'reopen'
        ? 'A justification is required to reopen this asset.'
        : 'A reason is required for this action.',
      { code: 'VALIDATION_FAILED', status: 400 },
    )
    return
  }
  submitting.value = true
  error.value = null
  try {
    if (props.mode === 'retire') {
      await lifecycle.retire(props.asset.uuid, { reason: reason.value.trim() })
    } else if (props.mode === 'dispose') {
      await lifecycle.dispose(props.asset.uuid, {
        reason: reason.value.trim(),
        method: method.value.trim() || undefined,
      })
    } else {
      await lifecycle.reopen(props.asset.uuid, { justification: reason.value.trim() })
    }
    toast.success(`${copy.value.success}: ${props.asset.tag}`)
    emit('changed')
    emit('close')
  } catch (e) {
    error.value = ApiError.fromUnknown(e)
  } finally {
    submitting.value = false
  }
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent'
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
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
          {{ copy.title }} — <span class="font-mono text-accent">{{ asset.tag }}</span>
        </h2>
        <p class="mt-1 text-sm text-muted">{{ copy.intro }}</p>

        <InlineAlert
          v-if="error"
          :tone="error.status === 409 ? 'warning' : 'error'"
          class="mt-4"
          :message="error.message"
          :correlation-id="error.correlationId"
        />
        <ul v-if="blockers.length" class="mt-2 list-inside list-disc rounded-lg border border-warning/40 bg-warning/5 p-3 text-sm text-ink-secondary">
          <li v-for="(blocker, i) in blockers" :key="i">{{ blocker }}</li>
        </ul>

        <form class="mt-4 space-y-4" novalidate @submit.prevent="submit">
          <FormField v-if="mode === 'dispose'" v-slot="{ inputId }" label="Disposal method" hint="Optional — for example recycling, sale, or certified destruction.">
            <input :id="inputId" v-model="method" type="text" maxlength="100" :class="inputClass" autocomplete="off" >
          </FormField>
          <FormField v-slot="{ inputId }" :label="copy.reasonLabel" required>
            <textarea
              :id="inputId"
              v-model="reason"
              rows="3"
              required
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
              :class="mode === 'reopen'
                ? 'bg-accent text-on-accent hover:bg-accent-hover'
                : 'bg-danger text-canvas hover:bg-danger/90'"
              :disabled="submitting"
            >
              <AppIcon v-if="!submitting" :name="mode === 'reopen' ? 'refresh' : 'warning'" size="sm" />
              {{ submitting ? 'Submitting…' : copy.submit }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
