<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import PageHeader from '~/components/PageHeader.vue'
import MaintenanceRecordList from '~/components/maintenance/MaintenanceRecordList.vue'
import MaintenanceCompleteDialog from '~/components/maintenance/MaintenanceCompleteDialog.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import PaginationControls from '~/components/PaginationControls.vue'
import type { MaintenanceRecord } from '~/types/workflow'

// Maintenance work list (Operator+, FR-011): open work first, overdue flagged
// with icon + text (never color alone, layout §14.4).
definePageMeta({ title: 'Maintenance' })
useHead({ title: 'Maintenance' })

const service = useMaintenanceService()
const { canManageAssets } = usePermissions()
const { loaded } = useAuth()

const page = ref(1)
const { data, pending, error, refresh } = await useAsyncData(
  'maintenance-list',
  () => service.list({ page: page.value, page_size: 50, ordering: 'next_due' }),
  { server: false, watch: [page] },
)

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
    <PageHeader title="Maintenance" description="Open repair and service work, plus maintenance history." />

    <InlineAlert
      v-if="loaded && !canManageAssets"
      tone="warning"
      title="Restricted module"
      message="Your role does not include the maintenance work list."
    />
    <LoadingSkeleton v-else-if="pending && !records.length" :lines="4" label="Loading maintenance…" />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Maintenance records could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />

    <template v-else>
      <MaintenanceRecordList
        :records="records"
        show-asset
        :can-complete="canManageAssets"
        @complete="openComplete"
      />
      <div class="mt-4">
        <PaginationControls
          :page="page"
          :page-size="50"
          :total="data?.count ?? 0"
          :pending="pending"
          @change="(p) => (page = p)"
        />
      </div>
    </template>

    <MaintenanceCompleteDialog
      :open="completeOpen"
      :record="completeTarget"
      @close="completeOpen = false"
      @completed="refresh()"
    />
  </div>
</template>
