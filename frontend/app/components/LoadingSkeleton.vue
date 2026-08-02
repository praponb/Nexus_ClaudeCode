<script setup lang="ts">
withDefaults(
  defineProps<{
    lines?: number
    label?: string
  }>(),
  { lines: 4, label: 'Loading…' },
)
</script>

<template>
  <div role="status" class="space-y-3">
    <span class="sr-only">{{ label }}</span>
    <div
      v-for="i in lines"
      :key="i"
      class="h-12 animate-pulse rounded-lg border border-border bg-surface"
      :style="{ opacity: String(1 - (i - 1) * 0.15) }"
      aria-hidden="true"
    />
  </div>
</template>
