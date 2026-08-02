<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import type { ReferenceDataItem, ReferenceDataType } from '~/types/control'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'

// Reference data administration (FR-026): create/edit/deactivate. In-use
// values are deactivated, never deleted (BR-004); deactivate is idempotent
// and audited (Rev 1.2 §11.1.10).
definePageMeta({ title: 'Reference data' })
useHead({ title: 'Reference data' })

const service = useAdminService()
const toast = useToast()
const { refresh: refreshSharedRefData } = useReferenceData()

const TYPES: Array<{ value: ReferenceDataType; label: string }> = [
  { value: 'categories', label: 'Categories' },
  { value: 'statuses', label: 'Statuses' },
  { value: 'conditions', label: 'Conditions' },
  { value: 'departments', label: 'Departments' },
  { value: 'locations', label: 'Locations' },
  { value: 'cost-centers', label: 'Cost centers' },
  { value: 'suppliers', label: 'Suppliers' },
]

const activeType = ref<ReferenceDataType>('categories')
const items = ref<ReferenceDataItem[]>([])
const pending = ref(false)
const error = ref<ApiError | null>(null)

async function load(): Promise<void> {
  pending.value = true
  error.value = null
  try {
    items.value = await service.listReferenceData(activeType.value)
  } catch (e) {
    error.value = ApiError.fromUnknown(e)
  } finally {
    pending.value = false
  }
}

watch(activeType, () => void load(), { immediate: import.meta.client })

/* Create form */
const createOpen = ref(false)
const newName = ref('')
const newCode = ref('')
const newDescription = ref('')
const creating = ref(false)
const createError = ref<ApiError | null>(null)

async function create(): Promise<void> {
  createError.value = null
  if (!newName.value.trim() || !newCode.value.trim()) {
    createError.value = new ApiError('Name and code are both required.', { code: 'VALIDATION_FAILED', status: 400 })
    return
  }
  if (creating.value) return
  creating.value = true
  try {
    await service.createReferenceData(activeType.value, {
      name: newName.value.trim(),
      code: newCode.value.trim(),
      description: newDescription.value.trim() || undefined,
    })
    toast.success(`${codeToLabel(activeType.value)} entry created`)
    createOpen.value = false
    newName.value = ''
    newCode.value = ''
    newDescription.value = ''
    await load()
    await refreshSharedRefData()
  } catch (e) {
    createError.value = ApiError.fromUnknown(e)
  } finally {
    creating.value = false
  }
}

/* Activate/deactivate */
const busyUuid = ref<string | null>(null)
const confirmDeactivate = ref<ReferenceDataItem | null>(null)

async function setActive(item: ReferenceDataItem, active: boolean): Promise<void> {
  if (busyUuid.value) return
  busyUuid.value = item.uuid
  try {
    await service.updateReferenceData(activeType.value, item.uuid, { active })
    toast.success(`${item.name} ${active ? 'reactivated' : 'deactivated'}`)
    await load()
    await refreshSharedRefData()
  } catch (e) {
    toast.error('Update failed', ApiError.fromUnknown(e).message)
  } finally {
    busyUuid.value = null
  }
}

