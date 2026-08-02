<script setup lang="ts">
import { ApiError, isAuthError, isNotFoundError } from '~/utils/errors'
import type { AssetDetail } from '~/types/api'
import PageHeader from '~/components/PageHeader.vue'
import AssetForm from '~/components/asset/AssetForm.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'

definePageMeta({ title: 'Edit asset' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const service = useAssetsService()
const { canManageAssets } = usePermissions()
const { loaded } = useAuth()

const { data: asset, pending, error, refresh } = await useAsyncData(
  `asset-edit-${uuid.value}`,
  () => service.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

useHead(() => ({ title: asset.value ? `Edit ${asset.value.tag}` : 'Edit asset' }))

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))

function onSaved(saved: AssetDetail): void {
  void navigateTo(`/assets/${saved.uuid}`)
}

/** Reload latest server state after a version conflict; remounts the form. */
async function onReload(): Promise<void> {
  await refresh()
}
</script>

<template>
  <div>
    <PageHeader title="Edit asset" :description="asset ? `${asset.tag} · ${asset.name}` : ''">
      <template #breadcrumbs>
        <ol class="flex items-center gap-1">
          <li><NuxtLink to="/assets" class="rounded hover:text-ink">Assets</NuxtLink></li>
          <li aria-hidden="true">/</li>
          <li>
            <NuxtLink :to="`/assets/${uuid}`" class="rounded hover:text-ink">{{ asset?.tag || 'Asset' }}</NuxtLink>
          </li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" class="text-ink-secondary">Edit</li>
        </ol>
      </template>
    </PageHeader>

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
      v-else-if="apiError && !isAuthError(apiError)"
      tone="error"
      title="Asset could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <InlineAlert
      v-else-if="loaded && !canManageAssets"
      tone="warning"
      title="You cannot edit assets"
      message="Your role does not include asset editing. Contact an asset manager or operator."
    />
    <!-- :key remounts the form after a conflict reload, clearing stale state. -->
    <AssetForm
      v-else-if="asset"
      :key="`${asset.uuid}-${asset.updated_at}`"
      mode="edit"
      :initial="asset"
      @saved="onSaved"
      @reload="onReload"
    />
  </div>
</template>
