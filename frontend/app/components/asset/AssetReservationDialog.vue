<script setup lang="ts">
import type { AssetDetail } from '~/types/api'
import { ApiError } from '~/utils/errors'
import { toIsoDateTime, toLocalInputValue, validateReservationWindow } from '~/utils/reservation'
import AppIcon from '~/components/AppIcon.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'

// Reservation dialog (FR-010): reserves the asset for a future window.
// Overlapping active reservations are rejected by the backend (409); the
// confirmed-response rule applies (no optimistic completion, design §14.6).
const props = withDefaults(
  defineProps<{
    open?: boolean
    asset: AssetDetail
  }>(),
  { open: false },
)

const emit = defineEmits<{
  (e: 'close' | 'reserved'): void
}>()

const lifecycle = useLifecycleService()
const toast = useToast()

const startAt = ref('')
const endAt = ref('')
const purpose = ref('')
const submitting = ref(false)
const error = ref<ApiError | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const titleId = useId()

watch(
  () => props.open,
  async (open) => {
    if (open) {
      const start = new Date()
      start.setMinutes(0, 0, 0)
      start.setHours(start.getHours() + 1)
      const end = new Date(start)
      end.setHours(end.getHours() + 4)
      startAt.value = toLocalInputValue(start)
      endAt.value = toLocalInputValue(end)
      purpose.value = ''
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
  if (submitting.value) return
  const validationError = validateReservationWindow(startAt.value, endAt.value)
  if (validationError) {
    error.value = new ApiError(validationError, { code: 'VALIDATION_FAILED', status: 400 })
    return
  }
  submitting.value = true
  error.value = null
  try {
    await lifecycle.reserve(props.asset.uuid, {
      start_at: toIsoDateTime(startAt.value),
      end_at: toIsoDateTime(endAt.value),
      purpose: purpose.value.trim() || undefined,
    })
    toast.success(`Reservation created for ${props.asset.tag}`)
    emit('reserved')
    emit('close')
  } catch (e) {
    const apiError = ApiError.fromUnknown(e)
    // Overlapping active reservation → 409; surface the backend's safe message.
    error.value = apiError
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
          Reserve asset — <span class="font-mono text-accent">{{ asset.tag }}</span>
        </h2>
        <p class="mt-1 text-sm text-muted">
          Reserve this asset for a future time window. Overlapping reservations for the same asset
          are not possible.
        </p>

        <InlineAlert
          v-if="error"
          :tone="error.status === 409 ? 'warning' : 'error'"
          class="mt-4"
          :message="error.message"
          :correlation-id="error.correlationId"
        />

        <form class="mt-4 space-y-4" novalidate @submit.prevent="submit">
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField v-slot="{ inputId }" label="Reserved from" required>
              <input :id="inputId" v-model="startAt" type="datetime-local" required :class="inputClass" >
            </FormField>
            <FormField v-slot="{ inputId }" label="Reserved until" required>
              <input :id="inputId" v-model="endAt" type="datetime-local" required :class="inputClass" >
            </FormField>
          </div>
          <FormField v-slot="{ inputId }" label="Purpose" hint="Optional — why the asset is needed.">
            <input
              :id="inputId"
              v-model="purpose"
              type="text"
              maxlength="200"
              placeholder="Onboarding laptop for new hire"
              :class="inputClass"
              autocomplete="off"
            >
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
              class="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
              :disabled="submitting"
            >
              <AppIcon v-if="!submitting" name="clock" size="sm" />
              {{ submitting ? 'Reserving…' : 'Reserve asset' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
