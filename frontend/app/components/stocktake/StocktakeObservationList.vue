<script setup lang="ts">
import type { StocktakeObservation } from '~/types/workflow'
import StocktakeOutcomeBadge from '~/components/stocktake/StocktakeOutcomeBadge.vue'
import EmptyState from '~/components/EmptyState.vue'
import { formatDateTime } from '~/utils/format'

defineProps<{ observations: StocktakeObservation[] }>()
</script>

<template>
  <EmptyState
    v-if="!observations.length"
    icon="scan"
    title="No observations yet"
    message="Scan or enter asset tags on the count page to record observations."
  />
  <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
    <table class="min-w-full divide-y divide-border text-sm">
      <caption class="sr-only">Stocktake observations</caption>
      <thead class="bg-raised">
        <tr>
          <th scope="col" class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted">Tag</th>
          <th scope="col" class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted">Outcome</th>
          <th scope="col" class="hidden px-3 py-2 text-left text-xs font-semibold uppercase text-muted sm:table-cell">Asset</th>
          <th scope="col" class="hidden px-3 py-2 text-left text-xs font-semibold uppercase text-muted md:table-cell">Condition</th>
          <th scope="col" class="px-3 py-2 text-left text-xs font-semibold uppercase text-muted">Observed</th>
          <th scope="col" class="hidden px-3 py-2 text-left text-xs font-semibold uppercase text-muted lg:table-cell">Note</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr v-for="obs in observations" :key="obs.uuid">
          <td class="whitespace-nowrap px-3 py-2 font-mono text-accent">{{ obs.tag_scanned }}</td>
          <td class="whitespace-nowrap px-3 py-2"><StocktakeOutcomeBadge :outcome="obs.outcome" /></td>
          <td class="hidden max-w-48 truncate px-3 py-2 text-ink-secondary sm:table-cell">
            <NuxtLink v-if="obs.asset" :to="`/assets/${obs.asset.uuid}`" class="rounded hover:text-accent">
              {{ obs.asset.name }}
            </NuxtLink>
            <span v-else class="text-faint">Unknown asset</span>
          </td>
          <td class="hidden px-3 py-2 text-ink-secondary md:table-cell">{{ obs.condition?.label || '—' }}</td>
          <td class="whitespace-nowrap px-3 py-2 text-muted">{{ formatDateTime(obs.observed_at) }}</td>
          <td class="hidden max-w-56 truncate px-3 py-2 text-ink-secondary lg:table-cell">{{ obs.note || '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
