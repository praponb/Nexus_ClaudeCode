<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDateTime } from '~/utils/format'
import type { AppNotification, NotificationPreference } from '~/types/control'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import PaginationControls from '~/components/PaginationControls.vue'

// Notification center (FR-023): in-app list with read state, deep links, and
// per-type preferences. Mandatory compliance notifications cannot be disabled.
definePageMeta({ title: 'Notifications' })
useHead({ title: 'Notifications' })

const service = useNotificationsService()
const toast = useToast()

const page = ref(1)
const unreadOnly = ref(false)
const marking = ref<string | null>(null)

const { data, pending, error, refresh } = await useAsyncData(
  'notifications-list',
  () =>
    service.list({
      page: page.value,
      page_size: 25,
      ...(unreadOnly.value ? { unread: true } : {}),
    }),
  { server: false, watch: [page, unreadOnly] },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const items = computed(() => data.value?.results ?? [])

async function markRead(item: AppNotification): Promise<void> {
  if (item.read_at || marking.value) return
  marking.value = item.uuid
  try {
    await service.markRead(item.uuid)
    await refresh()
  } catch (e) {
    toast.error('Could not mark as read', ApiError.fromUnknown(e).message)
  } finally {
    marking.value = null
  }
}

/* ---- Preferences ---- */
const prefsOpen = ref(false)
const prefs = ref<NotificationPreference[]>([])
const prefsLoading = ref(false)
const prefsSaving = ref(false)
const prefsError = ref<ApiError | null>(null)

async function loadPrefs(): Promise<void> {
  prefsLoading.value = true
  prefsError.value = null
  try {
    const state = await service.preferences()
    prefs.value = state.preferences
  } catch (e) {
    prefsError.value = ApiError.fromUnknown(e)
  } finally {
    prefsLoading.value = false
  }
}

function togglePrefs(): void {
  prefsOpen.value = !prefsOpen.value
  if (prefsOpen.value && !prefs.value.length) void loadPrefs()
}

async function savePrefs(): Promise<void> {
  if (prefsSaving.value) return
  prefsSaving.value = true
  prefsError.value = null
  try {
    await service.updatePreferences({
      preferences: prefs.value.map((p) => ({
        type: p.type,
        enabled: p.mandatory ? true : p.enabled,
        mandatory: p.mandatory,
      })),
    })
    toast.success('Notification preferences saved')
    prefsOpen.value = false
  } catch (e) {
    prefsError.value = ApiError.fromUnknown(e)
  } finally {
    prefsSaving.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl">
    <PageHeader title="Notifications" description="In-app alerts for events in your scope.">
      <template #actions>
        <button
          type="button"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
          :aria-expanded="prefsOpen"
          @click="togglePrefs"
        >
          <AppIcon name="cog" size="sm" />
          Preferences
        </button>
      </template>
    </PageHeader>

    <!-- Preferences panel -->
    <section v-if="prefsOpen" aria-labelledby="notif-prefs" class="mb-6 rounded-xl border border-border bg-surface p-4 sm:p-6">
      <h2 id="notif-prefs" class="text-base font-semibold text-ink">Notification preferences</h2>
      <p class="mt-1 text-sm text-muted">
        Choose which optional notifications you receive. Compliance notifications are mandatory
        and cannot be turned off.
      </p>
      <InlineAlert v-if="prefsError" tone="error" class="mt-3" :message="prefsError.message" :correlation-id="prefsError.correlationId" />
      <p v-if="prefsLoading" class="mt-3 text-sm text-muted" role="status">Loading preferences…</p>
      <template v-else>
        <ul v-if="prefs.length" class="mt-2 space-y-1">
          <li v-for="pref in prefs" :key="pref.type" class="flex min-h-11 items-center gap-2 rounded-lg px-2 hover:bg-hover">
            <input
              :id="`pref-${pref.type}`"
              v-model="pref.enabled"
              type="checkbox"
              class="h-4 w-4 accent-accent"
              :disabled="pref.mandatory"
            >
            <label :for="`pref-${pref.type}`" class="flex-1 cursor-pointer text-sm text-ink-secondary">
              {{ pref.label || codeToLabel(pref.type) }}
              <span v-if="pref.mandatory" class="ml-2 rounded-full border border-border-strong px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-faint">
                Mandatory
              </span>
              <span v-if="pref.description" class="block text-xs text-muted">{{ pref.description }}</span>
            </label>
          </li>
        </ul>
        <p v-else class="mt-2 text-sm text-muted">No configurable notification types were provided by the server.</p>
        <div class="mt-4 flex justify-end">
          <button
            type="button"
            class="inline-flex min-h-11 items-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
            :disabled="prefsSaving"
            @click="savePrefs"
          >
            {{ prefsSaving ? 'Saving…' : 'Save preferences' }}
          </button>
        </div>
      </template>
    </section>

    <div class="mb-4">
      <label class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-ink-secondary">
        <input v-model="unreadOnly" type="checkbox" class="h-4 w-4 accent-accent" @change="page = 1" >
        Unread only
      </label>
    </div>

    <LoadingSkeleton v-if="pending && !items.length" :lines="4" label="Loading notifications…" />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Notifications could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <EmptyState
      v-else-if="!items.length"
      icon="bell"
      :title="unreadOnly ? 'No unread notifications' : 'No notifications yet'"
      :message="unreadOnly
        ? 'You are all caught up.'
        : 'Events that affect you — assignments, approvals, stocktakes — will appear here.'"
    />

    <template v-else>
      <ul class="space-y-2">
        <li
          v-for="item in items"
          :key="item.uuid"
          class="rounded-xl border bg-surface p-4"
          :class="item.read_at ? 'border-border' : 'border-accent/40'"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="flex items-center gap-2 font-medium text-ink">
                <span v-if="!item.read_at" class="h-2 w-2 shrink-0 rounded-full bg-accent" aria-hidden="true" />
                {{ item.title }}
                <span v-if="!item.read_at" class="sr-only">(unread)</span>
              </p>
              <p class="mt-1 text-sm text-ink-secondary">{{ item.body }}</p>
              <p class="mt-1 text-xs text-faint">
                {{ codeToLabel(item.type) }} · {{ formatDateTime(item.created_at) }}
              </p>
            </div>
            <div class="flex shrink-0 flex-col items-end gap-2">
              <NuxtLink
                v-if="item.link"
                :to="item.link"
                class="inline-flex min-h-11 items-center rounded-lg px-2 text-sm font-medium text-accent hover:text-accent-hover sm:min-h-0"
              >
                Open
              </NuxtLink>
              <button
                v-if="!item.read_at"
                type="button"
                class="inline-flex min-h-11 items-center rounded-lg border border-border-strong px-3 py-1 text-sm font-medium text-ink hover:bg-hover disabled:opacity-60 sm:min-h-0"
                :disabled="marking === item.uuid"
                @click="markRead(item)"
              >
                {{ marking === item.uuid ? 'Marking…' : 'Mark read' }}
              </button>
            </div>
          </div>
        </li>
      </ul>

      <div class="mt-4">
        <PaginationControls
          :page="page"
          :page-size="25"
          :total="data?.count ?? 0"
          :pending="pending"
          @change="page = $event"
        />
      </div>
    </template>
  </div>
</template>
