<script setup lang="ts">
import type { AssetDetail } from '~/types/api'
import { ApiError } from '~/utils/errors'
import AppIcon from '~/components/AppIcon.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'

const props = withDefaults(
  defineProps<{
    open?: boolean
    asset: AssetDetail
  }>(),
  { open: false },
)

const emit = defineEmits<{
  (e: 'close' | 'reported'): void
}>()

const lifecycle = useLifecycleService()
const toast = useToast()

const EXCEPTION_TYPES = [
  { value: 'missing', label: 'Missing' },
  { value: 'lost', label: 'Lost' },
  { value: 'stolen', label: 'Stolen' },
  { value: 'damaged', label: 'Damaged' },
] as const

const exceptionType = ref<(typeof EXCEPTION_TYPES)[number]['value']>('missing')
const note = ref('')
const submitting = ref(false)
const error = ref<ApiError | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const titleId = useId()

watch(
  () => props.open,
  async (open) => {
    if (open) {
      exceptionType.value = 'missing'
      note.value = ''
      error.value = null
      await nextTick()
      panelRef.value?.querySelector<HTMLElement>('select')?.focus()
    }
  },
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') emit('close')
}

async function submit(): Promise<void> {
  if (submitting.value) return
  if (!note.value.trim()) {
    error.value = new ApiError('Describe what happened so the report can be investigated.', {
      code: 'VALIDATION_FAILED',
      status: 400,
    })
    return
  }
  submitting.value = true
  error.value = null
  try {
    await lifecycle.reportException(props.asset.uuid, {
      exception_type: exceptionType.value,
      note: note.value.trim(),
    })
    toast.success(`Exception reported for ${props.asset.tag}`)
    emit('reported')
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
          Report exception — <span class="font-mono text-accent">{{ asset.tag }}</span>
        </h2>
        <p class="mt-1 text-sm text-muted">
          Report this asset as missing, lost, stolen, or damaged. The original event is preserved
          even after the exception is resolved.
        </p>

        <InlineAlert v-if="error" tone="error" class="mt-4" :message="error.message" :correlation-id="error.correlationId" />

        <form class="mt-4 space-y-4" @submit.prevent="submit">
          <FormField v-slot="{ inputId }" label="Exception type" required>
            <select :id="inputId" v-model="exceptionType" :class="inputClass">
              <option v-for="t in EXCEPTION_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </FormField>
          <FormField v-slot="{ inputId }" label="What happened?" required>
            <textarea
              :id="inputId"
              v-model="note"
              rows="4"
              class="w-full rounded-lg border border-border bg-input px-3 py-2 text-sm text-ink focus:border-accent"
              placeholder="When and where was the asset last seen? Any damage details?"
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
              class="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-danger px-4 py-2 text-sm font-semibold text-canvas hover:bg-danger/90 disabled:opacity-60"
              :disabled="submitting"
            >
              <AppIcon v-if="!submitting" name="warning" size="sm" />
              {{ submitting ? 'Submitting…' : 'Submit exception report' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
