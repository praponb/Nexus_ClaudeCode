<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import EmptyState from '~/components/EmptyState.vue'

// Return / check-in flow (FR-009): condition, damage, destination.
definePageMeta({ title: 'Return asset' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const assets = useAssetsService()
const lifecycle = useLifecycleService()
const toast = useToast()
const { canManageAssets } = usePermissions()
const { conditions, locations } = useReferenceData()

const { data: asset, pending, error: loadError, refresh } = await useAsyncData(
  `return-asset-${uuid.value}`,
  () => assets.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

useHead(() => ({ title: asset.value ? `Return ${asset.value.tag}` : 'Return asset' }))

const condition = ref('')
const destination = ref('')
const damaged = ref(false)
const notes = ref('')

const submitting = ref(false)
const error = ref<ApiError | null>(null)
const errorRef = ref<HTMLElement | null>(null)

watch(asset, (a) => {
  if (a?.condition?.uuid && !condition.value) condition.value = a.condition.uuid
})

async function submit(): Promise<void> {
  error.value = null
  if (!condition.value) {
    error.value = new ApiError('Select the observed condition of the returned asset.', { status: 400 })
    await nextTick()
    errorRef.value?.focus()
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    await lifecycle.returnAsset(uuid.value, {
      condition: condition.value,
      destination_location: destination.value || undefined,
      damaged: damaged.value,
      notes: notes.value.trim() || undefined,
    })
    toast.success(`Asset ${asset.value?.tag ?? ''} checked in`)
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
    <PageHeader title="Return asset" :description="asset ? `${asset.tag} · ${asset.name}` : ''">
      <template #breadcrumbs>
        <ol class="flex items-center gap-1">
          <li><NuxtLink to="/assets" class="rounded hover:text-ink">Assets</NuxtLink></li>
          <li aria-hidden="true">/</li>
          <li><NuxtLink :to="`/assets/${uuid}`" class="rounded hover:text-ink">{{ asset?.tag || 'Asset' }}</NuxtLink></li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" class="text-ink-secondary">Return</li>
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
      title="You cannot process returns"
      message="Your role does not include return operations."
    />

    <form v-else class="space-y-6" novalidate @submit.prevent="submit">
      <div class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 class="text-sm font-semibold text-ink">Currently with</h2>
        <p class="mt-1 text-sm text-ink-secondary">
          {{ asset?.custodian?.display_name || 'Unassigned' }}
          <span v-if="asset?.location" class="text-muted"> · {{ asset.location.name }}</span>
        </p>
      </div>

      <div v-if="error" ref="errorRef" tabindex="-1">
        <InlineAlert tone="error" :message="error.message" :correlation-id="error.correlationId" />
      </div>

      <fieldset class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
        <legend class="px-1 text-sm font-semibold text-ink">Return details</legend>
        <FormField v-slot="{ inputId }" label="Observed condition" required>
          <select :id="inputId" v-model="condition" required :class="inputClass">
            <option value="" disabled>Select a condition</option>
            <option v-for="c in conditions" :key="c.uuid" :value="c.uuid">{{ c.label }}</option>
          </select>
        </FormField>
        <FormField v-slot="{ inputId }" label="Return destination">
          <select :id="inputId" v-model="destination" :class="inputClass">
            <option value="">Default storage location</option>
            <option v-for="l in locations" :key="l.uuid" :value="l.uuid">{{ l.name }}</option>
          </select>
        </FormField>
        <label class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-ink-secondary">
          <input v-model="damaged" type="checkbox" class="h-4 w-4 accent-accent" >
          Damage or missing accessories observed
        </label>
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
          <AppIcon v-if="!submitting" name="back" size="sm" />
          {{ submitting ? 'Processing return…' : 'Confirm return' }}
        </button>
      </div>
    </form>
  </div>
</template>
