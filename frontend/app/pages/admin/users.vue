<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import { codeToLabel } from '~/utils/status'
import { formatDateTime } from '~/utils/format'
import type { Role } from '~/types/api'
import type { AdminUser } from '~/types/control'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import StatusBadge from '~/components/StatusBadge.vue'
import FormField from '~/components/FormField.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import EmptyState from '~/components/EmptyState.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import PaginationControls from '~/components/PaginationControls.vue'

// User administration (FR-027): role/scope assignment and activation.
// The final active system administrator cannot be deactivated — the backend
// enforces this and the error is shown verbatim. Secrets are never displayed.
definePageMeta({ title: 'User administration' })
useHead({ title: 'User administration' })

const service = useAdminService()
const toast = useToast()
const { user: currentUser } = useAuth()

const page = ref(1)
const search = ref('')
const appliedSearch = ref('')

const { data, pending, error, refresh } = await useAsyncData(
  'admin-users',
  () =>
    service.listUsers({
      page: page.value,
      page_size: 25,
      ...(appliedSearch.value ? { search: appliedSearch.value } : {}),
    }),
  { server: false, watch: [page, appliedSearch] },
)

const apiError = computed(() => (error.value ? ApiError.fromUnknown(error.value) : null))
const users = computed(() => data.value?.results ?? [])

const ROLES: Role[] = [
  'system_admin',
  'asset_manager',
  'department_manager',
  'operator',
  'employee',
  'auditor',
]

/* Edit dialog */
const editOpen = ref(false)
const editing = ref<AdminUser | null>(null)
const editRole = ref<Role>('employee')
const editActive = ref(true)
const editName = ref('')
const saving = ref(false)
const saveError = ref<ApiError | null>(null)

function openEdit(record: AdminUser): void {
  editing.value = record
  editRole.value = record.role
  editActive.value = record.active
  editName.value = record.display_name
  saveError.value = null
  editOpen.value = true
}

const isSelf = computed(() => Boolean(currentUser.value && editing.value?.uuid === currentUser.value.uuid))

