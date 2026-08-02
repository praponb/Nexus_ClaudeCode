<script setup lang="ts">
/**
 * Labeled form field wrapper. Renders label, optional hint and error, and
 * provides ids to the slotted control via slot props so the input owns the
 * aria attributes (no placeholder-only labels, layout.md §13.2).
 */
const props = withDefaults(
  defineProps<{
    label: string
    required?: boolean
    hint?: string
    error?: string | null
    id?: string
  }>(),
  { required: false, hint: '', error: null, id: '' },
)

const autoId = useId()
const inputId = computed(() => props.id || `field-${autoId}`)
const hintId = computed(() => `${inputId.value}-hint`)
const errorId = computed(() => `${inputId.value}-error`)
const describedBy = computed(() =>
  [props.hint ? hintId.value : '', props.error ? errorId.value : ''].filter(Boolean).join(' ') || undefined,
)
</script>

<template>
  <div class="space-y-1.5">
    <label :for="inputId" class="block text-sm font-medium text-ink-secondary">
      {{ label }}
      <span v-if="required" class="text-danger" aria-hidden="true"> *</span>
      <span v-if="required" class="sr-only">(required)</span>
    </label>
    <slot :input-id="inputId" :described-by="describedBy" :invalid="Boolean(error)" />
    <p v-if="hint" :id="hintId" class="text-xs text-muted">{{ hint }}</p>
    <p v-if="error" :id="errorId" class="flex items-center gap-1 text-sm text-danger" role="alert">
      {{ error }}
    </p>
  </div>
</template>
