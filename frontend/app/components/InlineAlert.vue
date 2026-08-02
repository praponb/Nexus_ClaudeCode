<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '~/components/AppIcon.vue'
import type { ToastTone } from '~/composables/useToast'

const props = withDefaults(
  defineProps<{
    tone?: ToastTone
    title?: string
    message: string
    /** Support reference shown for unexpected failures (layout.md §20.2). */
    correlationId?: string | null
    retryLabel?: string
  }>(),
  { tone: 'info', title: '', correlationId: null, retryLabel: '' },
)

const emit = defineEmits<{ (e: 'retry'): void }>()

const toneClass = computed(() => {
  switch (props.tone) {
    case 'success':
      return 'border-success/40 bg-success/10 text-success'
    case 'warning':
      return 'border-warning/40 bg-warning/10 text-warning'
    case 'error':
      return 'border-danger/40 bg-danger/10 text-danger'
    default:
      return 'border-info/40 bg-info/10 text-info'
  }
})

const toneIcon = computed(() => {
  switch (props.tone) {
    case 'success':
      return 'success' as const
    case 'warning':
      return 'warning' as const
    case 'error':
      return 'error' as const
    default:
      return 'info' as const
  }
})
</script>

<template>
  <div class="flex gap-3 rounded-lg border p-4" :class="toneClass" :role="tone === 'error' || tone === 'warning' ? 'alert' : 'status'">
    <AppIcon :name="toneIcon" class="mt-0.5 shrink-0" />
    <div class="min-w-0 flex-1">
      <p v-if="title" class="font-semibold text-ink">{{ title }}</p>
      <p class="text-sm text-ink-secondary">{{ message }}</p>
      <p v-if="correlationId" class="mt-1 font-mono text-xs text-muted">
        Support reference: {{ correlationId }}
      </p>
      <button
        v-if="retryLabel"
        type="button"
        class="mt-2 inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-raised px-3 py-1.5 text-sm font-medium text-ink hover:bg-hover sm:min-h-0"
        @click="emit('retry')"
      >
        <AppIcon name="refresh" size="sm" />
        {{ retryLabel }}
      </button>
    </div>
  </div>
</template>
