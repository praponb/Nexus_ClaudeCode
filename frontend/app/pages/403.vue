<script setup lang="ts">
import EmptyState from '~/components/EmptyState.vue'

definePageMeta({ title: 'Access denied' })
useHead({ title: 'Access denied' })
</script>

<template>
  <EmptyState
    icon="warning"
    title="Access denied"
    message="You do not have permission to view this page. If you believe this is a mistake, contact your administrator."
    action-to="/"
    action-label="Go to dashboard"
  />
</template>
