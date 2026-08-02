<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import type { IconName } from '~/utils/icons'
import { formatCount } from '~/utils/format'

const props = withDefaults(
  defineProps<{
    label: string
    value: number | string
    icon?: IconName
    /** When set, the card links to a filtered list (layout.md §10.1). */
    to?: string
    context?: string
  }>(),
  { icon: 'cube', to: '', context: '' },
)

const displayValue = computed(() =>
  typeof props.value === 'number' ? formatCount(props.value) : props.value,
)

const cardClass =
  'flex h-full flex-col gap-2 rounded-xl border border-border bg-surface p-4 transition-colors'
</script>

<template>
  <NuxtLink v-if="to" :to="to" :class="[cardClass, 'hover:border-border-strong hover:bg-hover']">
    <div class="flex items-center justify-between">
      <span class="text-sm font-medium text-muted">{{ label }}</span>
      <AppIcon :name="icon" class="text-accent" />
    </div>
    <p class="text-3xl font-bold text-ink">{{ displayValue }}</p>
    <p v-if="context" class="text-xs text-muted">{{ context }}</p>
  </NuxtLink>
  <div v-else :class="cardClass">
    <div class="flex items-center justify-between">
      <span class="text-sm font-medium text-muted">{{ label }}</span>
      <AppIcon :name="icon" class="text-accent" />
    </div>
    <p class="text-3xl font-bold text-ink">{{ displayValue }}</p>
    <p v-if="context" class="text-xs text-muted">{{ context }}</p>
  </div>
</template>
