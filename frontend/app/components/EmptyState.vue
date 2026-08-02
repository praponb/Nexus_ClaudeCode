<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import type { IconName } from '~/utils/icons'

withDefaults(
  defineProps<{
    title: string
    message?: string
    icon?: IconName
    /** Optional primary action link. */
    actionTo?: string
    actionLabel?: string
  }>(),
  { message: '', icon: 'info', actionTo: '', actionLabel: '' },
)
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 rounded-xl border border-border bg-surface px-6 py-12 text-center">
    <div class="flex h-12 w-12 items-center justify-center rounded-full bg-raised text-muted">
      <AppIcon :name="icon" size="lg" />
    </div>
    <h2 class="text-lg font-semibold text-ink">{{ title }}</h2>
    <p v-if="message" class="max-w-md text-sm text-muted">{{ message }}</p>
    <div class="mt-2 flex flex-wrap items-center justify-center gap-3">
      <NuxtLink
        v-if="actionTo && actionLabel"
        :to="actionTo"
        class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
      >
        {{ actionLabel }}
      </NuxtLink>
      <slot />
    </div>
  </div>
</template>
