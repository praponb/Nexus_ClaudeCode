<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import InlineAlert from '~/components/InlineAlert.vue'

const props = defineProps<{ assetUuid: string }>()
const emit = defineEmits<{ (e: 'added'): void }>()

const service = useAssetsService()
const toast = useToast()

const body = ref('')
const submitting = ref(false)
const error = ref<ApiError | null>(null)

async function submit(): Promise<void> {
  if (submitting.value || !body.value.trim()) return
  submitting.value = true
  error.value = null
  try {
    await service.addNote(props.assetUuid, body.value.trim())
    body.value = ''
    toast.success('Note added')
    emit('added')
  } catch (e) {
    error.value = ApiError.fromUnknown(e)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="rounded-xl border border-border bg-surface p-4" @submit.prevent="submit">
    <label for="asset-note-body" class="block text-sm font-medium text-ink-secondary">
      Add a note
    </label>
    <textarea
      id="asset-note-body"
      v-model="body"
      rows="3"
      class="mt-2 w-full rounded-lg border border-border bg-input px-3 py-2 text-sm text-ink placeholder:text-faint focus:border-accent"
      placeholder="Notes are timestamped and attributed to you. Corrections are append-only."
    />
    <InlineAlert v-if="error" tone="error" class="mt-2" :message="error.message" :correlation-id="error.correlationId" />
    <div class="mt-3 flex justify-end">
      <button
        type="submit"
        class="inline-flex min-h-11 items-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
        :disabled="submitting || !body.trim()"
      >
        {{ submitting ? 'Adding…' : 'Add note' }}
      </button>
    </div>
  </form>
</template>
