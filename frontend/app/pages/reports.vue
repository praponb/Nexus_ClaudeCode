<script setup lang="ts">
// Reports module shell: the catalog lives in reports/index.vue, the viewer in
// reports/[type].vue. This parent only routes between them.
definePageMeta({ title: 'Reports' })
</script>

<template>
  <NuxtPage />
</template>
