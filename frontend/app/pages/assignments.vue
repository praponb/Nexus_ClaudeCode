<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import PageHeader from '~/components/PageHeader.vue'
import AppIcon from '~/components/AppIcon.vue'
import AssetTable from '~/components/asset/AssetTable.vue'
import AssetCardList from '~/components/asset/AssetCardList.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'

// Assignment/transfer work queue (Operator+): assets currently in transit or
// assigned, built from the scoped asset register until a dedicated queue
// endpoint exists (assumption documented in the cycle summary).
definePageMeta({ title: 'Assignments' })
useHead({ title: 'Assignments' })

const service = useAssetsService()
const { canManageAssets } = usePermissions()
const { loaded } = useAuth()

const { data: inTransit, pending: pendingTransit, error: transitError, refresh: refreshTransit } =
  await useAsyncData(
    'queue-in-transit',
    () => service.list({ status: 'in_transit', page_size: 50, ordering: '-updated_at' }),
    { server: false },
  )

const { data: assigned, pending: pendingAssigned, error: assignedError, refresh: refreshAssigned } =
  await useAsyncData(
    'queue-assigned',
    () => service.list({ status: 'assigned', page_size: 50, ordering: '-updated_at' }),
    { server: false },
  )

const pending = computed(() => pendingTransit.value || pendingAssigned.value)
const error = computed(() => {
  const e = transitError.value || assignedError.value
  return e ? ApiError.fromUnknown(e) : null
})

function refreshAll(): void {
  void refreshTransit()
  void refreshAssigned()
}
</script>

<template>
  <div>
    <PageHeader
      title="Assignments and transfers"
      description="Assets currently checked out or moving between locations."
    />

    <InlineAlert
      v-if="loaded && !canManageAssets"
      tone="warning"
      title="Restricted work queue"
      message="Your role does not include the assignment work queue. Use the asset register to look up your own assets."
    />

    <LoadingSkeleton v-else-if="pending && !inTransit && !assigned" :lines="5" label="Loading work queue…" />
    <InlineAlert
      v-else-if="error"
      tone="error"
      title="Work queue could not be loaded"
      :message="error.message"
      :correlation-id="error.correlationId"
      retry-label="Retry"
      @retry="refreshAll"
    />

    <div v-else class="space-y-8">
      <section aria-labelledby="queue-transit">
        <h2 id="queue-transit" class="mb-3 flex items-center gap-2 text-lg font-semibold text-ink">
          <AppIcon name="refresh" class="text-info" />
          In transit
          <span class="text-sm font-normal text-muted">({{ inTransit?.count ?? 0 }})</span>
        </h2>
        <EmptyState
          v-if="!inTransit?.results.length"
          icon="info"
          title="Nothing in transit"
          message="Assets being transferred between locations will appear here until receipt is confirmed."
        />
        <template v-else>
          <div class="hidden lg:block"><AssetTable :items="inTransit.results" caption="Assets currently in transit" /></div>
          <div class="lg:hidden"><AssetCardList :items="inTransit.results" /></div>
        </template>
      </section>

      <section aria-labelledby="queue-assigned">
        <h2 id="queue-assigned" class="mb-3 flex items-center gap-2 text-lg font-semibold text-ink">
          <AppIcon name="user-circle" class="text-success" />
          Assigned
          <span class="text-sm font-normal text-muted">({{ assigned?.count ?? 0 }})</span>
        </h2>
        <EmptyState
          v-if="!assigned?.results.length"
          icon="info"
          title="No assigned assets"
          message="Assigned assets in your scope will appear here."
        />
        <template v-else>
          <div class="hidden lg:block"><AssetTable :items="assigned.results" caption="Assigned assets" /></div>
          <div class="lg:hidden"><AssetCardList :items="assigned.results" /></div>
        </template>
      </section>
    </div>
  </div>
</template>
