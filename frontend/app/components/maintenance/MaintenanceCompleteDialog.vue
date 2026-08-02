<script setup lang="ts">
import type { MaintenanceRecord } from '~/types/workflow'
import { ApiError } from '~/utils/errors'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'

const props = withDefaults(
  defineProps<{
    open?: boolean
    record?: MaintenanceRecord | null
  }>(),
  { open: false, record: null },
)

const emit = defineEmits<{ (e: 'close' | 'completed'): void }>()

const service = useMaintenanceService()
const toast = useToast()

const completedAt = ref('')
const result = ref('')
const nextDue = ref('')
const submitting = ref(false)
const error = ref<ApiError | null>(null)
const titleId = useId()
const panelRef = ref<HTMLElement | null>(null)

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      completedAt.value = today()
      result.value = ''
      nextDue.value = ''
      error.value = null
      await nextTick()
      panelRef.value?.querySelector<HTMLElement>('input, textarea')?.focus()
    }
  },
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') emit('close')
}

async function submit(): Promise<void> {
  if (!props.record || submitting.value) return
  submitting.value = true
  error.value = null
  try {
    await service.complete(props.record.uuid, {
      completed_at: completedAt.value || null,
      result: result.value.trim() || undefined,
      next_due: nextDue.value || null,
    })
    toast.success('Maintenance completed')
    emit('completed')
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
    <div v-if="open && record" class="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6" @keydown="onKeydown">
      <div class="absolute inset-0 bg-canvas/80" aria-hidden="true" @click="emit('close')" />
      <div
        ref="panelRef"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        class="relative w-full max-w-lg rounded-t-2xl border border-border bg-raised p-6 sm:rounded-2xl"
      >
        <h2 :id="titleId" class="text-lg font-semibold text-ink">Complete maintenance</h2>
        <p class="mt-1 text-sm text-muted">{{ record.issue }}</p>

        <InlineAlert v-if="error" tone="error" class="mt-4" :message="error.message" :correlation-id="error.correlationId" />

        <form class="mt-4 space-y-4" @submit.prevent="submit">
          <FormField v-slot="{ inputId }" label="Completion date" required>
            <input :id="inputId" v-model="completedAt" type="date" required :class="inputClass" >
          </FormField>
          <FormField v-slot="{ inputId }" label="Result">
            <textarea :id="inputId" v-model="result" rows="3" class="w-full rounded-lg border border-border bg-input px-3 py-2 text-sm text-ink focus:border-accent" placeholder="What was done? Parts replaced, outcome…" />
          </FormField>
          <FormField v-slot="{ inputId }" label="Next maintenance due" hint="Optional — used for upcoming-work tracking.">
            <input :id="inputId" v-model="nextDue" type="date" :class="inputClass" >
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
              class="inline-flex min-h-11 items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
              :disabled="submitting"
            >
              {{ submitting ? 'Completing…' : 'Complete maintenance' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
