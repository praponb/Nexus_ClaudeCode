<script setup lang="ts">
import type { StatusRef } from '~/types/api'
import StatusBadge from '~/components/StatusBadge.vue'

defineProps<{ status: StatusRef | null | undefined }>()
</script>

<template>
  <StatusBadge
    v-if="status"
    :label="status.label"
    :code="status.code"
    :treatment-hint="status.semantic_treatment"
  />
  <span v-else class="text-sm text-faint">Unknown status</span>
</template>
