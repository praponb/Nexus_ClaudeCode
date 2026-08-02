<script setup lang="ts">
import { ApiError, isAuthError } from '~/utils/errors'
import { formatDateTime } from '~/utils/format'
import PageHeader from '~/components/PageHeader.vue'
import DashboardKpiCard from '~/components/dashboard/DashboardKpiCard.vue'
import AssetActivityTimeline from '~/components/asset/AssetActivityTimeline.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import AppIcon from '~/components/AppIcon.vue'
import type { HistoryEvent } from '~/types/api'

// Dashboard (FR-020): scoped KPIs, alert indicators linking to filtered
// lists, ranked lists as the accessible chart alternative (D-15), and recent
// activity — all with a last-refreshed timestamp.
definePageMeta({ title: 'Dashboard' })
useHead({ title: 'Dashboard' })

const service = useDashboardService()
const { canManageAssets } = usePermissions()

const { data, pending, error, refresh } = await useAsyncData(
  'dashboard-summary',
  () => service.summary(),
  { server: false },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))

const topStatuses = computed(() => [...(data.value?.by_status ?? [])].sort((a, b) => b.count - a.count).slice(0, 8))
const topCategories = computed(() => [...(data.value?.by_category ?? [])].sort((a, b) => b.count - a.count).slice(0, 8))
const maxStatus = computed(() => Math.max(1, ...topStatuses.value.map((s) => s.count)))
const maxCategory = computed(() => Math.max(1, ...topCategories.value.map((c) => c.count)))

const hasAlerts = computed(() => {
  const d = data.value
  if (!d) return false
  return [d.overdue_returns, d.maintenance_due, d.warranty_expiring, d.missing].some(
    (v) => typeof v === 'number',
  )
})

// The dashboard's recent-activity feed is a lighter projection than the
// full per-asset HistoryEvent shape AssetActivityTimeline expects (no
// actor/uuid/details; asset identity nested) -- map it explicitly rather
// than assuming the shapes match.
const recentActivity = computed<HistoryEvent[]>(() =>
  (data.value?.recent_activity ?? []).map((event) => ({
    uuid: event.asset?.uuid ?? event.occurred_at,
    type: event.event_type,
    actor: 'System',
    occurred_at: event.occurred_at,
    summary: event.summary,
  })),
)
</script>

