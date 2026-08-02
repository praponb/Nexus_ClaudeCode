<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import { BOTTOM_NAV, navForRole, isActivePath } from '~/utils/navigation'

const emit = defineEmits<{ (e: 'openMore'): void }>()

const route = useRoute()
const { role } = usePermissions()
const items = computed(() => navForRole(BOTTOM_NAV, role.value))
</script>

<template>
  <nav
    class="no-print fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-sidebar pb-[env(safe-area-inset-bottom)]"
    aria-label="Primary mobile navigation"
  >
    <ul class="grid grid-cols-5">
      <li v-for="item in items" :key="item.to">
        <NuxtLink
          :to="item.to"
          class="flex min-h-14 flex-col items-center justify-center gap-0.5 px-1 py-2 text-[11px] font-medium"
          :class="isActivePath(item, route.path) ? 'text-accent' : 'text-muted'"
          :aria-current="isActivePath(item, route.path) ? 'page' : undefined"
        >
          <AppIcon :name="item.icon" />
          <span>{{ item.label }}</span>
        </NuxtLink>
      </li>
      <li>
        <button
          type="button"
          class="flex min-h-14 w-full flex-col items-center justify-center gap-0.5 px-1 py-2 text-[11px] font-medium text-muted"
          aria-label="More navigation options"
          @click="emit('openMore')"
        >
          <AppIcon name="menu" />
          <span>More</span>
        </button>
      </li>
    </ul>
  </nav>
</template>
