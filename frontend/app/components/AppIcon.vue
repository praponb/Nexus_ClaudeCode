<script setup lang="ts">
import { computed } from 'vue'
import { ICON_PATHS, type IconName } from '~/utils/icons'

const props = withDefaults(
  defineProps<{
    name: IconName
    size?: 'sm' | 'md' | 'lg'
    /** Decorative icons are hidden from assistive tech (default). */
    decorative?: boolean
  }>(),
  { size: 'md', decorative: true },
)

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'h-4 w-4'
    case 'lg':
      return 'h-6 w-6'
    default:
      return 'h-5 w-5'
  }
})

const paths = computed(() => ICON_PATHS[props.name])
</script>

<template>
  <svg
    :class="sizeClass"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    :aria-hidden="decorative ? 'true' : undefined"
    focusable="false"
  >
    <path v-for="(d, i) in paths" :key="i" :d="d" />
  </svg>
</template>
