<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '~/components/AppIcon.vue'
import { treatmentForStatus } from '~/utils/status'

const props = withDefaults(
  defineProps<{
    /** Human-readable label — always rendered as text (never color alone). */
    label: string
    code?: string | null
    /** Backend-provided semantic_treatment takes precedence when present. */
    treatmentHint?: string | null
    size?: 'sm' | 'md'
  }>(),
  { code: null, treatmentHint: null, size: 'md' },
)

const style = computed(() => treatmentForStatus(props.code, props.treatmentHint))
const sizeClass = computed(() => (props.size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'))
</script>

<template>
  <span
    class="inline-flex max-w-full items-center gap-1.5 rounded-full border font-medium"
    :class="[style.badgeClass, sizeClass]"
  >
    <AppIcon :name="style.icon" size="sm" class="shrink-0" />
    <span class="truncate">{{ label }}</span>
  </span>
</template>
