<script setup lang="ts">
import type { NamedRef } from '~/types/api'
import { unwrapList } from '~/types/api'
import { ApiError } from '~/utils/errors'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'

const props = defineProps<{ assetUuid: string }>()
const emit = defineEmits<{ (e: 'created'): void }>()

const service = useMaintenanceService()
const api = useApi()
const toast = useToast()
const { canViewFinance } = usePermissions()

const types = ref<NamedRef[]>([])
onMounted(async () => {
  try {
    types.value = unwrapList<NamedRef>(await api.get<unknown>('/reference-data/maintenance-types/'))
  } catch {
    types.value = [] // Type becomes a free-text field when not configured.
  }
})

const type = ref('')
const typeText = ref('')
const issue = ref('')
const provider = ref('')
const startedAt = ref(new Date().toISOString().slice(0, 10))
const costAmount = ref('')
const costCurrency = ref('USD')
const nextDue = ref('')

const submitting = ref(false)
const error = ref<ApiError | null>(null)

async function submit(): Promise<void> {
  error.value = null
  if (!issue.value.trim()) {
    error.value = new ApiError('Describe the issue or work required.', { status: 400 })
    return
  }
  if (costAmount.value && !/^\d+(\.\d{1,2})?$/.test(costAmount.value)) {
    error.value = new ApiError('Enter a valid cost amount, for example 149.00.', { status: 400 })
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    await service.create({
      asset: props.assetUuid,
      type: types.value.length ? type.value || undefined : typeText.value.trim() || undefined,
      issue: issue.value.trim(),
      provider: provider.value.trim() || undefined,
      started_at: startedAt.value || null,
      cost: costAmount.value ? { amount: costAmount.value, currency: costCurrency.value || 'USD' } : null,
      next_due: nextDue.value || null,
    })
    toast.success('Maintenance record created')
    issue.value = ''
    provider.value = ''
    costAmount.value = ''
    nextDue.value = ''
    emit('created')
  } catch (e) {
    error.value = ApiError.fromUnknown(e)
  } finally {
    submitting.value = false
  }
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink placeholder:text-faint focus:border-accent'
</script>

<template>
  <form class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6" novalidate @submit.prevent="submit">
    <h2 class="text-base font-semibold text-ink">New maintenance record</h2>

    <InlineAlert v-if="error" tone="error" :message="error.message" :correlation-id="error.correlationId" />

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <FormField v-if="types.length" v-slot="{ inputId }" label="Maintenance type">
        <select :id="inputId" v-model="type" :class="inputClass">
          <option value="">Select a type</option>
          <option v-for="t in types" :key="t.uuid" :value="t.uuid">{{ t.name }}</option>
        </select>
      </FormField>
      <FormField v-else v-slot="{ inputId }" label="Maintenance type">
        <input :id="inputId" v-model="typeText" type="text" placeholder="Repair, inspection, upgrade…" :class="inputClass" autocomplete="off" >
      </FormField>
      <FormField v-slot="{ inputId }" label="Provider / technician">
        <input :id="inputId" v-model="provider" type="text" :class="inputClass" autocomplete="off" >
      </FormField>
    </div>

    <FormField v-slot="{ inputId }" label="Issue / work required" required>
      <textarea :id="inputId" v-model="issue" rows="3" required class="w-full rounded-lg border border-border bg-input px-3 py-2 text-sm text-ink focus:border-accent" />
    </FormField>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <FormField v-slot="{ inputId }" label="Started">
        <input :id="inputId" v-model="startedAt" type="date" :class="inputClass" >
      </FormField>
      <FormField v-if="canViewFinance" v-slot="{ inputId }" label="Cost">
        <div class="flex gap-2">
          <input :id="inputId" v-model="costAmount" type="text" inputmode="decimal" placeholder="0.00" :class="inputClass" autocomplete="off" >
          <label :for="`${inputId}-currency`" class="sr-only">Currency</label>
          <input
            :id="`${inputId}-currency`"
            v-model="costCurrency"
            type="text"
            maxlength="3"
            class="w-20 rounded-lg border border-border bg-input px-2 font-mono text-sm uppercase text-ink"
            autocomplete="off"
          >
        </div>
      </FormField>
      <FormField v-slot="{ inputId }" label="Next due">
        <input :id="inputId" v-model="nextDue" type="date" :class="inputClass" >
      </FormField>
    </div>

    <div class="flex justify-end">
      <button
        type="submit"
        class="inline-flex min-h-11 items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
        :disabled="submitting"
      >
        {{ submitting ? 'Creating…' : 'Create maintenance record' }}
      </button>
    </div>
  </form>
</template>
