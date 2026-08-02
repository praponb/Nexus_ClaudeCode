<script setup lang="ts">
import EmptyState from '~/components/EmptyState.vue'

definePageMeta({ title: 'Page not found' })
useHead({ title: 'Page not found' })
</script>

<template>
  <EmptyState
    icon="search"
    title="Page not found"
    message="The page you are looking for does not exist or has moved."
    action-to="/"
    action-label="Go to dashboard"
  />
</template>