/** BR-004 deactivate: never destroys the row; repeat calls are idempotent. */
async function deactivate(item: ReferenceDataItem): Promise<void> {
  if (busyUuid.value) return
  busyUuid.value = item.uuid
  try {
    await service.deactivateReferenceData(activeType.value, item.uuid)
    toast.success(`${item.name} deactivated`)
    confirmDeactivate.value = null
    await load()
    await refreshSharedRefData()
  } catch (e) {
    toast.error('Deactivation failed', ApiError.fromUnknown(e).message)
  } finally {
    busyUuid.value = null
  }
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent'
</script>

<template>
  <div>
    <PageHeader title="Reference data" description="Lists that drive asset categorization and lifecycle rules.">
      <template #actions>
        <button
          type="button"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
          @click="createOpen = !createOpen"
        >
          <AppIcon name="plus" size="sm" />
          New entry
        </button>
      </template>
    </PageHeader>

    <div role="tablist" aria-label="Reference data types" class="mb-4 flex flex-wrap gap-1">
      <button
        v-for="t in TYPES"
        :key="t.value"
        type="button"
        role="tab"
        :aria-selected="activeType === t.value"
        class="min-h-11 rounded-lg px-3 py-2 text-sm font-medium"
        :class="activeType === t.value ? 'bg-accent/10 text-accent' : 'text-ink-secondary hover:bg-hover'"
        @click="activeType = t.value"
      >
        {{ t.label }}
      </button>
    </div>

    <form
      v-if="createOpen"
      class="mb-4 max-w-2xl space-y-4 rounded-xl border border-border bg-surface p-4"
      novalidate
      @submit.prevent="create"
    >
      <h2 class="text-base font-semibold text-ink">New {{ codeToLabel(activeType) }} entry</h2>
      <InlineAlert v-if="createError" tone="error" :message="createError.message" :correlation-id="createError.correlationId" />
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField v-slot="{ inputId }" label="Name" required>
          <input :id="inputId" v-model="newName" type="text" required :class="inputClass" autocomplete="off" >
        </FormField>
        <FormField v-slot="{ inputId }" label="Code" required hint="Unique within this list; uppercase recommended.">
          <input :id="inputId" v-model="newCode" type="text" required class="font-mono" :class="inputClass" autocomplete="off" >
        </FormField>
      </div>
      <FormField v-slot="{ inputId }" label="Description">
        <input :id="inputId" v-model="newDescription" type="text" :class="inputClass" autocomplete="off" >
      </FormField>
      <div class="flex justify-end gap-2">
        <button
          type="button"
          class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
          @click="createOpen = false"
        >
          Cancel
        </button>
        <button
          type="submit"
          class="inline-flex min-h-11 items-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
          :disabled="creating"
        >
          {{ creating ? 'Creating…' : 'Create entry' }}
        </button>
      </div>
    </form>

    <LoadingSkeleton v-if="pending && !items.length" :lines="5" label="Loading entries…" />
    <InlineAlert
      v-else-if="error"
      tone="error"
      title="Entries could not be loaded"
      :message="error.message"
      :correlation-id="error.correlationId"
      retry-label="Retry"
      @retry="load()"
    />
    <EmptyState
      v-else-if="!items.length"
      icon="tag"
      title="No entries"
      message="Create the first entry for this list."
    />

    <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
      <table class="min-w-full divide-y divide-border text-sm">
        <caption class="sr-only">{{ codeToLabel(activeType) }} entries</caption>
        <thead class="bg-raised">
          <tr>
            <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Name</th>
            <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Code</th>
            <th scope="col" class="hidden px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted lg:table-cell">Description</th>
            <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Status</th>
            <th scope="col" class="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">
              <span class="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="item in items" :key="item.uuid" class="hover:bg-hover">
            <td class="px-3 py-3 font-medium text-ink">{{ item.name }}</td>
            <td class="whitespace-nowrap px-3 py-3 font-mono text-ink-secondary">{{ item.code || '—' }}</td>
            <td class="hidden max-w-64 px-3 py-3 lg:table-cell">
              <span class="block truncate text-ink-secondary">{{ item.description || '—' }}</span>
            </td>
            <td class="whitespace-nowrap px-3 py-3">
              <StatusBadge
                :label="item.active === false ? 'Inactive' : 'Active'"
                :code="item.active === false ? 'inactive' : 'active'"
                size="sm"
              />
            </td>
            <td class="whitespace-nowrap px-3 py-3 text-right">
              <template v-if="confirmDeactivate?.uuid === item.uuid">
                <span class="mr-2 text-xs text-warning">Deactivate "{{ item.name }}"? In-use rows are kept for history.</span>
                <button
                  type="button"
                  class="mr-1 inline-flex min-h-11 items-center rounded-lg border border-danger/50 bg-danger/10 px-3 py-1 text-sm font-medium text-danger hover:bg-danger/20 sm:min-h-0"
                  :disabled="busyUuid === item.uuid"
                  @click="deactivate(item)"
                >
                  Confirm
                </button>
                <button
                  type="button"
                  class="inline-flex min-h-11 items-center rounded-lg px-3 py-1 text-sm font-medium text-ink hover:bg-hover sm:min-h-0"
                  @click="confirmDeactivate = null"
                >
                  Cancel
                </button>
              </template>
              <template v-else>
                <button
                  v-if="item.active === false"
                  type="button"
                  class="inline-flex min-h-11 items-center rounded-lg px-3 py-1 text-sm font-medium text-accent hover:bg-hover disabled:opacity-60 sm:min-h-0"
                  :disabled="busyUuid === item.uuid"
                  @click="setActive(item, true)"
                >
                  Reactivate
                </button>
                <button
                  v-else
                  type="button"
                  class="inline-flex min-h-11 items-center rounded-lg px-3 py-1 text-sm font-medium text-danger hover:bg-hover disabled:opacity-60 sm:min-h-0"
                  :disabled="busyUuid === item.uuid"
                  @click="confirmDeactivate = item"
                >
                  Deactivate
                </button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
