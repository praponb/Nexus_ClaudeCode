<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import EmptyState from '~/components/EmptyState.vue'

// Assignment flow (J-1 completion, FR-007). Success is only shown after the
// backend confirms (design §14.6); Idempotency-Key handled by the service.
definePageMeta({ title: 'Assign asset' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const assets = useAssetsService()
const lifecycle = useLifecycleService()
const toast = useToast()
const { canManageAssets } = usePermissions()
const { departments, locations } = useReferenceData()

const { data: asset, pending, error: loadError, refresh } = await useAsyncData(
  `assign-asset-${uuid.value}`,
  () => assets.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

useHead(() => ({ title: asset.value ? `Assign ${asset.value.tag}` : 'Assign asset' }))

type TargetKind = 'person' | 'department' | 'location'
const targetKind = ref<TargetKind>('person')
const custodian = ref('')
const department = ref('')
const location = ref('')
const expectedReturn = ref('')
const notes = ref('')
const requireAck = ref(false)

const submitting = ref(false)
const error = ref<ApiError | null>(null)
const errorRef = ref<HTMLElement | null>(null)

function validate(): boolean {
  if (targetKind.value === 'person' && !custodian.value.trim()) {
    error.value = new ApiError('Enter the username of the person receiving the asset.', { status: 400 })
    return false
  }
  if (targetKind.value === 'department' && !department.value) {
    error.value = new ApiError('Select a department.', { status: 400 })
    return false
  }
  if (targetKind.value === 'location' && !location.value) {
    error.value = new ApiError('Select a location.', { status: 400 })
    return false
  }
  return true
}

async function submit(): Promise<void> {
  error.value = null
  if (!validate() || submitting.value) {
    await nextTick()
    errorRef.value?.focus()
    return
  }
  submitting.value = true
  try {
    await lifecycle.assign(uuid.value, {
      custodian: targetKind.value === 'person' ? custodian.value.trim() : undefined,
      department: targetKind.value === 'department' ? department.value : undefined,
      location: targetKind.value === 'location' ? location.value : undefined,
      expected_return_at: expectedReturn.value || null,
      notes: notes.value.trim() || undefined,
      requires_acknowledgement: requireAck.value,
    })
    toast.success(`Asset ${asset.value?.tag ?? ''} assigned`)
    await navigateTo(`/assets/${uuid.value}`)
  } catch (e) {
    error.value = ApiError.fromUnknown(e)
    await nextTick()
    errorRef.value?.focus()
  } finally {
    submitting.value = false
  }
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink placeholder:text-faint focus:border-accent'
const loadApiError = computed(() => (loadError.value ? ApiError.fromUnknown(loadError.value) : null))
</script>

<template>
  <div class="max-w-3xl">
    <PageHeader title="Assign asset" :description="asset ? `${asset.tag} · ${asset.name}` : ''">
      <template #breadcrumbs>
        <ol class="flex items-center gap-1">
          <li><NuxtLink to="/assets" class="rounded hover:text-ink">Assets</NuxtLink></li>
          <li aria-hidden="true">/</li>
          <li><NuxtLink :to="`/assets/${uuid}`" class="rounded hover:text-ink">{{ asset?.tag || 'Asset' }}</NuxtLink></li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" class="text-ink-secondary">Assign</li>
        </ol>
      </template>
    </PageHeader>

    <LoadingSkeleton v-if="pending && !asset" :lines="4" label="Loading asset…" />
    <EmptyState
      v-else-if="loadApiError && loadApiError.status === 404"
      icon="search"
      title="Asset not found"
      message="This asset does not exist or is outside your organizational scope."
      action-to="/assets"
      action-label="Back to asset register"
    />
    <InlineAlert
      v-else-if="loadApiError"
      tone="error"
      title="Asset could not be loaded"
      :message="loadApiError.message"
      :correlation-id="loadApiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <InlineAlert
      v-else-if="!canManageAssets"
      tone="warning"
      title="You cannot assign assets"
      message="Your role does not include assignment operations."
    />

    <form v-else class="space-y-6" novalidate @submit.prevent="submit">
      <div class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 class="text-sm font-semibold text-ink">Current state</h2>
        <dl class="mt-2 grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
          <div>
            <dt class="text-muted">Status</dt>
            <dd class="text-ink">{{ asset?.status?.label || '—' }}</dd>
          </div>
          <div>
            <dt class="text-muted">Custodian</dt>
            <dd class="text-ink">{{ asset?.custodian?.display_name || 'Unassigned' }}</dd>
          </div>
          <div>
            <dt class="text-muted">Location</dt>
            <dd class="text-ink">{{ asset?.location?.name || '—' }}</dd>
          </div>
        </dl>
      </div>

      <div v-if="error" ref="errorRef" tabindex="-1">
        <InlineAlert tone="error" :message="error.message" :correlation-id="error.correlationId" />
      </div>

      <fieldset class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
        <legend class="px-1 text-sm font-semibold text-ink">Assign to</legend>
        <div role="radiogroup" aria-label="Assignment target" class="flex flex-wrap gap-2">
          <label
            v-for="option in [
              { value: 'person', label: 'A person' },
              { value: 'department', label: 'A department' },
              { value: 'location', label: 'A location' },
            ]"
            :key="option.value"
            class="flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm"
            :class="targetKind === option.value ? 'border-accent bg-accent/10 text-ink' : 'border-border bg-input text-ink-secondary'"
          >
            <input v-model="targetKind" type="radio" name="assign-target" :value="option.value" class="accent-accent" >
            {{ option.label }}
          </label>
        </div>

        <FormField
          v-if="targetKind === 'person'"
          v-slot="{ inputId, describedBy }"
          label="Custodian username"
          required
          hint="The person's sign-in username. Any active assignment is closed automatically."
        >
          <input :id="inputId" v-model="custodian" type="text" :aria-describedby="describedBy" :class="inputClass" autocomplete="off" >
        </FormField>
        <FormField v-else-if="targetKind === 'department'" v-slot="{ inputId }" label="Department" required>
          <select :id="inputId" v-model="department" :class="inputClass">
            <option value="" disabled>Select a department</option>
            <option v-for="d in departments" :key="d.uuid" :value="d.uuid">{{ d.name }}</option>
          </select>
        </FormField>
        <FormField v-else v-slot="{ inputId }" label="Location" required>
          <select :id="inputId" v-model="location" :class="inputClass">
            <option value="" disabled>Select a location</option>
            <option v-for="l in locations" :key="l.uuid" :value="l.uuid">{{ l.name }}</option>
          </select>
        </FormField>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField v-slot="{ inputId }" label="Expected return date">
            <input :id="inputId" v-model="expectedReturn" type="date" :class="inputClass" >
          </FormField>
          <div class="flex items-end pb-1">
            <label class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-ink-secondary">
              <input v-model="requireAck" type="checkbox" class="h-4 w-4 accent-accent" >
              Require receipt acknowledgement
            </label>
          </div>
        </div>

        <FormField v-slot="{ inputId }" label="Notes">
          <textarea :id="inputId" v-model="notes" rows="3" class="w-full rounded-lg border border-border bg-input px-3 py-2 text-sm text-ink focus:border-accent" />
        </FormField>
      </fieldset>

      <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <NuxtLink
          :to="`/assets/${uuid}`"
          class="inline-flex min-h-11 items-center justify-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
        >
          Cancel
        </NuxtLink>
        <button
          type="submit"
          class="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
          :disabled="submitting"
        >
          <AppIcon v-if="!submitting" name="user-circle" size="sm" />
          {{ submitting ? 'Assigning…' : 'Assign asset' }}
        </button>
      </div>
    </form>
  </div>
</template>
