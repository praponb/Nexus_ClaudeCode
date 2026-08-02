<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import { parseScannedTag } from '~/utils/scan'

const emit = defineEmits<{ (e: 'lookup', tag: string): void }>()

const props = withDefaults(defineProps<{ initial?: string; busy?: boolean }>(), {
  initial: '',
  busy: false,
})

const value = ref(props.initial)
const error = ref('')

watch(
  () => props.initial,
  (v) => {
    if (v) value.value = v
  },
)

function submit(): void {
  error.value = ''
  const tag = parseScannedTag(value.value)
  if (!tag) {
    error.value = 'Enter a valid asset tag, for example AST-000123, or paste a scan deep link.'
    return
  }
  emit('lookup', tag)
}
</script>

<template>
  <form class="space-y-3" @submit.prevent="submit">
    <label for="manual-tag" class="block text-sm font-medium text-ink-secondary">
      Enter asset tag manually
    </label>
    <div class="flex gap-2">
      <input
        id="manual-tag"
        v-model="value"
        type="text"
        class="h-11 min-w-0 flex-1 rounded-lg border border-border bg-input px-3 font-mono text-sm text-ink placeholder:text-faint focus:border-accent"
        :class="error ? 'border-danger' : ''"
        placeholder="AST-000123"
        autocomplete="off"
        autocapitalize="characters"
        :aria-invalid="Boolean(error)"
        aria-describedby="manual-tag-error"
      >
      <button
        type="submit"
        class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
        :disabled="busy"
      >
        <AppIcon name="search" size="sm" />
        {{ busy ? 'Looking up…' : 'Look up' }}
      </button>
    </div>
    <p v-if="error" id="manual-tag-error" class="text-sm text-danger" role="alert">{{ error }}</p>
  </form>
</template>
