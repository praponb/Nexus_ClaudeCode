<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'

// Reports catalog (FR-021): the default report set, scoped to what the
// signed-in role may see. Each report opens the viewer with filters.
definePageMeta({ title: 'Reports' })
useHead({ title: 'Reports' })

const service = useReportsService()
const { canApprove, isAuditor } = usePermissions()
const { loaded } = useAuth()

const canViewReports = computed(() => canApprove.value || isAuditor.value)

const { data, pending, error, refresh } = await useAsyncData(
  'reports-catalog',
  () => service.catalog(),
  { server: false },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const reports = computed(() => data.value ?? [])
</script>

<template>
  <div>
    <PageHeader
      title="Reports"
      description="Operational and audit reports over the records you are permitted to see."
    />

    <InlineAlert
      v-if="loaded && !canViewReports"
      tone="warning"
      title="Restricted module"
      message="Your role does not include the reports catalog."
    />

    <LoadingSkeleton v-else-if="pending && !reports.length" :lines="4" label="Loading reports…" />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Reports could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <EmptyState
      v-else-if="!reports.length"
      icon="chart"
      title="No reports available"
      message="The server did not return any report definitions for your role."
    />

    <ul v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      <li v-for="report in reports" :key="report.type">
        <NuxtLink
          :to="`/reports/${report.type}`"
          class="block h-full rounded-xl border border-border bg-surface p-4 hover:border-border-strong hover:bg-hover"
        >
          <div class="flex items-center gap-2">
            <AppIcon name="chart" class="shrink-0 text-accent" />
            <h2 class="font-semibold text-ink">{{ report.name }}</h2>
          </div>
          <p v-if="report.description" class="mt-2 text-sm text-muted">{{ report.description }}</p>
          <p v-if="report.filters?.length" class="mt-2 text-xs text-faint">
            Filters: {{ report.filters.map((f) => f.label).join(', ') }}
          </p>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
