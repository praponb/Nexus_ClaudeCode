<script setup lang="ts">
const props = defineProps<{
  assetUuid: string
  active: 'overview' | 'maintenance' | 'documents' | 'history'
}>()

const tabs = computed(() => [
  { key: 'overview' as const, label: 'Overview', to: `/assets/${props.assetUuid}` },
  { key: 'maintenance' as const, label: 'Maintenance', to: `/assets/${props.assetUuid}/maintenance` },
  { key: 'documents' as const, label: 'Documents', to: `/assets/${props.assetUuid}/documents` },
  { key: 'history' as const, label: 'History', to: `/assets/${props.assetUuid}/history` },
])
</script>

<template>
  <div role="tablist" aria-label="Asset sections" class="no-print flex gap-1 overflow-x-auto border-b border-border">
    <NuxtLink
      v-for="tab in tabs"
      :key="tab.key"
      :to="tab.to"
      role="tab"
      :aria-selected="tab.key === active"
      :aria-current="tab.key === active ? 'page' : undefined"
      class="whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium"
      :class="tab.key === active ? 'border-accent text-accent' : 'border-transparent text-muted hover:text-ink'"
    >
      {{ tab.label }}
    </NuxtLink>
  </div>
</template>
