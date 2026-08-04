<script setup lang="ts">
import { ApiError, isAuthError, isForbiddenError } from '~/utils/errors'
import {
  toApiParams,
  hasActiveFilters,
  serializeAssetFilters,
  savedViewConfigToQuery,
  type AssetListFilters,
} from '~/utils/filters'
import PageHeader from '~/components/PageHeader.vue'
import AppIcon from '~/components/AppIcon.vue'
import FilterBar from '~/components/filters/FilterBar.vue'
import FilterDrawer from '~/components/filters/FilterDrawer.vue'
import AssetTable from '~/components/asset/AssetTable.vue'
import AssetCardList from '~/components/asset/AssetCardList.vue'
import PaginationControls from '~/components/PaginationControls.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'

definePageMeta({ title: 'Assets' })
useHead({ title: 'Assets' })

const router = useRouter()
const service = useAssetsService()
const { filters, activeCount, setFilters, clearFilters } = useAssetFilters()
const { canManageAssets } = usePermissions()
const { views, pending: viewsPending, saveCurrent, remove } = useSavedViews()

const params = computed(() => toApiParams(filters.value))

const { data, pending, error, refresh } = await useAsyncData(
  'asset-list',
  () => service.list(params.value),
  { server: false, watch: [params] },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const items = computed(() => data.value?.results ?? [])
const total = computed(() => data.value?.count ?? 0)

const resultMessage = computed(() => {
  if (pending.value) return 'Loading assets…'
  if (apiError.value) return ''
  return `${total.value} asset${total.value === 1 ? '' : 's'} found.`
})

const drawerOpen = ref(false)

function updateFilters(patch: Partial<AssetListFilters>): void {
  setFilters(patch)
}

/* Saved views (own views: save / apply / delete — FR-006). */
const selectedView = ref('')
const saveDialogOpen = ref(false)
const viewName = ref('')

async function applyView(uuid: string): Promise<void> {
  selectedView.value = uuid
  if (!uuid) return
  const view = views.value.find((v) => v.uuid === uuid)
  if (!view) return
  // The stored config is nested; spreading it straight into `query` put the
  // whole `filters` object through toString() and produced a literal
  // `?filters=[object Object]`, silently losing the saved filters.
  await router.replace({ path: '/assets', query: savedViewConfigToQuery(view.config) })
}

async function saveView(): Promise<void> {
  const name = viewName.value.trim()
  if (!name) return
  const view = await saveCurrent(name, filters.value)
  if (view) {
    saveDialogOpen.value = false
    viewName.value = ''
    selectedView.value = view.uuid
  }
}

async function deleteView(): Promise<void> {
  if (!selectedView.value) return
  const ok = await remove(selectedView.value)
  if (ok) selectedView.value = ''
}

/** Carry the current filter state into the export center (FR-019). */
const exportQuery = computed(() => serializeAssetFilters(filters.value))

const selectClass =
  'h-11 rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent sm:h-10'
</script>

<template>
  <div>
    <PageHeader title="Asset register" description="Search, filter, and open assets in your scope.">
      <template #actions>
        <NuxtLink
          :to="{ path: '/exports', query: exportQuery }"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
        >
          <AppIcon name="archive" size="sm" />
          Export view
        </NuxtLink>
        <NuxtLink
          v-if="canManageAssets"
          to="/assets/new"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
        >
          <AppIcon name="plus" size="sm" />
          New asset
        </NuxtLink>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-center gap-2">
      <label for="saved-view-select" class="text-sm text-muted">Saved view</label>
      <select
        id="saved-view-select"
        :value="selectedView"
        :class="selectClass"
        @change="applyView(($event.target as HTMLSelectElement).value)"
      >
        <option value="">None</option>
        <option v-for="view in views" :key="view.uuid" :value="view.uuid">
          {{ view.name }}{{ view.shared ? ' (shared)' : '' }}
        </option>
      </select>
      <button
        type="button"
        class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-hover sm:min-h-10"
        @click="saveDialogOpen = !saveDialogOpen"
      >
        Save current view
      </button>
      <button
        v-if="selectedView"
        type="button"
        class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm font-medium text-danger hover:bg-hover sm:min-h-10"
        @click="deleteView"
      >
        Delete view
      </button>
    </div>

    <div v-if="saveDialogOpen" class="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface p-3">
      <label for="saved-view-name" class="text-sm text-ink-secondary">View name</label>
      <input
        id="saved-view-name"
        v-model="viewName"
        type="text"
        :class="selectClass"
        placeholder="For example: Laptops in Oslo"
        @keydown.enter.prevent="saveView"
      >
      <button
        type="button"
        class="inline-flex min-h-11 items-center rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60 sm:min-h-10"
        :disabled="!viewName.trim() || viewsPending"
        @click="saveView"
      >
        Save view
      </button>
    </div>

    <FilterBar
      :filters="filters"
      :active-count="activeCount"
      :pending="pending"
      class="mb-4"
      @update="updateFilters"
      @clear="clearFilters"
      @open-drawer="drawerOpen = true"
    />

    <p class="mb-3 text-sm text-muted" aria-live="polite">{{ resultMessage }}</p>

    <LoadingSkeleton v-if="pending && !items.length" :lines="5" label="Loading assets…" />

    <InlineAlert
      v-else-if="apiError && isForbiddenError(apiError)"
      tone="warning"
      title="You do not have access to these assets"
      message="Your role or organizational scope does not include this view. Contact an administrator if you believe this is wrong."
      :correlation-id="apiError.correlationId"
    />
    <InlineAlert
      v-else-if="apiError && !isAuthError(apiError)"
      tone="error"
      title="Assets could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />

    <EmptyState
      v-else-if="!items.length && hasActiveFilters(filters)"
      icon="search"
      title="No assets match your filters"
      message="Try broadening the search text or clearing some filters."
    >
      <button
        type="button"
        class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-raised px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
        @click="clearFilters"
      >
        Clear all filters
      </button>
    </EmptyState>

    <EmptyState
      v-else-if="!items.length"
      icon="cube"
      title="No assets registered yet"
      message="Register your first asset to start tracking it through its lifecycle."
      :action-to="canManageAssets ? '/assets/new' : ''"
      action-label="Register asset"
    />

    <template v-else>
      <div class="hidden lg:block" :aria-busy="pending">
        <AssetTable
          :items="items"
          :ordering="filters.ordering"
          caption="Asset register: tag, name, category, status, condition, custodian, department, location, and last update"
          @sort="(ordering) => setFilters({ ordering })"
        />
      </div>
      <div class="lg:hidden" :aria-busy="pending">
        <AssetCardList :items="items" />
      </div>

      <div class="mt-4">
        <PaginationControls
          :page="filters.page"
          :page-size="filters.pageSize"
          :total="total"
          :pending="pending"
          @change="(page) => setFilters({ page })"
        />
      </div>
    </template>

    <FilterDrawer
      :open="drawerOpen"
      :filters="filters"
      @close="drawerOpen = false"
      @apply="updateFilters"
      @clear="clearFilters"
    />
  </div>
</template>
