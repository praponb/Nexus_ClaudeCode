<script setup lang="ts">
import type { AssetDetail, AssetWritePayload, DuplicateCandidate } from '~/types/api'
import { ApiError, isVersionConflict } from '~/utils/errors'
import { newCorrelationId } from '~/utils/correlation'
import AppIcon from '~/components/AppIcon.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import ConfirmDialog from '~/components/ConfirmDialog.vue'
import AssetDuplicatePanel from '~/components/asset/AssetDuplicatePanel.vue'

const props = withDefaults(
  defineProps<{
    mode: 'create' | 'edit'
    initial?: AssetDetail | null
  }>(),
  { initial: null },
)

const emit = defineEmits<{
  (e: 'saved', asset: AssetDetail): void
  (e: 'reload'): void
}>()

const service = useAssetsService()
const toast = useToast()
const router = useRouter()
const { canViewFinance } = usePermissions()
const { categories, statuses, conditions, departments, locations } = useReferenceData()

interface FormState {
  tag: string
  name: string
  category: string
  status: string
  condition: string
  department: string
  location: string
  serial_number: string
  manufacturer: string
  model: string
  description: string
  acquisition_type: string
  purchase_date: string
  purchase_price_amount: string
  purchase_currency: string
  warranty_start: string
  warranty_end: string
}

function blankForm(): FormState {
  return {
    tag: '',
    name: '',
    category: '',
    status: '',
    condition: '',
    department: '',
    location: '',
    serial_number: '',
    manufacturer: '',
    model: '',
    description: '',
    acquisition_type: '',
    purchase_date: '',
    purchase_price_amount: '',
    purchase_currency: 'USD',
    warranty_start: '',
    warranty_end: '',
  }
}

function formFromAsset(asset: AssetDetail): FormState {
  return {
    tag: asset.tag ?? '',
    name: asset.name ?? '',
    category: asset.category?.uuid ?? '',
    status: asset.status?.uuid ?? '',
    condition: asset.condition?.uuid ?? '',
    department: asset.department?.uuid ?? '',
    location: asset.location?.uuid ?? '',
    serial_number: asset.serial_number ?? '',
    manufacturer: asset.manufacturer ?? '',
    model: asset.model ?? '',
    description: asset.description ?? '',
    acquisition_type: asset.acquisition_type ?? '',
    purchase_date: asset.purchase_date ?? '',
    purchase_price_amount: asset.purchase_price?.amount ?? '',
    purchase_currency: asset.purchase_price?.currency ?? 'USD',
    warranty_start: asset.warranty_start ?? '',
    warranty_end: asset.warranty_end ?? '',
  }
}

const form = reactive<FormState>(blankForm())
const snapshot = ref(JSON.stringify(blankForm()))

// Category-specific dynamic fields (design §9.4), keyed by
// CategoryAttributeDefinition.key. Reset whenever the category changes
// since a different category has a different attribute schema.
const categoryAttributes = ref<Record<string, string | boolean>>({})

watch(
  () => props.initial,
  (asset) => {
    if (asset) {
      Object.assign(form, formFromAsset(asset))
      snapshot.value = JSON.stringify(formFromAsset(asset))
      const next: Record<string, string | boolean> = {}
      for (const [key, value] of Object.entries(asset.category_attributes ?? {})) {
        next[key] = typeof value === 'boolean' ? value : String(value ?? '')
      }
      categoryAttributes.value = next
    }
  },
  { immediate: true },
)

const selectedCategoryAttributeDefs = computed(
  () => categories.value.find((c) => c.uuid === form.category)?.attribute_definitions ?? [],
)

watch(
  () => form.category,
  () => {
    // Selecting a different category invalidates any values entered for
    // the previous category's attribute schema.
    categoryAttributes.value = {}
  },
)

const isDirty = computed(() => JSON.stringify(form) !== snapshot.value)

const errors = ref<Record<string, string>>({})
const summaryError = ref<ApiError | null>(null)
const conflict = ref<ApiError | null>(null)
const submitting = ref(false)
const summaryRef = ref<HTMLElement | null>(null)

const duplicateWarnings = ref<string[]>([])
const duplicateCandidates = ref<DuplicateCandidate[]>([])
const duplicatesAcknowledged = ref(false)
const duplicatePanelRef = ref<HTMLElement | null>(null)

// A stable idempotency key per editing session makes safe retries harmless (D-08).
const idempotencyKey = ref(newCorrelationId())

watch(
  () => [form.serial_number, form.manufacturer, form.model],
  () => {
    duplicatesAcknowledged.value = false
    duplicateWarnings.value = []
    duplicateCandidates.value = []
  },
)

