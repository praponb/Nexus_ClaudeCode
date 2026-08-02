<script setup lang="ts">
import type { HistoryEvent, Paginated } from '~/types/api'
import { ApiError, isAuthError, isNotFoundError } from '~/utils/errors'
import AppIcon from '~/components/AppIcon.vue'
import AssetActivityTimeline from '~/components/asset/AssetActivityTimeline.vue'
import AssetDetailTabs from '~/components/asset/AssetDetailTabs.vue'
import AssetNotesPanel from '~/components/asset/AssetNotesPanel.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'

definePageMeta({ title: 'Asset history' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const service = useAssetsService()

const { data: asset } = await useAsyncData(
  `asset-head-${uuid.value}`,
  () => service.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

/** Full activity feed (FR-029); fall back to the C1 history endpoint if absent. */
async function fetchFeed(): Promise<Paginated<HistoryEvent>> {
  try {
    return await service.activity(uuid.value)
  } catch (e) {
    if (isNotFoundError(e)) return service.history(uuid.value)
    throw e
  }
}

const { data, pending, error, refresh } = await useAsyncData(
  `asset-history-${uuid.value}`,
  fetchFeed,
  { server: false, watch: [uuid] },
)

useHead(() => ({ title: asset.value ? `History · ${asset.value.tag}` : 'Asset history' }))

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const events = computed(() => data.value?.results ?? [])
</script>

<template>
  <div>
    <nav aria-label="Breadcrumb" class="no-print mb-4 text-sm text-muted">
      <ol class="flex items-center gap-1">
        <li><NuxtLink to="/assets" class="rounded hover:text-ink">Assets</NuxtLink></li>
        <li aria-hidden="true">/</li>
        <li>
          <NuxtLink :to="`/assets/${uuid}`" class="rounded hover:text-ink">{{ asset?.tag || 'Asset' }}</NuxtLink>
        </li>
        <li aria-hidden="true">/</li>
        <li aria-current="page" class="text-ink-secondary">History</li>
      </ol>
    </nav>

    <div class="mb-6">
      <h1 class="text-2xl font-bold text-ink">History</h1>
      <p v-if="asset" class="mt-1 text-sm text-muted">
        <span class="font-mono text-accent">{{ asset.tag }}</span> · {{ asset.name }}
      </p>
    </div>

    <div class="mb-6">
      <AssetDetailTabs :asset-uuid="uuid" active="history" />
    </div>

    <div class="mb-6 max-w-2xl">
      <AssetNotesPanel :asset-uuid="uuid" @added="refresh()" />
    </div>

    <LoadingSkeleton v-if="pending && !events.length" :lines="4" label="Loading history…" />
    <EmptyState
      v-else-if="apiError && isNotFoundError(apiError)"
      icon="search"
      title="Asset not found"
      message="This asset does not exist or is outside your organizational scope."
      action-to="/assets"
      action-label="Back to asset register"
    />
    <InlineAlert
      v-else-if="apiError && !isAuthError(apiError)"
      tone="error"
      title="History could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <EmptyState
      v-else-if="!events.length"
      icon="clock"
      title="No history yet"
      message="Lifecycle, assignment, maintenance, and note events will appear here as the asset is used."
      :action-to="`/assets/${uuid}`"
      action-label="Back to asset"
    />
    <div v-else>
      <p v-if="data?.next" class="mb-4 flex items-center gap-2 text-sm text-muted">
        <AppIcon name="info" size="sm" />
        Showing the {{ events.length }} most recent events.
      </p>
      <AssetActivityTimeline :events="events" />
    </div>
  </div>
</template>
