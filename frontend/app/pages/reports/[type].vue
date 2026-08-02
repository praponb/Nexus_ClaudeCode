<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { formatDateTime } from '~/utils/format'
import { formatReportCell, normalizeColumns, reportCellLink } from '~/utils/report'
import type { ReportDefinition } from '~/types/control'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'

// Report viewer (FR-021): date-range + declared filters, reconciled totals,
// supporting-record links, and authorized export.
definePageMeta({ title: 'Report' })

const route = useRoute()
const reportType = computed(() => String(route.params.type))
const service = useReportsService()
const toast = useToast()

/* Definition (from the catalog; tolerant if the catalog is unavailable). */
const { data: catalog } = await useAsyncData('reports-catalog', () => service.catalog(), {
  server: false,
})
const definition = computed<ReportDefinition | null>(
  () => catalog.value?.find((r) => r.type === reportType.value) ?? null,
)

useHead(() => ({ title: definition.value?.name || 'Report' }))

/* Filters: date range always available; declared filters rendered by type. */
const dateFrom = ref('')
const dateTo = ref('')
const extraFilters = ref<Record<string, string>>({})

watch(
  definition,
  (def) => {
    const next: Record<string, string> = {}
    for (const f of def?.filters ?? []) next[f.key] = ''
    extraFilters.value = next
  },
  { immediate: true },
)

const queryParams = computed(() => {
  const params: Record<string, string> = {}
  if (dateFrom.value) params.date_from = dateFrom.value
  if (dateTo.value) params.date_to = dateTo.value
  for (const [key, value] of Object.entries(extraFilters.value)) {
    if (value) params[key] = value
  }
  return params
})

const appliedParams = ref<Record<string, string>>({})

const { data: result, pending, error, refresh } = await useAsyncData(
  `report-${reportType.value}`,
  () => service.run(reportType.value, appliedParams.value),
  { server: false, watch: [appliedParams] },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const columns = computed(() => normalizeColumns(result.value))
const rows = computed(() => result.value?.rows ?? [])
const totals = computed(() => result.value?.totals ?? null)

function applyFilters(): void {
  appliedParams.value = { ...queryParams.value }
}

/* Export (authorized roles; backend re-enforces). */
const exporting = ref(false)
async function exportReport(): Promise<void> {
  if (exporting.value) return
  exporting.value = true
  try {
    const res = await service.exportReport(reportType.value, queryParams.value)
    if (res && typeof res === 'object' && 'uuid' in res) {
      toast.success('Export queued', 'Track progress and download it in the export center.')
    } else {
      toast.success('Export requested')
    }
  } catch (e) {
    toast.error('Export failed', ApiError.fromUnknown(e).message)
  } finally {
    exporting.value = false
  }
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent'
</script>

<template>
  <div>
    <nav aria-label="Breadcrumb" class="mb-4 text-sm text-muted">
      <ol class="flex items-center gap-1">
        <li><NuxtLink to="/reports" class="rounded hover:text-ink">Reports</NuxtLink></li>
        <li aria-hidden="true">/</li>
        <li aria-current="page" class="text-ink-secondary">{{ definition?.name || reportType }}</li>
      </ol>
    </nav>

    <PageHeader :title="definition?.name || 'Report'" :description="definition?.description || ''">
      <template #actions>
        <button
          type="button"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover disabled:opacity-60"
          :disabled="exporting"
          @click="exportReport"
        >
          <AppIcon name="archive" size="sm" />
          {{ exporting ? 'Requesting…' : 'Export' }}
        </button>
      </template>
      <template v-if="result?.generated_at" #meta>
        Generated {{ formatDateTime(result.generated_at) }}
      </template>
    </PageHeader>

    <form
      class="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4"
      aria-label="Report filters"
      @submit.prevent="applyFilters"
    >
      <FormField v-slot="{ inputId }" label="From date" class="w-40">
        <input :id="inputId" v-model="dateFrom" type="date" :class="inputClass" >
      </FormField>
      <FormField v-slot="{ inputId }" label="To date" class="w-40">
        <input :id="inputId" v-model="dateTo" type="date" :class="inputClass" >
      </FormField>
      <FormField
        v-for="filter in definition?.filters ?? []"
        :key="filter.key"
        v-slot="{ inputId }"
        :label="filter.label"
        class="w-44"
      >
        <select v-if="filter.type === 'select'" :id="inputId" v-model="extraFilters[filter.key]" :class="inputClass">
          <option value="">All</option>
          <option v-for="option in filter.options ?? []" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <input
          v-else
          :id="inputId"
          v-model="extraFilters[filter.key]"
          :type="filter.type === 'date' ? 'date' : 'text'"
          :class="inputClass"
        >
      </FormField>
      <button
        type="submit"
        class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
      >
        <AppIcon name="filter" size="sm" />
        Apply filters
      </button>
    </form>

    <LoadingSkeleton v-if="pending && !rows.length" :lines="5" label="Running report…" />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="The report could not be generated"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <EmptyState
      v-else-if="result && !rows.length"
      icon="chart"
      title="No matching records"
      message="No records in your permitted scope match the current filters."
    />

    <div v-else-if="result" class="overflow-x-auto rounded-xl border border-border bg-surface">
      <table class="min-w-full divide-y divide-border text-sm">
        <caption class="sr-only">
          {{ definition?.name || 'Report' }} results — totals reconcile with the records you are permitted to see
        </caption>
        <thead class="bg-raised">
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              scope="col"
              class="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="(row, i) in rows" :key="i" class="hover:bg-hover">
            <td v-for="col in columns" :key="col.key" class="whitespace-nowrap px-3 py-2 text-ink-secondary">
              <NuxtLink
                v-if="reportCellLink(row[col.key])"
                :to="reportCellLink(row[col.key])!"
                class="rounded text-accent hover:text-accent-hover"
              >
                {{ formatReportCell(row[col.key]) }}
              </NuxtLink>
              <template v-else>{{ formatReportCell(row[col.key]) }}</template>
            </td>
          </tr>
        </tbody>
        <tfoot v-if="totals" class="border-t border-border-strong bg-raised">
          <tr>
            <td v-for="col in columns" :key="col.key" class="whitespace-nowrap px-3 py-2 text-sm font-semibold text-ink">
              {{ col.key in totals ? formatReportCell(totals[col.key]) : col === columns[0] ? 'Totals' : '' }}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>