function validate(): boolean {
  const next: Record<string, string> = {}
  if (!form.name.trim()) next.name = 'Enter an asset name.'
  if (!form.category) next.category = 'Select a category.'
  if (form.purchase_price_amount && !/^\d+(\.\d{1,2})?$/.test(form.purchase_price_amount)) {
    next.purchase_price_amount = 'Enter a valid amount, for example 1299.99.'
  }
  if (form.warranty_start && form.warranty_end && form.warranty_end < form.warranty_start) {
    next.warranty_end = 'Warranty end must be on or after the start date.'
  }
  errors.value = next
  return Object.keys(next).length === 0
}

function buildCategoryAttributesPayload(): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const def of selectedCategoryAttributeDefs.value) {
    const raw = categoryAttributes.value[def.key]
    if (raw === undefined || raw === '') continue
    if (def.field_type === 'number' || def.field_type === 'decimal' || def.field_type === 'currency') {
      const num = Number(raw)
      if (!Number.isNaN(num)) result[def.key] = num
    } else if (def.field_type === 'bool') {
      result[def.key] = Boolean(raw)
    } else {
      result[def.key] = raw
    }
  }
  return result
}

function buildPayload(): AssetWritePayload {
  const payload: AssetWritePayload = {
    name: form.name.trim(),
    category: form.category,
  }
  if (props.mode === 'create' && form.tag.trim()) payload.tag = form.tag.trim()
  if (form.status) payload.status = form.status
  if (form.condition) payload.condition = form.condition
  if (form.department) payload.department = form.department
  if (form.location) payload.location = form.location
  if (form.serial_number.trim()) payload.serial_number = form.serial_number.trim()
  if (form.manufacturer.trim()) payload.manufacturer = form.manufacturer.trim()
  if (form.model.trim()) payload.model = form.model.trim()
  if (form.description.trim()) payload.description = form.description.trim()
  if (form.acquisition_type.trim()) payload.acquisition_type = form.acquisition_type.trim()
  if (selectedCategoryAttributeDefs.value.length) {
    payload.category_attributes = buildCategoryAttributesPayload()
  }
  if (canViewFinance.value) {
    if (form.purchase_date) payload.purchase_date = form.purchase_date
    if (form.purchase_price_amount) {
      payload.purchase_price = {
        amount: form.purchase_price_amount,
        currency: form.purchase_currency || 'USD',
      }
    }
  }
  if (form.warranty_start) payload.warranty_start = form.warranty_start
  if (form.warranty_end) payload.warranty_end = form.warranty_end
  return payload
}

/** Non-blocking duplicate pre-check (design FR-003); server re-checks on save. */
async function duplicatesClear(): Promise<boolean> {
  try {
    const res = await service.checkDuplicates(
      {
        name: form.name.trim(),
        serial_number: form.serial_number.trim(),
        manufacturer: form.manufacturer.trim(),
        model: form.model.trim(),
        category: form.category,
      },
      props.mode === 'edit' ? props.initial?.uuid : undefined,
    )
    duplicateWarnings.value = res.warnings ?? []
    duplicateCandidates.value = res.candidates ?? []
    if (duplicateWarnings.value.length || duplicateCandidates.value.length) {
      duplicatesAcknowledged.value = true
      await nextTick()
      duplicatePanelRef.value?.focus()
      return false
    }
  } catch {
    // Pre-check unavailable — proceed; the save endpoint remains authoritative.
  }
  return true
}

function applyServerErrors(error: ApiError): void {
  const fieldErrors: Record<string, string> = {}
  for (const [field, messages] of Object.entries(error.fieldErrors)) {
    if (messages.length) fieldErrors[field] = messages[0]!
  }
  errors.value = { ...errors.value, ...fieldErrors }
  summaryError.value = error
}

async function onSubmit(): Promise<void> {
  summaryError.value = null
  conflict.value = null
  if (!validate()) {
    await nextTick()
    summaryRef.value?.focus()
    return
  }
  if (props.mode === 'create' && !duplicatesAcknowledged.value) {
    const clear = await duplicatesClear()
    if (!clear) return
  }

  submitting.value = true
  try {
    const payload = buildPayload()
    if (props.mode === 'create') {
      const { asset: saved, warnings } = await service.create(payload, idempotencyKey.value)
      snapshot.value = JSON.stringify(form)
      idempotencyKey.value = newCorrelationId()
      if (warnings.length) {
        toast.info(`Asset ${saved.tag} saved with warnings`, warnings[0])
      } else {
        toast.success(`Asset ${saved.tag} registered`)
      }
      emit('saved', saved)
    } else {
      const saved = await service.update(props.initial!.uuid, payload, props.initial!.version)
      snapshot.value = JSON.stringify(form)
      idempotencyKey.value = newCorrelationId()
      toast.success('Asset updated')
      emit('saved', saved)
    }
  } catch (e) {
    const error = e instanceof ApiError ? e : ApiError.fromUnknown(e)
    if (isVersionConflict(error)) {
      conflict.value = error
    } else {
      applyServerErrors(error)
    }
    await nextTick()
    summaryRef.value?.focus()
  } finally {
    submitting.value = false
  }
}