<template>
  <div>
    <PageHeader title="Dashboard" description="A scoped overview of the assets you can see.">
      <template #actions>
        <div class="flex flex-wrap gap-2">
          <NuxtLink
            v-if="canManageAssets"
            to="/data-quality"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
          >
            <AppIcon name="success" size="sm" />
            Data quality
          </NuxtLink>
          <NuxtLink
            v-if="canManageAssets"
            to="/assets/new"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
          >
            <AppIcon name="plus" size="sm" />
            New asset
          </NuxtLink>
        </div>
      </template>
      <template v-if="data?.generated_at" #meta>
        Last refreshed {{ formatDateTime(data.generated_at) }}
      </template>
    </PageHeader>

    <LoadingSkeleton v-if="pending && !data" :lines="4" label="Loading dashboard…" />

    <InlineAlert
      v-else-if="apiError && !isAuthError(apiError)"
      tone="error"
      title="Dashboard data could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />

    <EmptyState
      v-else-if="data && data.total_assets === 0"
      icon="cube"
      title="No assets yet"
      message="There are no assets in your scope. Register the first asset to start building the inventory."
      :action-to="canManageAssets ? '/assets/new' : ''"
      action-label="Register asset"
    />

    <div v-else-if="data" class="space-y-6">
      <section aria-label="Key figures" class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <DashboardKpiCard label="Total assets" :value="data.total_assets" icon="cube" to="/assets" context="In your scope" />
        <DashboardKpiCard label="Assigned" :value="data.assigned" icon="user-circle" to="/assignments" context="With a custodian" />
        <DashboardKpiCard label="Unassigned" :value="data.unassigned" icon="tag" to="/assets" context="Available to assign" />
        <DashboardKpiCard
          label="Status types"
          :value="data.by_status.length"
          icon="tasks"
          to="/assets"
          context="Distinct lifecycle states"
        />
      </section>

      <section v-if="hasAlerts" aria-label="Attention needed" class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <DashboardKpiCard
          v-if="typeof data.overdue_returns === 'number'"
          label="Overdue returns"
          :value="data.overdue_returns"
          icon="warning"
          to="/assignments"
          context="Expected back earlier"
        />
        <DashboardKpiCard
          v-if="typeof data.maintenance_due === 'number'"
          label="Maintenance due"
          :value="data.maintenance_due"
          icon="wrench"
          to="/maintenance"
          context="Scheduled or overdue work"
        />
        <DashboardKpiCard
          v-if="typeof data.warranty_expiring === 'number'"
          label="Warranty expiring"
          :value="data.warranty_expiring"
          icon="clock"
          to="/assets"
          context="Within the warning window"
        />
        <DashboardKpiCard
          v-if="typeof data.missing === 'number'"
          label="Missing"
          :value="data.missing"
          icon="error"
          to="/assets?status=missing"
          context="Reported missing or lost"
        />
      </section>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section aria-labelledby="dash-by-status" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
          <h2 id="dash-by-status" class="text-base font-semibold text-ink">Assets by status</h2>
          <ul class="mt-4 space-y-3">
            <li v-for="row in topStatuses" :key="row.code">
              <NuxtLink
                :to="{ path: '/assets', query: { status: row.code } }"
                class="group block rounded-lg p-1 hover:bg-hover"
                :aria-label="`${row.label}: ${row.count} assets. Open filtered list.`"
              >
                <div class="flex items-center justify-between text-sm">
                  <span class="text-ink-secondary group-hover:text-ink">{{ row.label }}</span>
                  <span class="font-semibold text-ink">{{ row.count }}</span>
                </div>
                <div class="mt-1 h-2 rounded-full bg-input" aria-hidden="true">
                  <div class="h-2 rounded-full bg-accent" :style="{ width: `${Math.max(4, (row.count / maxStatus) * 100)}%` }" />
                </div>
              </NuxtLink>
            </li>
          </ul>
          <p v-if="!topStatuses.length" class="mt-4 text-sm text-muted">No status data available.</p>
        </section>

        <section aria-labelledby="dash-by-category" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
          <h2 id="dash-by-category" class="text-base font-semibold text-ink">Assets by category</h2>
          <ul class="mt-4 space-y-3">
            <li v-for="row in topCategories" :key="row.uuid">
              <NuxtLink
                :to="{ path: '/assets', query: { category: row.uuid } }"
                class="group block rounded-lg p-1 hover:bg-hover"
                :aria-label="`${row.name}: ${row.count} assets. Open filtered list.`"
              >
                <div class="flex items-center justify-between text-sm">
                  <span class="text-ink-secondary group-hover:text-ink">{{ row.name }}</span>
                  <span class="font-semibold text-ink">{{ row.count }}</span>
                </div>
                <div class="mt-1 h-2 rounded-full bg-input" aria-hidden="true">
                  <div class="h-2 rounded-full bg-info" :style="{ width: `${Math.max(4, (row.count / maxCategory) * 100)}%` }" />
                </div>
              </NuxtLink>
            </li>
          </ul>
          <p v-if="!topCategories.length" class="mt-4 text-sm text-muted">No category data available.</p>
        </section>
      </div>

      <section v-if="recentActivity.length" aria-labelledby="dash-activity" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="dash-activity" class="text-base font-semibold text-ink">Recent activity</h2>
        <div class="mt-4">
          <AssetActivityTimeline :events="recentActivity" />
        </div>
      </section>
    </div>
  </div>
</template>
