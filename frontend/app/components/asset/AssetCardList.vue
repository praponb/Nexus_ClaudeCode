<script setup lang="ts">
import type { AssetSummary } from '~/types/api'
import AppIcon from '~/components/AppIcon.vue'
import AssetStatusBadge from '~/components/asset/AssetStatusBadge.vue'

withDefaults(
  defineProps<{
    items: AssetSummary[]
  }>(),
  {},
)
</script>

<template>
  <ul class="space-y-3">
    <li v-for="asset in items" :key="asset.uuid" class="rounded-xl border border-border bg-surface p-4">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <NuxtLink :to="`/assets/${asset.uuid}`" class="rounded font-mono text-sm font-medium text-accent hover:text-accent-hover">
            {{ asset.tag }}
          </NuxtLink>
          <h3 class="mt-0.5 break-words font-semibold text-ink">
            <NuxtLink :to="`/assets/${asset.uuid}`" class="rounded hover:text-accent">{{ asset.name }}</NuxtLink>
          </h3>
        </div>
        <AssetStatusBadge :status="asset.status" size="sm" />
      </div>

      <dl class="mt-3 grid grid-cols-1 gap-x-4 gap-y-1 text-sm">
        <div v-if="asset.category" class="flex gap-2">
          <dt class="text-muted">Category</dt>
          <dd class="text-ink-secondary">{{ asset.category.name }}</dd>
        </div>
        <div class="flex gap-2">
          <dt class="text-muted">Custodian</dt>
          <dd class="text-ink-secondary">{{ asset.custodian?.display_name || 'Unassigned' }}</dd>
        </div>
        <div v-if="asset.location" class="flex gap-2">
          <dt class="text-muted">Location</dt>
          <dd class="text-ink-secondary">{{ asset.location.name }}</dd>
        </div>
      </dl>

      <p v-if="asset.warnings?.length" class="mt-2 flex items-center gap-1.5 text-sm text-warning">
        <AppIcon name="warning" size="sm" />
        {{ asset.warnings[0] }}
      </p>

      <div class="mt-3 border-t border-border pt-3">
        <NuxtLink
          :to="`/assets/${asset.uuid}`"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-raised px-3 py-2 text-sm font-medium text-ink hover:bg-hover"
          :aria-label="`View details for asset ${asset.tag}`"
        >
          View details
          <AppIcon name="chevron-right" size="sm" />
        </NuxtLink>
      </div>
    </li>
  </ul>
</template>