async function save(): Promise<void> {
  if (!editing.value || saving.value) return
  saving.value = true
  saveError.value = null
  try {
    await service.updateUser(editing.value.uuid, {
      role: editRole.value,
      active: editActive.value,
      display_name: editName.value.trim() || undefined,
    })
    toast.success(`Updated ${editing.value.username}`)
    editOpen.value = false
    await refresh()
  } catch (e) {
    saveError.value = ApiError.fromUnknown(e)
  } finally {
    saving.value = false
  }
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink focus:border-accent'
</script>

<template>
  <div>
    <PageHeader title="Users" description="Accounts, roles, organizational scopes, and activation." />

    <form class="mb-4 flex flex-wrap items-end gap-2" role="search" @submit.prevent="appliedSearch = search; page = 1">
      <div>
        <label for="user-search" class="mb-1 block text-sm font-medium text-ink-secondary">Search users</label>
        <input id="user-search" v-model="search" type="search" placeholder="Name, username, or email" :class="inputClass" autocomplete="off" >
      </div>
      <button
        type="submit"
        class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
      >
        <AppIcon name="search" size="sm" />
        Search
      </button>
    </form>

    <LoadingSkeleton v-if="pending && !users.length" :lines="5" label="Loading users…" />
    <InlineAlert
      v-else-if="apiError"
      tone="error"
      title="Users could not be loaded"
      :message="apiError.message"
      :correlation-id="apiError.correlationId"
      retry-label="Retry"
      @retry="refresh()"
    />
    <EmptyState
      v-else-if="!users.length"
      icon="user-circle"
      title="No users found"
      message="Adjust the search or check back later."
    />

    <template v-else>
      <div class="overflow-x-auto rounded-xl border border-border bg-surface">
        <table class="min-w-full divide-y divide-border text-sm">
          <caption class="sr-only">User accounts</caption>
          <thead class="bg-raised">
            <tr>
              <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">User</th>
              <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Role</th>
              <th scope="col" class="hidden px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted xl:table-cell">Scopes</th>
              <th scope="col" class="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">Status</th>
              <th scope="col" class="hidden px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted lg:table-cell">Last sign-in</th>
              <th scope="col" class="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">
                <span class="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="record in users" :key="record.uuid" class="hover:bg-hover">
              <td class="px-3 py-3">
                <p class="font-medium text-ink">{{ record.display_name || record.username }}</p>
                <p class="text-xs text-muted">@{{ record.username }}<span v-if="record.email"> · {{ record.email }}</span></p>
              </td>
              <td class="whitespace-nowrap px-3 py-3 text-ink-secondary">{{ codeToLabel(record.role) }}</td>
              <td class="hidden max-w-56 px-3 py-3 xl:table-cell">
                <span class="block truncate text-ink-secondary">
                  {{ record.scopes?.length ? record.scopes.map((s) => s.name).join(', ') : '—' }}
                </span>
              </td>
              <td class="whitespace-nowrap px-3 py-3">
                <StatusBadge :label="record.active ? 'Active' : 'Inactive'" :code="record.active ? 'active' : 'inactive'" size="sm" />
              </td>
              <td class="hidden whitespace-nowrap px-3 py-3 text-muted lg:table-cell">
                {{ record.last_login ? formatDateTime(record.last_login) : 'Never' }}
              </td>
              <td class="whitespace-nowrap px-3 py-3 text-right">
                <button
                  type="button"
                  class="inline-flex min-h-11 items-center rounded-lg px-3 py-1 text-sm font-medium text-accent hover:bg-hover sm:min-h-0"
                  @click="openEdit(record)"
                >
                  Edit
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-4">
        <PaginationControls :page="page" :page-size="25" :total="data?.count ?? 0" :pending="pending" @change="page = $event" />
      </div>
    </template>

    <!-- Edit dialog -->
    <Teleport to="body">
      <div v-if="editOpen && editing" class="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6" @keydown="(e) => e.key === 'Escape' && (editOpen = false)">
        <div class="absolute inset-0 bg-canvas/80" aria-hidden="true" @click="editOpen = false" />
        <div role="dialog" aria-modal="true" aria-labelledby="edit-user-title" class="relative w-full max-w-lg rounded-t-2xl border border-border bg-raised p-6 sm:rounded-2xl">
          <h2 id="edit-user-title" class="text-lg font-semibold text-ink">
            Edit user — <span class="font-mono text-accent">@{{ editing.username }}</span>
          </h2>
          <p v-if="isSelf" class="mt-1 flex items-center gap-1 text-xs text-warning">
            <AppIcon name="warning" size="sm" />
            This is your own account. Role and activation changes take effect immediately.
          </p>

          <InlineAlert v-if="saveError" tone="error" class="mt-4" :message="saveError.message" :correlation-id="saveError.correlationId" />

          <form class="mt-4 space-y-4" @submit.prevent="save">
            <FormField v-slot="{ inputId }" label="Display name">
              <input :id="inputId" v-model="editName" type="text" :class="inputClass" autocomplete="off" >
            </FormField>
            <FormField v-slot="{ inputId }" label="Role" required>
              <select :id="inputId" v-model="editRole" :class="inputClass">
                <option v-for="r in ROLES" :key="r" :value="r">{{ codeToLabel(r) }}</option>
              </select>
            </FormField>
            <label class="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-ink-secondary">
              <input v-model="editActive" type="checkbox" class="h-4 w-4 accent-accent" >
              Account active
            </label>
            <p class="text-xs text-muted">
              Deactivation is audited. The final active system administrator cannot be deactivated.
            </p>

            <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                class="inline-flex min-h-11 items-center justify-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-hover"
                :disabled="saving"
                @click="editOpen = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="inline-flex min-h-11 items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
                :disabled="saving"
              >
                {{ saving ? 'Saving…' : 'Save changes' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>
