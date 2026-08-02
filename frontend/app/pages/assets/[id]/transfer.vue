<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import EmptyState from '~/components/EmptyState.vue'

// Transfer flow (J-2, FR-008): From/To comparison, reason required.
definePageMeta({ title: 'Transfer asset' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const assets = useAssetsService()
const lifecycle = useLifecycleService()
const toast = useToast()
const { canManageAssets } = usePermissions()
const { departments, locations } = useReferenceData()

const { data: asset, pending, error: loadError, refresh } = await useAsyncData(
  `transfer-asset-${uuid.value}`,
  () => assets.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

useHead(() => ({ title: asset.value ? `Transfer ${asset.value.tag}` : 'Transfer asset' }))

const toCustodian = ref('')
const toDepartment = ref('')
const toLocation = ref('')
const reason = ref('')
const notes = ref('')

const submitting = ref(false)
const error = ref<ApiError | null>(null)
const errorRef = ref<HTMLElement | null>(null)

async function submit(): Promise<void> {
  error.value = null
  if (!reason.value.trim()) {
    error.value = new ApiError('Enter a reason for the transfer.', { status: 400 })
    await nextTick()
    errorRef.value?.focus()
    return
  }
  if (!toCustodian.value.trim() && !toDepartment.value && !toLocation.value) {
    error.value = new ApiError('Choose at least one destination: custodian, department, or location.', { status: 400 })
    await nextTick()
    errorRef.value?.focus()
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    await lifecycle.transfer(uuid.value, {
      to_custodian: toCustodian.value.trim() || undefined,
      to_department: toDepartment.value || undefined,
      to_location: toLocation.value || undefined,
      reason: reason.value.trim(),
      notes: notes.value.trim() || undefined,
    })
    toast.success(`Transfer started for ${asset.value?.tag ?? ''}`)
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
  <div class="max-w-4xl">
    <PageHeader title="Transfer asset" :description="asset ? `${asset.tag} · ${asset.name}` : ''">
      <template #breadcrumbs>
        <ol class="flex items-center gap-1">
          <li><NuxtLink to="/assets" class="rounded hover:text-ink">Assets</NuxtLink></li>
          <li aria-hidden="true">/</li>
          <li><NuxtLink :to="`/assets/${uuid}`" class="rounded hover:text-ink">{{ asset?.tag || 'Asset' }}</NuxtLink></li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" class="text-ink-secondary">Transfer</li>
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
      title="You cannot transfer assets"
      message="Your role does not include transfer operations."
    />

    <form v-else class="space-y-6" novalidate @submit.prevent="submit">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <section aria-labelledby="transfer-from" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
          <h2 id="transfer-from" class="text-sm font-semibold text-ink">From</h2>
          <dl class="mt-3 space-y-2 text-sm">
            <div class="flex justify-between gap-3">
              <dt class="text-muted">Custodian</dt>
              <dd class="text-ink">{{ asset?.custodian?.display_name || 'Unassigned' }}</dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-muted">Department</dt>
              <dd class="text-ink">{{ asset?.department?.name || '—' }}</dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-muted">Location</dt>
              <dd class="text-ink">{{ asset?.location?.name || '—' }}</dd>
            </div>
          </dl>
        </section>

        <fieldset aria-labelledby="transfer-to" class="space-y-4 rounded-xl border border-accent/40 bg-surface p-4 sm:p-6">
          <legend id="transfer-to" class="px-1 text-sm font-semibold text-ink">To</legend>
          <FormField v-slot="{ inputId }" label="New custodian username">
            <input :id="inputId" v-model="toCustodian" type="text" :class="inputClass" autocomplete="off" >
          </FormField>
          <FormField v-slot="{ inputId }" label="New department">
            <select :id="inputId" v-model="toDepartment" :class="inputClass">
              <option value="">Keep current</option>
              <option v-for="d in departments" :key="d.uuid" :value="d.uuid">{{ d.name }}</option>
            </select>
          </FormField>
          <FormField v-slot="{ inputId }" label="New location">
            <select :id="inputId" v-model="toLocation" :class="inputClass">
              <option value="">Keep current</option>
              <option v-for="l in locations" :key="l.uuid" :value="l.uuid">{{ l.name }}</option>
            </select>
          </FormField>
        </fieldset>
      </div>

      <div v-if="error" ref="errorRef" tabindex="-1">
        <InlineAlert tone="error" :message="error.message" :correlation-id="error.correlationId" />
      </div>

      <fieldset class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
        <legend class="px-1 text-sm font-semibold text-ink">Transfer details</legend>
        <FormField v-slot="{ inputId }" label="Reason for transfer" required>
          <textarea :id="inputId" v-model="reason" rows="3" required class="w-full rounded-lg border border-border bg-input px-3 py-2 text-sm text-ink focus:border-accent" />
        </FormField>
        <FormField v-slot="{ inputId }" label="Notes">
          <textarea :id="inputId" v-model="notes" rows="2" class="w-full rounded-lg border border-border bg-input px-3 py-2 text-sm text-ink focus:border-accent" />
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
          <AppIcon v-if="!submitting" name="refresh" size="sm" />
          {{ submitting ? 'Starting transfer…' : 'Start transfer' }}
        </button>
      </div>
    </form>
  </div>
</template>