/* --- Unsaved-changes guard (layout.md §13.2) --- */
const leaveDialogOpen = ref(false)
const allowLeave = ref(false)
let pendingNavigation: string | null = null

onBeforeRouteLeave((to) => {
  if (allowLeave.value || !isDirty.value || submitting.value) return true
  pendingNavigation = to.fullPath
  leaveDialogOpen.value = true
  return false
})

function confirmLeave(): void {
  leaveDialogOpen.value = false
  allowLeave.value = true
  if (pendingNavigation) void router.push(pendingNavigation)
}

function onBeforeUnload(event: BeforeUnloadEvent): void {
  if (isDirty.value) event.preventDefault()
}

onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))

const inputClass =
  'h-11 w-full rounded-lg border bg-input px-3 text-sm text-ink placeholder:text-faint focus:border-accent sm:h-10'

function fieldClass(hasError: boolean): string {
  return `${inputClass} ${hasError ? 'border-danger' : 'border-border'}`
}

const submitLabel = computed(() => {
  if (submitting.value) return props.mode === 'create' ? 'Saving…' : 'Saving changes…'
  if (props.mode === 'create') return duplicatesAcknowledged.value ? 'Save asset anyway' : 'Save asset'
  return 'Save changes'
})

const errorSummaryList = computed(() => Object.entries(errors.value).filter(([, msg]) => Boolean(msg)))

/** "category_attributes.ram_gb" -> "Category attributes → ram gb". */
function formatFieldName(field: string): string {
  return field
    .split('.')
    .map((part) => part.replace(/_/g, ' '))
    .join(' → ')
}
</script>

