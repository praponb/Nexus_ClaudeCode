<script setup lang="ts">
import type { ConditionRef } from '~/types/api'
import StatusBadge from '~/components/StatusBadge.vue'

defineProps<{ condition: ConditionRef | null | undefined }>()
</script>

<template>
  <StatusBadge
    v-if="condition"
    :label="condition.label"
    :code="condition.code"
    :treatment-hint="condition.semantic_treatment"
  />
  <span v-else class="text-sm text-faint">Unknown condition</span>
</template>
