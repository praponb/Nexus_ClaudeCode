<script setup lang="ts">
import { ApiError, isNotFoundError } from '~/utils/errors'
import AppIcon from '~/components/AppIcon.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import EmptyState from '~/components/EmptyState.vue'

// QR label print view (FR-017, design D-14): server-rendered QR encoding the
// asset tag + deep link, 50×25mm print target, light print background.
definePageMeta({ title: 'Asset QR label' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const assets = useAssetsService()
const toast = useToast()

const { data: asset, error: assetError } = await useAsyncData(
  `asset-label-head-${uuid.value}`,
  () => assets.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

const { data: label, pending, error, refresh } = await useAsyncData(
  `asset-label-${uuid.value}`,
  () => assets.label(uuid.value),
  { server: false, watch: [uuid] },
)

useHead(() => ({ title: asset.value ? `QR label · ${asset.value.tag}` : 'Asset QR label' }))

const notFound = computed(() => isNotFoundError(assetError.value))
const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))

const deepLink = computed(() => {
  if (label.value?.deepLink) return label.value.deepLink
  if (import.meta.client) return `${window.location.origin}/scan?tag=${asset.value?.tag ?? ''}`
  return ''
})

async function copyLink(): Promise<void> {
  try {
    await navigator.clipboard.writeText(deepLink.value)
    toast.success('Deep link copied')
  } catch {
    toast.error('Could not copy the link')
  }
}

function printLabel(): void {
  window.print()
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
        <li aria-current="page" class="text-ink-secondary">QR label</li>
      </ol>
    </nav>

    <EmptyState
      v-if="notFound"
      icon="search"
      title="Asset not found"
      message="This asset does not exist or is outside your organizational scope."
      action-to="/assets"
      action-label="Back to asset register"
    />

    <template v-else>
      <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="text-2xl font-bold text-ink">QR label</h1>
          <p v-if="asset" class="mt-1 text-sm text-muted">
            <span class="font-mono text-accent">{{ asset.tag }}</span> · {{ asset.name }}
          </p>
        </div>
        <button
          type="button"
          class="no-print inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
          @click="printLabel"
        >
          Print label
        </button>
      </div>

      <LoadingSkeleton v-if="pending && !label" :lines="2" label="Loading label…" />
      <InlineAlert
        v-else-if="apiError"
        tone="error"
        title="Label could not be generated"
        :message="apiError.message"
        :correlation-id="apiError.correlationId"
        retry-label="Retry"
        @retry="refresh()"
      />

      <div v-else class="space-y-6">
        <!-- Print target: 50×25mm on a light background (layout §27). -->
        <div
          class="inline-flex items-center gap-3 rounded-md border border-border-strong bg-white p-2 text-black print:border-none"
          style="width: 50mm; min-height: 25mm"
        >
          <!-- eslint-disable-next-line vue/no-v-html -- server-rendered SVG from our own backend -->
          <div v-if="label?.svg" class="h-20 w-20 shrink-0 [&>svg]:h-full [&>svg]:w-full" aria-hidden="true" v-html="label.svg" />
          <div class="min-w-0">
            <p class="font-mono text-sm font-bold">{{ asset?.tag }}</p>
            <p class="truncate text-xs">{{ asset?.name }}</p>
          </div>
        </div>

        <div class="no-print rounded-xl border border-border bg-surface p-4 sm:max-w-xl sm:p-6">
          <h2 class="text-sm font-semibold text-ink">Deep link encoded in this QR code</h2>
          <p class="mt-2 break-all font-mono text-xs text-ink-secondary">{{ deepLink }}</p>
          <button
            type="button"
            class="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-raised px-3 py-2 text-sm font-medium text-ink hover:bg-hover"
            @click="copyLink"
          >
            <AppIcon name="copy" size="sm" />
            Copy link
          </button>
          <p class="mt-3 text-xs text-muted">
            Print at 100% scale so the QR code remains scannable at the 50×25mm label size.
          </p>
        </div>
      </div>
    </template>
  </div>
</template>
