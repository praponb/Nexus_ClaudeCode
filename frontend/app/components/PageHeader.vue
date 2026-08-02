<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <header class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
    <div class="min-w-0">
      <nav v-if="$slots.breadcrumbs" aria-label="Breadcrumb" class="no-print mb-1 text-sm text-muted">
        <slot name="breadcrumbs" />
      </nav>
      <h1 class="text-2xl font-bold leading-tight text-ink">{{ title }}</h1>
      <p v-if="description" class="mt-1 max-w-2xl text-sm text-muted">{{ description }}</p>
      <div v-if="$slots.meta" class="mt-2 text-xs text-faint">
        <slot name="meta" />
      </div>
    </div>
    <div v-if="$slots.actions" class="no-print flex shrink-0 flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>
