<script setup lang="ts">
import { ApiError, isNotFoundError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import type { StocktakeObservation } from '~/types/workflow'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import ScanCamera from '~/components/scan/ScanCamera.vue'
import ScanManualEntry from '~/components/scan/ScanManualEntry.vue'
import StocktakeProgress from '~/components/stocktake/StocktakeProgress.vue'
import StocktakeOutcomeBadge from '~/components/stocktake/StocktakeOutcomeBadge.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import { formatDateTime } from '~/utils/format'
import { parseScannedTag } from '~/utils/scan'

// Mobile count page (FR-022, layout §15.1): progress, scan/manual entry,
// condition + note, distinct result for every observation, recent scans.
// Nothing is committed silently — the operator confirms each observation.
definePageMeta({ title: 'Stocktake count' })

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const service = useStocktakeService()
const { conditions, locations } = useReferenceData()

const { data: session, pending, error, refresh } = await useAsyncData(
  `stocktake-count-${uuid.value}`,
  () => service.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

useHead(() => ({ title: session.value ? `Count · ${session.value.name}` : 'Stocktake count' }))

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const notFound = computed(() => apiError.value && isNotFoundError(apiError.value))

/* Observation form */
const tag = ref('')
const condition = ref('')
const location = ref('')
const note = ref('')
const submitting = ref(false)
const submitError = ref<ApiError | null>(null)
const lastResult = ref<StocktakeObservation | null>(null)
const recent = ref<StocktakeObservation[]>([])

function onTag(raw: string): void {
  const parsed = parseScannedTag(raw)
  if (parsed) {
    tag.value = parsed
    submitError.value = null
  }
}

async function submit(): Promise<void> {
  submitError.value = null
  if (!tag.value.trim()) {
    submitError.value = new ApiError('Scan or enter an asset tag first.', { status: 400 })
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    const observation = await service.addObservation(uuid.value, {
      tag_scanned: tag.value.trim(),
      condition: condition.value || undefined,
      location: location.value || undefined,
      note: note.value.trim() || undefined,
    })
    lastResult.value = observation
    recent.value = [observation, ...recent.value].slice(0, 10)
    tag.value = ''
    note.value = ''
    void refresh()
  } catch (e) {
    submitError.value = ApiError.fromUnknown(e)
  } finally {
    submitting.value = false
  }
}

function dismissResult(): void {
  lastResult.value = null
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent'
</script>

<template>
  <div class="mx-auto max-w-2xl">
    <LoadingSkeleton v-if="pending && !session" :lines="3" label="Loading session…" />
    <EmptyState
      v-else-if="notFound"
      icon="search"
      title="Stocktake not found"
      message="This session does not exist or is outside your scope."
      action-to="/stocktakes"
      action-label="Back to stocktakes"
    />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Stocktake could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />

    <div v-else-if="session" class="space-y-6">
      <PageHeader :title="`Count · ${session.name}`">
        <template #breadcrumbs>
          <ol class="flex items-center gap-1">
            <li><NuxtLink to="/stocktakes" class="rounded hover:text-ink">Stocktakes</NuxtLink></li>
            <li aria-hidden="true">/</li>
            <li><NuxtLink :to="`/stocktakes/${uuid}`" class="rounded hover:text-ink">{{ session.name }}</NuxtLink></li>
            <li aria-hidden="true">/</li>
            <li aria-current="page" class="text-ink-secondary">Count</li>
          </ol>
        </template>
      </PageHeader>

      <StocktakeProgress :session="session" />

      <!-- Result of the last observation — distinct per outcome (layout §15.2). -->
      <div
        v-if="lastResult"
        role="status"
        class="flex items-start justify-between gap-3 rounded-xl border border-border bg-surface p-4"
      >
        <div>
          <p class="font-mono text-sm text-accent">{{ lastResult.tag_scanned }}</p>
          <div class="mt-1">
            <StocktakeOutcomeBadge :outcome="lastResult.outcome" />
          </div>
          <p v-if="lastResult.asset" class="mt-1 text-sm text-ink-secondary">{{ lastResult.asset.name }}</p>
        </div>
        <button
          type="button"
          class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-raised px-3 py-2 text-sm text-ink hover:bg-hover"
          @click="dismissResult"
        >
          Scan next
        </button>
      </div>

      <ScanCamera @decoded="onTag" />

      <div class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <ScanManualEntry :busy="false" @lookup="onTag" />
      </div>

      <form class="space-y-4 rounded-xl border border-border bg-surface p-4 sm:p-6" novalidate @submit.prevent="submit">
        <h2 class="text-base font-semibold text-ink">
          Record observation
          <span v-if="tag" class="ml-2 font-mono text-sm font-normal text-accent">{{ tag }}</span>
        </h2>

        <InlineAlert v-if="submitError" tone="error" :message="submitError.message" :correlation-id="submitError.correlationId" />

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField v-slot="{ inputId }" label="Condition observed">
            <select :id="inputId" v-model="condition" :class="inputClass">
              <option value="">Unchanged / unknown</option>
              <option v-for="c in conditions" :key="c.uuid" :value="c.uuid">{{ c.label }}</option>
            </select>
          </FormField>
          <FormField v-slot="{ inputId }" label="Observed location">
            <select :id="inputId" v-model="location" :class="inputClass">
              <option value="">Current session location</option>
              <option v-for="l in locations" :key="l.uuid" :value="l.uuid">{{ l.name }}</option>
            </select>
          </FormField>
        </div>

        <FormField v-slot="{ inputId }" label="Note">
          <input :id="inputId" v-model="note" type="text" placeholder="Optional note for this observation" :class="inputClass" autocomplete="off" >
        </FormField>

        <button
          type="submit"
          class="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
          :disabled="submitting || !tag"
        >
          <AppIcon v-if="!submitting" name="check" size="sm" />
          {{ submitting ? 'Recording…' : tag ? `Record observation for ${tag}` : 'Scan or enter a tag first' }}
        </button>
      </form>

      <section v-if="recent.length" aria-labelledby="recent-scans">
        <h2 id="recent-scans" class="mb-2 text-sm font-semibold text-ink">Recent scans this session</h2>
        <ul class="space-y-2">
          <li
            v-for="obs in recent"
            :key="obs.uuid"
            class="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2"
          >
            <div class="min-w-0">
              <span class="font-mono text-sm text-accent">{{ obs.tag_scanned }}</span>
              <span class="ml-2 text-xs text-muted">{{ formatDateTime(obs.observed_at) }}</span>
            </div>
            <StocktakeOutcomeBadge :outcome="obs.outcome" />
          </li>
        </ul>
      </section>

      <p class="text-xs text-muted">
        {{ codeToLabel(session.status) }} · Observations are confirmed by the backend before they
        count toward the session — a loss of connectivity will be shown as an error, never as a save.
      </p>
    </div>
  </div>
</template>
