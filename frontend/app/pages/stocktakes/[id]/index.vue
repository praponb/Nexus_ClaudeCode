<script setup lang="ts">
import { ApiError, isNotFoundError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import type { StocktakeObservation, VarianceRow } from '~/types/workflow'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import StocktakeProgress from '~/components/stocktake/StocktakeProgress.vue'
import StocktakeObservationList from '~/components/stocktake/StocktakeObservationList.vue'
import StocktakeOutcomeBadge from '~/components/stocktake/StocktakeOutcomeBadge.vue'
import ConfirmDialog from '~/components/ConfirmDialog.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import { formatDate } from '~/utils/format'

// Stocktake session detail (FR-022): progress, observations, and the
// start → reconcile → close lifecycle with confirmation and variance review
// before any master-data updates.
definePageMeta({ title: 'Stocktake session' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const service = useStocktakeService()
const toast = useToast()
const { canManageAssets, canApprove } = usePermissions()

const { data: session, pending, error, refresh } = await useAsyncData(
  `stocktake-${uuid.value}`,
  () => service.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

const observations = ref<StocktakeObservation[]>([])
const variance = ref<VarianceRow[]>([])
const varianceError = ref(false)

async function loadLists(): Promise<void> {
  try {
    observations.value = await service.observations(uuid.value)
  } catch {
    observations.value = session.value?.observations ?? []
  }
  try {
    varianceError.value = false
    variance.value = await service.variance(uuid.value)
  } catch {
    varianceError.value = true
    variance.value = []
  }
}

onMounted(loadLists)
watch(session, () => void loadLists())

useHead(() => ({ title: session.value ? `Stocktake · ${session.value.name}` : 'Stocktake session' }))

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const notFound = computed(() => apiError.value && isNotFoundError(apiError.value))

const statusCode = computed(() => (session.value?.status ?? '').toLowerCase())
const isDraft = computed(() => ['draft', 'planned', 'created'].includes(statusCode.value))
const isOpen = computed(() => ['open', 'in_progress', 'active', 'counting'].includes(statusCode.value))
const isClosed = computed(() => ['closed', 'completed'].includes(statusCode.value))

const actionBusy = ref(false)
const actionError = ref<ApiError | null>(null)
const reconcileConfirm = ref(false)
const closeConfirm = ref(false)

async function doAction(action: 'start' | 'reconcile' | 'close'): Promise<void> {
  if (actionBusy.value) return
  actionBusy.value = true
  actionError.value = null
  try {
    if (action === 'start') await service.start(uuid.value)
    if (action === 'reconcile') await service.reconcile(uuid.value)
    if (action === 'close') await service.close(uuid.value)
    toast.success(
      action === 'start' ? 'Stocktake started' : action === 'reconcile' ? 'Reconciliation applied' : 'Stocktake closed',
    )
    await refresh()
    await loadLists()
  } catch (e) {
    actionError.value = ApiError.fromUnknown(e)
  } finally {
    actionBusy.value = false
    reconcileConfirm.value = false
    closeConfirm.value = false
  }
}
</script>

<template>
  <div>
    <LoadingSkeleton v-if="pending && !session" :lines="4" label="Loading stocktake…" />
    <EmptyState
      v-else-if="notFound"
      icon="search"
      title="Stocktake not found"
      message="This session does not exist or is outside your scope."
      action-to="/stocktakes"
      action-label="Back to stocktakes"
    />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Stocktake could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />

    <div v-else-if="session" class="space-y-6">
      <PageHeader :title="session.name" :description="session.instructions || ''">
        <template #breadcrumbs>
          <ol class="flex items-center gap-1">
            <li><NuxtLink to="/stocktakes" class="rounded hover:text-ink">Stocktakes</NuxtLink></li>
            <li aria-hidden="true">/</li>
            <li aria-current="page" class="text-ink-secondary">{{ session.name }}</li>
          </ol>
        </template>
        <template #meta>
          <StatusBadge :label="codeToLabel(session.status)" :code="session.status" size="sm" />
          <span class="ml-2">
            <span v-if="session.start_date">Starts {{ formatDate(session.start_date) }}</span>
            <span v-if="session.due_date"> · Due {{ formatDate(session.due_date) }}</span>
          </span>
        </template>
        <template #actions>
          <button
            v-if="isDraft && canManageAssets"
            type="button"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
            :disabled="actionBusy"
            @click="doAction('start')"
          >
            <AppIcon name="check" size="sm" />
            Start stocktake
          </button>
          <NuxtLink
            v-if="!isClosed"
            :to="`/stocktakes/${uuid}/count`"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
          >
            <AppIcon name="scan" size="sm" />
            Count assets
          </NuxtLink>
          <button
            v-if="isOpen && canApprove"
            type="button"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
            @click="reconcileConfirm = true"
          >
            Reconcile
          </button>
          <button
            v-if="isOpen && canApprove"
            type="button"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-danger/50 bg-danger/10 px-4 py-2 text-sm font-medium text-danger hover:bg-danger/20"
            @click="closeConfirm = true"
          >
            Close session
          </button>
        </template>
      </PageHeader>

      <InlineAlert v-if="actionError" tone="error" :message="actionError.message" :correlation-id="actionError.correlationId" />

      <StocktakeProgress :session="session" />

      <section aria-labelledby="stocktake-observations">
        <h2 id="stocktake-observations" class="mb-3 text-lg font-semibold text-ink">
          Observations
          <span class="text-sm font-normal text-muted">({{ observations.length }})</span>
        </h2>
        <StocktakeObservationList :observations="observations" />
      </section>

      <section v-if="variance.length" aria-labelledby="stocktake-variance">
        <h2 id="stocktake-variance" class="mb-3 text-lg font-semibold text-ink">
          Variance
          <span class="text-sm font-normal text-muted">({{ variance.length }})</span>
        </h2>
        <ul class="space-y-2">
          <li
            v-for="(row, index) in variance"
            :key="row.uuid ?? index"
            class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2"
          >
            <div class="min-w-0">
              <NuxtLink
                v-if="row.asset"
                :to="`/assets/${row.asset.uuid}`"
                class="rounded font-mono text-sm text-accent hover:text-accent-hover"
              >
                {{ row.asset.tag }}
              </NuxtLink>
              <span v-else class="font-mono text-sm text-ink-secondary">{{ row.tag_scanned || 'Unknown tag' }}</span>
              <span v-if="row.asset" class="ml-2 text-sm text-ink-secondary">{{ row.asset.name }}</span>
              <p v-if="row.note" class="text-xs text-muted">{{ row.note }}</p>
            </div>
            <StocktakeOutcomeBadge :outcome="row.outcome" />
          </li>
        </ul>
      </section>
      <p v-else-if="varianceError" class="text-sm text-muted">
        Variance is available after reconciliation has run.
      </p>
    </div>

    <ConfirmDialog
      :open="reconcileConfirm"
      title="Apply reconciliation?"
      :message="`Reviewed variances will update master asset data for “${session?.name ?? ''}”. Every change is recorded in the audit history.`"
      confirm-label="Apply reconciliation"
      :busy="actionBusy"
      @confirm="doAction('reconcile')"
      @cancel="reconcileConfirm = false"
    />
    <ConfirmDialog
      :open="closeConfirm"
      title="Close this stocktake?"
      :message="`Closing “${session?.name ?? ''}” ends counting and produces the final variance report. This cannot be undone.`"
      confirm-label="Close stocktake"
      tone="danger"
      :busy="actionBusy"
      @confirm="doAction('close')"
      @cancel="closeConfirm = false"
    />
  </div>
</template>
