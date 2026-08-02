<script setup lang="ts">
import type { DuplicateCandidate } from '~/types/api'
import InlineAlert from '~/components/InlineAlert.vue'

defineProps<{
  warnings: string[]
  candidates: DuplicateCandidate[]
}>()
</script>

<template>
  <div class="space-y-3 rounded-lg border border-warning/40 bg-warning/5 p-4">
    <InlineAlert
      tone="warning"
      title="Possible duplicate assets"
      :message="warnings.length ? warnings.join(' ') : 'Existing assets look similar to the one you are registering. Review them before saving.'"
    />
    <ul v-if="candidates.length" class="space-y-2">
      <li
        v-for="candidate in candidates"
        :key="candidate.uuid"
        class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2"
      >
        <div class="min-w-0">
          <NuxtLink :to="`/assets/${candidate.uuid}`" class="rounded font-mono text-sm text-accent hover:text-accent-hover">
            {{ candidate.tag }}
          </NuxtLink>
          <span class="ml-2 text-sm text-ink-secondary">{{ candidate.name }}</span>
          <p v-if="candidate.match_reasons.length" class="text-xs text-muted">
            Matches: {{ candidate.match_reasons.join(', ') }}
          </p>
        </div>
        <NuxtLink
          :to="`/assets/${candidate.uuid}`"
          class="inline-flex min-h-11 items-center rounded-lg px-3 py-1 text-sm font-medium text-accent hover:bg-hover sm:min-h-0"
        >
          Review
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
