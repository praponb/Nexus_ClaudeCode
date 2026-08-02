<script setup lang="ts">
import { ApiError, isAuthError, isNotFoundError } from '~/utils/errors'
import type { MaintenanceRecord } from '~/types/workflow'
import AssetDetailTabs from '~/components/asset/AssetDetailTabs.vue'
import MaintenanceRecordForm from '~/components/maintenance/MaintenanceRecordForm.vue'
import MaintenanceRecordList from '~/components/maintenance/MaintenanceRecordList.vue'
import MaintenanceCompleteDialog from '~/components/maintenance/MaintenanceCompleteDialog.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'

// Asset maintenance tab (FR-011/FR-012): records for this asset + new record.
definePageMeta({ title: 'Asset maintenance' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const assets = useAssetsService()
const maintenance = useMaintenanceService()
const { canManageAssets } = usePermissions()

const { data: asset, error: assetError } = await useAsyncData(
  `asset-maint-head-${uuid.value}`,
  () => assets.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

const { data, pending, error, refresh } = await useAsyncData(
  `asset-maint-${uuid.value}`,
  () => maintenance.list({ asset: uuid.value, page_size: 100 }),
  { server: false, watch: [uuid] },
)

useHead(() => ({ title: asset.value ? `Maintenance · ${asset.value.tag}` : 'Asset maintenance' }))

const notFound = computed(() => isNotFoundError(assetError.value))
const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const records = computed(() => data.value?.results ?? [])

const completeTarget = ref<MaintenanceRecord | null>(null)
const completeOpen = ref(false)

function openComplete(record: MaintenanceRecord): void {
  completeTarget.value = record
  completeOpen.value = true
}
</script>

<template>
  <div>
    <nav aria-label="Breadcrumb" class="no-print mb-4 text-sm text-muted">
      <ol class="flex items-center gap-1">
        <li><NuxtLink to="/assets" class="rounded hover:text-ink">Assets</NuxtLink></li>
        <li aria-hidden="true">/</li>
        <li><NuxtLink :to="`/assets/${uuid}`" class="rounded hover:text-ink">{{ asset?.tag || 'Asset' }}</NuxtLink></li>
        <li aria-hidden="true">/</li>
        <li aria-current="page" class="text-ink-secondary">Maintenance</li>
      </ol>
    </nav>

    <div class="mb-6">
      <h1 class="text-2xl font-bold text-ink">Maintenance</h1>
      <p v-if="asset" class="mt-1 text-sm text-muted">
        <span class="font-mono text-accent">{{ asset.tag }}</span> · {{ asset.name }}
      </p>
    </div>

    <div class="mb-6">
      <AssetDetailTabs :asset-uuid="uuid" active="maintenance" />
    </div>

    <EmptyState
      v-if="notFound"
      icon="search"
      title="Asset not found"
      message="This asset does not exist or is outside your organizational scope."
      action-to="/assets"
      action-label="Back to asset register"
    />

    <template v-else>
      <div v-if="canManageAssets" class="mb-6">
        <MaintenanceRecordForm :asset-uuid="uuid" @created="refresh()" />
      </div>

      <LoadingSkeleton v-if="pending && !records.length" :lines="3" label="Loading maintenance records…" />
      <InlineAlert
        v-else-if="apiError && !isAuthError(apiError)"
        tone="error"
        title="Maintenance records could not be loaded"
        :message="apiError.message"
        :correlation-id="apiError.correlationId"
        retry-label="Retry"
        @retry="refresh()"
      />
      <MaintenanceRecordList
        v-else
        :records="records"
        :can-complete="canManageAssets"
        @complete="openComplete"
      />
    </template>

    <MaintenanceCompleteDialog
      :open="completeOpen"
      :record="completeTarget"
      @close="completeOpen = false"
      @completed="refresh()"
    />
  </div>
</template>
