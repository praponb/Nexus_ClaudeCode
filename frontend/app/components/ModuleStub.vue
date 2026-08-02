<script setup lang="ts">
import EmptyState from '~/components/EmptyState.vue'
import PageHeader from '~/components/PageHeader.vue'

withDefaults(
  defineProps<{
    title: string
    description?: string
  }>(),
  { description: '' },
)
</script>

<template>
  <div>
    <PageHeader :title="title" :description="description" />
    <EmptyState
      icon="clock"
      title="Coming in a later release"
      message="This module is part of the delivery plan and is not available yet. The Assets register and Dashboard are available now."
      action-to="/assets"
      action-label="Open asset register"
    />
  </div>
</template>
