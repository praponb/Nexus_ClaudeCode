<script setup lang="ts">
import { ApiError, isAuthError, isForbiddenError, isNotFoundError } from '~/utils/errors'
import { formatDate, formatDateTime, formatMoney, isPastDate } from '~/utils/format'
import AppIcon from '~/components/AppIcon.vue'
import AssetIdentityHeader from '~/components/asset/AssetIdentityHeader.vue'
import AssetActionBar from '~/components/asset/AssetActionBar.vue'
import AssetDetailTabs from '~/components/asset/AssetDetailTabs.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'

definePageMeta({ title: 'Asset detail' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const service = useAssetsService()
const { canManageAssets, canViewFinance } = usePermissions()

const { data: asset, pending, error, refresh } = await useAsyncData(
  `asset-${uuid.value}`,
  () => service.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

useHead(() => ({ title: asset.value ? `${asset.value.tag} · ${asset.value.name}` : 'Asset detail' }))

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))

interface DetailRow {
  label: string
  value: string
  mono?: boolean
}

const identityRows = computed<DetailRow[]>(() => {
  const a = asset.value
  if (!a) return []
  return [
    { label: 'Serial number', value: a.serial_number || '—', mono: true },
    { label: 'Manufacturer', value: a.manufacturer || '—' },
    { label: 'Model', value: a.model || '—' },
    { label: 'Category', value: a.category?.name || '—' },
    { label: 'Department', value: a.department?.name || '—' },
    { label: 'Location', value: a.location?.name || '—' },
    { label: 'Registered', value: formatDateTime(a.created_at) },
    { label: 'Last updated', value: formatDateTime(a.updated_at) },
  ]
})

const financeRows = computed<DetailRow[]>(() => {
  const a = asset.value
  if (!a) return []
  return [
    { label: 'Purchase date', value: a.purchase_date ? formatDate(a.purchase_date) : '—' },
    { label: 'Purchase price', value: formatMoney(a.purchase_price) },
    { label: 'Supplier', value: a.supplier?.name || '—' },
    { label: 'Warranty start', value: a.warranty_start ? formatDate(a.warranty_start) : '—' },
    { label: 'Warranty end', value: a.warranty_end ? formatDate(a.warranty_end) : '—' },
  ]
})

const warrantyExpired = computed(() => isPastDate(asset.value?.warranty_end))
</script>

<template>
  <div>
    <nav aria-label="Breadcrumb" class="no-print mb-4 text-sm text-muted">
      <ol class="flex items-center gap-1">
        <li><NuxtLink to="/assets" class="rounded hover:text-ink">Assets</NuxtLink></li>
        <li aria-hidden="true">/</li>
        <li aria-current="page" class="max-w-48 truncate text-ink-secondary">{{ asset?.tag || 'Asset' }}</li>
      </ol>
    </nav>

    <LoadingSkeleton v-if="pending && !asset" :lines="5" label="Loading asset…" />

    <EmptyState
      v-else-if="apiError && isNotFoundError(apiError)"
      icon="search"
      title="Asset not found"
      message="This asset does not exist or is outside your organizational scope."
      action-to="/assets"
      action-label="Back to asset register"
    />
    <InlineAlert
      v-else-if="apiError && isForbiddenError(apiError)"
      tone="warning"
      title="You do not have access to this asset"
      message="Your role or organizational scope does not include this asset."
      :correlation-id="apiError.correlationId"
    />
    <InlineAlert
      v-else-if="apiError && !isAuthError(apiError)"
      tone="error"
      title="Asset could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />

    <div v-else-if="asset" class="space-y-6">
      <AssetIdentityHeader :asset="asset">
        <template #actions>
          <NuxtLink
            v-if="canManageAssets"
            :to="`/assets/${asset.uuid}/edit`"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
          >
            <AppIcon name="pencil" size="sm" />
            Edit asset
          </NuxtLink>
        </template>
      </AssetIdentityHeader>

      <AssetActionBar :asset="asset" @changed="refresh()" />

      <AssetDetailTabs :asset-uuid="asset.uuid" active="overview" />

      <InlineAlert
        v-if="warrantyExpired"
        tone="warning"
        title="Warranty expired"
        :message="`The warranty for this asset ended on ${formatDate(asset.warranty_end)}.`"
      />

      <section aria-labelledby="asset-description-heading" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="asset-description-heading" class="text-base font-semibold text-ink">Description</h2>
        <p class="mt-2 whitespace-pre-line text-sm text-ink-secondary">{{ asset.description || 'No description recorded.' }}</p>
      </section>

      <section aria-labelledby="asset-identity-heading" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="asset-identity-heading" class="text-base font-semibold text-ink">Identity and placement</h2>
        <dl class="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="row in identityRows" :key="row.label">
            <dt class="text-muted">{{ row.label }}</dt>
            <dd class="mt-0.5 break-words text-ink" :class="row.mono ? 'font-mono' : ''">{{ row.value }}</dd>
          </div>
        </dl>
      </section>

      <section
        v-if="canViewFinance"
        aria-labelledby="asset-finance-heading"
        class="rounded-xl border border-border bg-surface p-4 sm:p-6"
      >
        <h2 id="asset-finance-heading" class="text-base font-semibold text-ink">Financial and warranty</h2>
        <dl class="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="row in financeRows" :key="row.label">
            <dt class="text-muted">{{ row.label }}</dt>
            <dd class="mt-0.5 break-words text-ink">{{ row.value }}</dd>
          </div>
        </dl>
      </section>
    </div>
  </div>
</template>
