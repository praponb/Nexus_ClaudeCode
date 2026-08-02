<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'

const { toasts, dismiss, toneIcon } = useToast()

const toneClass: Record<string, string> = {
  success: 'border-success/40 text-success',
  error: 'border-danger/40 text-danger',
  warning: 'border-warning/40 text-warning',
  info: 'border-info/40 text-info',
}
</script>

<template>
  <div
    aria-live="polite"
    aria-atomic="false"
    class="no-print pointer-events-none fixed inset-x-3 bottom-20 z-[60] flex flex-col gap-2 sm:inset-x-auto sm:bottom-6 sm:right-6 sm:w-96 lg:bottom-6"
  >
    <div
      v-for="toast in toasts"
      :key="toast.id"
      class="pointer-events-auto flex items-start gap-3 rounded-lg border bg-raised p-3 shadow-xl"
      :class="toneClass[toast.tone]"
    >
      <AppIcon :name="toneIcon(toast.tone)" class="mt-0.5 shrink-0" />
      <div class="min-w-0 flex-1">
        <p class="text-sm font-semibold text-ink">{{ toast.title }}</p>
        <p v-if="toast.description" class="mt-0.5 text-sm text-ink-secondary">{{ toast.description }}</p>
      </div>
      <button
        type="button"
        class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-muted hover:bg-hover hover:text-ink sm:min-h-8 sm:min-w-8"
        :aria-label="`Dismiss notification: ${toast.title}`"
        @click="dismiss(toast.id)"
      >
        <AppIcon name="close" size="sm" />
      </button>
    </div>
  </div>
</template>
