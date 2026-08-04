<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import AssetSearch from '~/components/search/AssetSearch.vue'

const emit = defineEmits<{ (e: 'openDrawer' | 'toggleSidebar'): void }>()

const route = useRoute()
// `viewUser` (not `user`) so the header renders identically on the server and
// on the first client render -- see useAuth.
const { viewUser: user, logout } = useAuth()
const { canManageAssets } = usePermissions()

const profileOpen = ref(false)
const mobileSearchOpen = ref(false)

const pageTitle = computed(() => route.meta.title || 'Asset Inventory')

const roleLabel = computed(() => {
  const role = user.value?.role
  if (!role) return ''
  return role.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
})

async function signOut(): Promise<void> {
  profileOpen.value = false
  await logout()
  await navigateTo('/login')
}

function closeProfileOnEscape(event: KeyboardEvent): void {
  if (event.key === 'Escape') profileOpen.value = false
}
</script>

<template>
  <header class="no-print sticky top-0 z-40 border-b border-border bg-sidebar">
    <div class="flex h-14 items-center gap-2 px-3 sm:px-4">
      <button
        type="button"
        class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-ink-secondary hover:bg-hover lg:hidden"
        aria-label="Open navigation menu"
        @click="emit('openDrawer')"
      >
        <AppIcon name="menu" />
      </button>
      <button
        type="button"
        class="hidden min-h-11 min-w-11 items-center justify-center rounded-lg text-ink-secondary hover:bg-hover lg:inline-flex"
        aria-label="Toggle sidebar"
        @click="emit('toggleSidebar')"
      >
        <AppIcon name="menu" />
      </button>

      <NuxtLink to="/" class="flex items-center gap-2 rounded-lg px-1 py-1" aria-label="Asset Inventory home">
        <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-on-accent">
          <AppIcon name="cube" size="sm" />
        </span>
        <span class="hidden text-sm font-semibold text-ink md:inline">Asset Inventory</span>
      </NuxtLink>

      <p class="ml-1 min-w-0 flex-1 truncate text-sm text-muted lg:hidden">{{ pageTitle }}</p>

      <div class="hidden flex-1 justify-center px-6 lg:flex">
        <div class="w-full max-w-xl">
          <AssetSearch />
        </div>
      </div>

      <div class="ml-auto flex items-center gap-1">
        <button
          type="button"
          class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-ink-secondary hover:bg-hover lg:hidden"
          aria-label="Open search"
          :aria-expanded="mobileSearchOpen"
          @click="mobileSearchOpen = !mobileSearchOpen"
        >
          <AppIcon name="search" />
        </button>

        <NuxtLink
          v-if="canManageAssets"
          to="/assets/new"
          class="hidden min-h-11 items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover sm:inline-flex"
        >
          <AppIcon name="plus" size="sm" />
          New asset
        </NuxtLink>

        <NuxtLink
          to="/notifications"
          class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-ink-secondary hover:bg-hover"
          aria-label="Notifications"
        >
          <AppIcon name="bell" />
        </NuxtLink>
        <NuxtLink
          to="/help"
          class="hidden min-h-11 min-w-11 items-center justify-center rounded-lg text-ink-secondary hover:bg-hover sm:inline-flex"
          aria-label="Help"
        >
          <AppIcon name="help" />
        </NuxtLink>

        <div class="relative">
          <button
            type="button"
            class="inline-flex min-h-11 items-center gap-2 rounded-lg px-2 text-ink-secondary hover:bg-hover"
            aria-haspopup="menu"
            :aria-expanded="profileOpen"
            aria-label="Account menu"
            @click="profileOpen = !profileOpen"
            @keydown="closeProfileOnEscape"
          >
            <AppIcon name="user-circle" size="lg" />
            <span class="hidden max-w-32 truncate text-sm md:inline">{{ user?.display_name || 'Account' }}</span>
            <AppIcon name="chevron-down" size="sm" class="hidden md:inline" />
          </button>

          <div
            v-if="profileOpen"
            class="fixed inset-0 z-40"
            aria-hidden="true"
            @click="profileOpen = false"
          />
          <div
            v-if="profileOpen"
            role="menu"
            aria-label="Account"
            class="absolute right-0 z-50 mt-1 w-64 overflow-hidden rounded-lg border border-border bg-raised shadow-2xl"
            @keydown="closeProfileOnEscape"
          >
            <div class="border-b border-border px-4 py-3">
              <p class="truncate text-sm font-semibold text-ink">{{ user?.display_name || 'Signed in' }}</p>
              <p v-if="user?.email" class="truncate text-xs text-muted">{{ user.email }}</p>
              <p v-if="roleLabel" class="mt-1 text-xs text-muted">{{ roleLabel }}</p>
            </div>
            <button
              type="button"
              role="menuitem"
              class="flex min-h-11 w-full items-center gap-2 px-4 py-2 text-left text-sm text-ink-secondary hover:bg-hover"
              @click="signOut"
            >
              <AppIcon name="logout" size="sm" />
              Sign out
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="mobileSearchOpen" class="border-t border-border p-3 lg:hidden">
      <AssetSearch auto-focus />
    </div>
  </header>
</template>