<template>
  <form novalidate class="max-w-3xl space-y-6" @submit.prevent="onSubmit">
    <p class="text-sm text-muted">
      Fields marked <span class="text-danger" aria-hidden="true">*</span> are required.
    </p>

    <div
      v-if="errorSummaryList.length || summaryError || conflict"
      ref="summaryRef"
      tabindex="-1"
      role="alert"
      class="space-y-3 rounded-lg border border-danger/40 bg-danger/5 p-4"
    >
      <template v-if="conflict">
        <InlineAlert
          tone="warning"
          title="This asset was changed by someone else"
          :message="conflict.message || 'Reload the latest version before saving your changes again.'"
          :correlation-id="conflict.correlationId"
        />
        <button
          type="button"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-raised px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
          @click="emit('reload')"
        >
          <AppIcon name="refresh" size="sm" />
          Reload latest data
        </button>
      </template>
      <template v-else>
        <p class="font-semibold text-ink">
          {{ summaryError ? summaryError.message : 'Check the highlighted fields and try again.' }}
        </p>
        <p v-if="summaryError?.correlationId" class="font-mono text-xs text-muted">
          Support reference: {{ summaryError.correlationId }}
        </p>
        <ul v-if="errorSummaryList.length" class="list-inside list-disc text-sm text-ink-secondary">
          <li v-for="[field, message] in errorSummaryList" :key="field">
            <span class="capitalize">{{ formatFieldName(field) }}</span>: {{ message }}
          </li>
        </ul>
      </template>
    </div>

    <div
      v-if="duplicateWarnings.length || duplicateCandidates.length"
      ref="duplicatePanelRef"
      tabindex="-1"
    >
      <AssetDuplicatePanel :warnings="duplicateWarnings" :candidates="duplicateCandidates" />
      <p class="mt-2 text-sm text-muted">
        If none of these are the same physical asset, choose “Save asset anyway” to continue.
      </p>
    </div>

    <fieldset class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
      <legend class="px-1 text-sm font-semibold text-ink">Identity</legend>

      <FormField
        v-if="mode === 'create'"
        v-slot="{ inputId, describedBy }"
        label="Asset tag"
        hint="Leave blank to have a tag generated automatically."
      >
        <input
          :id="inputId"
          v-model="form.tag"
          type="text"
          :aria-describedby="describedBy"
          class="font-mono"
          :class="fieldClass(false)"
          autocomplete="off"
        >
      </FormField>

      <FormField v-slot="{ inputId, describedBy }" label="Asset name" required :error="errors.name">
        <input
          :id="inputId"
          v-model="form.name"
          type="text"
          required
          :aria-invalid="Boolean(errors.name)"
          :aria-describedby="describedBy"
          :class="fieldClass(Boolean(errors.name))"
          autocomplete="off"
        >
      </FormField>

      <FormField v-slot="{ inputId, describedBy }" label="Category" required :error="errors.category">
        <select
          :id="inputId"
          v-model="form.category"
          required
          :aria-invalid="Boolean(errors.category)"
          :aria-describedby="describedBy"
          :class="fieldClass(Boolean(errors.category))"
        >
          <option value="" disabled>Select a category</option>
          <option v-for="c in categories" :key="c.uuid" :value="c.uuid">{{ c.name }}</option>
        </select>
      </FormField>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField v-slot="{ inputId, describedBy }" label="Serial number" :error="errors.serial_number">
          <input
            :id="inputId"
            v-model="form.serial_number"
            type="text"
            :aria-invalid="Boolean(errors.serial_number)"
            :aria-describedby="describedBy"
            class="font-mono"
            :class="fieldClass(Boolean(errors.serial_number))"
            autocomplete="off"
          >
        </FormField>
        <FormField v-slot="{ inputId }" label="Manufacturer">
          <input :id="inputId" v-model="form.manufacturer" type="text" :class="fieldClass(false)" autocomplete="off" >
        </FormField>
      </div>

      <FormField v-slot="{ inputId }" label="Model">
        <input :id="inputId" v-model="form.model" type="text" :class="fieldClass(false)" autocomplete="off" >
      </FormField>
    </fieldset>

    <fieldset
      v-if="selectedCategoryAttributeDefs.length"
      class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6"
    >
      <legend class="px-1 text-sm font-semibold text-ink">Category attributes</legend>
      <FormField
        v-for="def in selectedCategoryAttributeDefs"
        :key="def.key"
        v-slot="{ inputId, describedBy }"
        :label="def.label"
        :required="def.required"
        :error="errors[`category_attributes.${def.key}`]"
      >
        <select
          v-if="def.field_type === 'choice'"
          :id="inputId"
          v-model="categoryAttributes[def.key]"
          :aria-describedby="describedBy"
          :class="fieldClass(Boolean(errors[`category_attributes.${def.key}`]))"
        >
          <option value="">Select {{ def.label.toLowerCase() }}</option>
          <option v-for="opt in def.options" :key="opt" :value="opt">{{ opt }}</option>
        </select>
        <label
          v-else-if="def.field_type === 'bool'"
          class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-ink-secondary"
        >
          <input :id="inputId" v-model="categoryAttributes[def.key]" type="checkbox" class="h-4 w-4 accent-accent" >
          {{ def.label }}
        </label>
        <textarea
          v-else-if="def.field_type === 'longtext'"
          :id="inputId"
          v-model="categoryAttributes[def.key]"
          rows="3"
          :aria-describedby="describedBy"
          :class="fieldClass(Boolean(errors[`category_attributes.${def.key}`]))"
        />
        <input
          v-else
          :id="inputId"
          v-model="categoryAttributes[def.key]"
          :type="
            def.field_type === 'number' || def.field_type === 'decimal' || def.field_type === 'currency'
              ? 'number'
              : def.field_type === 'date'
                ? 'date'
                : def.field_type === 'datetime'
                  ? 'datetime-local'
                  : 'text'
          "
          :step="def.field_type === 'decimal' || def.field_type === 'currency' ? '0.01' : undefined"
          :aria-describedby="describedBy"
          :aria-invalid="Boolean(errors[`category_attributes.${def.key}`])"
          :class="fieldClass(Boolean(errors[`category_attributes.${def.key}`]))"
          autocomplete="off"
        >
      </FormField>
    </fieldset>

    <fieldset class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
      <legend class="px-1 text-sm font-semibold text-ink">Status and placement</legend>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField v-slot="{ inputId }" label="Status">
          <select :id="inputId" v-model="form.status" :class="fieldClass(false)">
            <option value="">Select a status</option>
            <option v-for="s in statuses" :key="s.uuid" :value="s.uuid">{{ s.label }}</option>
          </select>
        </FormField>
        <FormField v-slot="{ inputId }" label="Condition">
          <select :id="inputId" v-model="form.condition" :class="fieldClass(false)">
            <option value="">Select a condition</option>
            <option v-for="c in conditions" :key="c.uuid" :value="c.uuid">{{ c.label }}</option>
          </select>
        </FormField>
        <FormField v-slot="{ inputId }" label="Department">
          <select :id="inputId" v-model="form.department" :class="fieldClass(false)">
            <option value="">Select a department</option>
            <option v-for="d in departments" :key="d.uuid" :value="d.uuid">{{ d.name }}</option>
          </select>
        </FormField>
        <FormField v-slot="{ inputId }" label="Location">
          <select :id="inputId" v-model="form.location" :class="fieldClass(false)">
            <option value="">Select a location</option>
            <option v-for="l in locations" :key="l.uuid" :value="l.uuid">{{ l.name }}</option>
          </select>
        </FormField>
        <FormField
          v-slot="{ inputId, describedBy }"
          label="Acquisition type"
          hint="For example: purchased, leased, donated. Required unless saving as Draft."
          :error="errors.acquisition_type"
        >
          <input
            :id="inputId"
            v-model="form.acquisition_type"
            type="text"
            :aria-invalid="Boolean(errors.acquisition_type)"
            :aria-describedby="describedBy"
            :class="fieldClass(Boolean(errors.acquisition_type))"
            autocomplete="off"
          >
        </FormField>
      </div>
    </fieldset>

    <fieldset class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
      <legend class="px-1 text-sm font-semibold text-ink">Details</legend>
      <FormField v-slot="{ inputId }" label="Description">
        <textarea :id="inputId" v-model="form.description" rows="4" :class="fieldClass(false)" />
      </FormField>
    </fieldset>

    <fieldset v-if="canViewFinance" class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6">
      <legend class="px-1 text-sm font-semibold text-ink">Financial and warranty</legend>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField v-slot="{ inputId }" label="Purchase date">
          <input :id="inputId" v-model="form.purchase_date" type="date" :class="fieldClass(false)" >
        </FormField>
        <FormField
          v-slot="{ inputId, describedBy }"
          label="Purchase price"
          :error="errors.purchase_price_amount"
          hint="Amount plus ISO currency, for example 1299.99 USD."
        >
          <div class="flex gap-2">
            <input
              :id="inputId"
              v-model="form.purchase_price_amount"
              type="text"
              inputmode="decimal"
              :aria-invalid="Boolean(errors.purchase_price_amount)"
              :aria-describedby="describedBy"
              :class="fieldClass(Boolean(errors.purchase_price_amount))"
              autocomplete="off"
            >
            <label :for="`${inputId}-currency`" class="sr-only">Currency</label>
            <input
              :id="`${inputId}-currency`"
              v-model="form.purchase_currency"
              type="text"
              maxlength="3"
              class="w-20 rounded-lg border border-border bg-input px-2 font-mono text-sm uppercase text-ink"
              autocomplete="off"
            >
          </div>
        </FormField>
        <FormField v-slot="{ inputId }" label="Warranty start">
          <input :id="inputId" v-model="form.warranty_start" type="date" :class="fieldClass(false)" >
        </FormField>
        <FormField v-slot="{ inputId, describedBy }" label="Warranty end" :error="errors.warranty_end">
          <input
            :id="inputId"
            v-model="form.warranty_end"
            type="date"
            :aria-invalid="Boolean(errors.warranty_end)"
            :aria-describedby="describedBy"
            :class="fieldClass(Boolean(errors.warranty_end))"
          >
        </FormField>
      </div>
    </fieldset>

    <div class="no-print sticky bottom-16 z-10 flex flex-col-reverse gap-2 rounded-xl border border-border bg-raised p-3 sm:static sm:flex-row sm:justify-end sm:border-0 sm:bg-transparent sm:p-0 lg:bottom-0">
      <NuxtLink
        :to="mode === 'edit' && initial ? `/assets/${initial.uuid}` : '/assets'"
        class="inline-flex min-h-11 items-center justify-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
      >
        Cancel
      </NuxtLink>
      <button
        type="submit"
        class="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="submitting"
      >
        {{ submitLabel }}
      </button>
    </div>

    <ConfirmDialog
      :open="leaveDialogOpen"
      title="Discard unsaved changes?"
      message="You have unsaved changes on this form. If you leave now, those changes will be lost."
      confirm-label="Discard changes"
      cancel-label="Keep editing"
      tone="danger"
      @confirm="confirmLeave"
      @cancel="leaveDialogOpen = false"
    />
  </form>
</template>
