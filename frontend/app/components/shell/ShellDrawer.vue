<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import { PRIMARY_NAV, navForRole, isActivePath } from '~/utils/navigation'

const props = withDefaults(defineProps<{ open?: boolean }>(), { open: false })
const emit = defineEmits<{ (e: 'close'): void }>()

const route = useRoute()
const { role } = usePermissions()
const { user, logout } = useAuth()
const items = computed(() => navForRole(PRIMARY_NAV, role.value))
const panelRef = ref<HTMLElement | null>(null)

watch(
  () => props.open,
  async (open) => {
    if (open) {
      await nextTick()
      panelRef.value?.querySelector<HTMLElement>('a, button')?.focus()
    }
  },
)

watch(
  () => route.fullPath,
  () => {
    if (props.open) emit('close')
  },
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') emit('close')
}

async function signOut(): Promise<void> {
  emit('close')
  await logout()
  await navigateTo('/login')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 lg:hidden" @keydown="onKeydown">
      <div class="absolute inset-0 bg-canvas/80" aria-hidden="true" @click="emit('close')" />
      <div
        ref="panelRef"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
        class="absolute bottom-0 left-0 top-0 flex w-72 max-w-[85vw] flex-col border-r border-border bg-sidebar"
      >
        <div class="flex h-14 items-center justify-between border-b border-border px-4">
          <span class="text-sm font-semibold text-ink">Asset Inventory</span>
          <button
            type="button"
            class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-ink-secondary hover:bg-hover"
            aria-label="Close navigation menu"
            @click="emit('close')"
          >
            <AppIcon name="close" />
          </button>
        </div>

        <nav class="flex-1 overflow-y-auto px-2 py-4" aria-label="Primary">
          <ul class="space-y-1">
            <li v-for="item in items" :key="item.to">
              <NuxtLink
                :to="item.to"
                class="flex min-h-11 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium hover:bg-hover"
                :class="isActivePath(item, route.path) ? 'bg-hover text-accent' : 'text-ink-secondary'"
                :aria-current="isActivePath(item, route.path) ? 'page' : undefined"
              >
                <AppIcon :name="item.icon" />
                <span class="truncate">{{ item.label }}</span>
                <span
                  v-if="item.planned"
                  class="ml-auto rounded-full border border-border-strong px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-faint"
                >
                  Soon
                </span>
              </NuxtLink>
            </li>
          </ul>
        </nav>

        <div class="border-t border-border p-4">
          <p class="truncate text-sm font-semibold text-ink">{{ user?.display_name || 'Signed in' }}</p>
          <button
            type="button"
            class="mt-2 flex min-h-11 w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink-secondary hover:bg-hover"
            @click="signOut"
          >
            <AppIcon name="logout" size="sm" />
            Sign out
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
