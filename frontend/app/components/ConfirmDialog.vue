<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'

const props = withDefaults(
  defineProps<{
    open?: boolean
    title: string
    message: string
    confirmLabel?: string
    cancelLabel?: string
    tone?: 'primary' | 'danger'
    busy?: boolean
  }>(),
  {
    open: false,
    confirmLabel: 'Confirm',
    cancelLabel: 'Cancel',
    tone: 'primary',
    busy: false,
  },
)

const emit = defineEmits<{ (e: 'confirm' | 'cancel'): void }>()

const titleId = useId()
const descId = useId()
const panelRef = ref<HTMLElement | null>(null)
let previouslyFocused: Element | null = null

watch(
  () => props.open,
  async (open) => {
    if (open) {
      previouslyFocused = document.activeElement
      await nextTick()
      const target = panelRef.value?.querySelector<HTMLElement>('[data-autofocus]') ?? panelRef.value
      target?.focus()
    } else if (previouslyFocused instanceof HTMLElement) {
      previouslyFocused.focus()
      previouslyFocused = null
    }
  },
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.stopPropagation()
    emit('cancel')
    return
  }
  if (event.key !== 'Tab' || !panelRef.value) return
  const focusable = panelRef.value.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
  )
  if (!focusable.length) return
  const first = focusable[0]!
  const last = focusable[focusable.length - 1]!
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

const confirmClass = computed(() =>
  props.tone === 'danger'
    ? 'bg-danger text-canvas hover:bg-danger/90'
    : 'bg-accent text-on-accent hover:bg-accent-hover',
)
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6">
      <div class="absolute inset-0 bg-canvas/80" aria-hidden="true" @click="emit('cancel')" />
      <div
        ref="panelRef"
        role="alertdialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="descId"
        tabindex="-1"
        class="relative w-full max-w-lg rounded-t-2xl border border-border bg-raised p-6 shadow-2xl sm:rounded-2xl"
        @keydown="onKeydown"
      >
        <div class="flex items-start gap-3">
          <div
            v-if="tone === 'danger'"
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-danger/10 text-danger"
          >
            <AppIcon name="warning" />
          </div>
          <div class="min-w-0">
            <h2 :id="titleId" class="text-lg font-semibold text-ink">{{ title }}</h2>
            <p :id="descId" class="mt-2 text-sm text-ink-secondary">{{ message }}</p>
          </div>
        </div>
        <div class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            class="inline-flex min-h-11 items-center justify-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
            :disabled="busy"
            @click="emit('cancel')"
          >
            {{ cancelLabel }}
          </button>
          <button
            type="button"
            data-autofocus
            class="inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-60"
            :class="confirmClass"
            :disabled="busy"
            @click="emit('confirm')"
          >
            {{ busy ? 'Working…' : confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
