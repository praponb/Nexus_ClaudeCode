<script setup lang="ts">
import StatusBadge from '~/components/StatusBadge.vue'
import { codeToLabel } from '~/utils/status'

defineProps<{ outcome: string | null | undefined }>()
</script>

<template>
  <StatusBadge :label="codeToLabel(outcome)" :code="outcome === 'found' ? 'available' : outcome" :treatment-hint="outcome" />
</template>
