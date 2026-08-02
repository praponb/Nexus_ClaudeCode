<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDate } from '~/utils/format'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'

// Stocktake sessions (FR-022): list + create (Manager+), execution on the
// count page. Offline stocktake is out of scope (D-03).
definePageMeta({ title: 'Stocktakes' })
useHead({ title: 'Stocktakes' })

const service = useStocktakeService()
const toast = useToast()
const { hasRole } = usePermissions()
const { locations } = useReferenceData()

const canCreate = computed(() => hasRole('system_admin', 'asset_manager', 'department_manager'))

const { data, pending, error, refresh } = await useAsyncData(
  'stocktakes-list',
  () => service.list({ page_size: 50, ordering: '-created_at' }),
  { server: false },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const sessions = computed(() => data.value?.results ?? [])

/* Create form */
const createOpen = ref(false)
const name = ref('')
const selectedLocations = ref<string[]>([])
const startDate = ref('')
const dueDate = ref('')
const instructions = ref('')
const creating = ref(false)
const createError = ref<ApiError | null>(null)

async function create(): Promise<void> {
  createError.value = null
  if (!name.value.trim()) {
    createError.value = new ApiError('Name the stocktake session.', { status: 400 })
    return
  }
  if (creating.value) return
  creating.value = true
  try {
    const session = await service.create({
      name: name.value.trim(),
      location_uuids: selectedLocations.value,
      start_date: startDate.value || null,
      due_date: dueDate.value || null,
      instructions: instructions.value.trim() || undefined,
    })
    toast.success(`Stocktake “${session.name}” created`)
    await navigateTo(`/stocktakes/${session.uuid}`)
  } catch (e) {
    createError.value = ApiError.fromUnknown(e)
  } finally {
    creating.value = false
  }
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink placeholder:text-faint focus:border-accent'
</script>

<template>
  <div>
    <PageHeader title="Stocktakes" description="Physical count sessions and reconciliation.">
      <template #actions>
        <button
          v-if="canCreate"
          type="button"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
          @click="createOpen = !createOpen"
        >
          <AppIcon name="plus" size="sm" />
          New stocktake
        </button>
      </template>
    </PageHeader>

    <form
      v-if="createOpen && canCreate"
      class="mb-6 max-w-2xl space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6"
      novalidate
      @submit.prevent="create"
    >
      <h2 class="text-base font-semibold text-ink">New stocktake session</h2>
      <InlineAlert v-if="createError" tone="error" :message="createError.message" :correlation-id="createError.correlationId" />

      <FormField v-slot="{ inputId }" label="Session name" required>
        <input :id="inputId" v-model="name" type="text" required placeholder="Q3 office stocktake" :class="inputClass" autocomplete="off" >
      </FormField>

      <fieldset>
        <legend class="mb-1 text-sm font-medium text-ink-secondary">Locations in scope</legend>
        <div class="max-h-40 space-y-1 overflow-y-auto rounded-lg border border-border bg-input p-2">
          <label
            v-for="l in locations"
            :key="l.uuid"
            class="flex min-h-11 cursor-pointer items-center gap-2 rounded px-2 text-sm text-ink-secondary hover:bg-hover"
          >
            <input v-model="selectedLocations" type="checkbox" :value="l.uuid" class="h-4 w-4 accent-accent" >
            {{ l.name }}
          </label>
          <p v-if="!locations.length" class="px-2 py-1 text-sm text-muted">Loading locations…</p>
        </div>
        <p class="mt-1 text-xs text-muted">Leave all unchecked to include every location in your scope.</p>
      </fieldset>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField v-slot="{ inputId }" label="Start date">
          <input :id="inputId" v-model="startDate" type="date" :class="inputClass" >
        </FormField>
        <FormField v-slot="{ inputId }" label="Due date">
          <input :id="inputId" v-model="dueDate" type="date" :class="inputClass" >
        </FormField>
      </div>

      <FormField v-slot="{ inputId }" label="Instructions for operators">
        <textarea :id="inputId" v-model="instructions" rows="2" class="w-full rounded-lg border border-border bg-input px-3 py-2 text-sm text-ink focus:border-accent" />
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
          {{ creating ? 'Creating…' : 'Create stocktake' }}
        </button>
      </div>
    </form>

    <LoadingSkeleton v-if="pending && !sessions.length" :lines="3" label="Loading stocktakes…" />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Stocktakes could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <EmptyState
      v-else-if="!sessions.length"
      icon="check"
      title="No stocktake sessions"
      message="Create a session to start counting assets at your locations."
    />

    <ul v-else class="grid grid-cols-1 gap-3 md:grid-cols-2">
      <li v-for="session in sessions" :key="session.uuid">
        <NuxtLink
          :to="`/stocktakes/${session.uuid}`"
          class="block h-full rounded-xl border border-border bg-surface p-4 hover:border-border-strong hover:bg-hover"
        >
          <div class="flex items-center justify-between gap-2">
            <h2 class="truncate font-semibold text-ink">{{ session.name }}</h2>
            <StatusBadge :label="codeToLabel(session.status)" :code="session.status" size="sm" />
          </div>
          <p class="mt-1 text-sm text-muted">
            <span v-if="session.locations?.length">{{ session.locations.map((l) => l.name).join(', ') }}</span>
            <span v-else>All locations in scope</span>
          </p>
          <p class="mt-1 text-xs text-faint">
            <span v-if="session.start_date">Starts {{ formatDate(session.start_date) }}</span>
            <span v-if="session.due_date"> · Due {{ formatDate(session.due_date) }}</span>
          </p>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
