<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import { PRIMARY_NAV, navForRole, isActivePath } from '~/utils/navigation'

const props = withDefaults(defineProps<{ collapsed?: boolean }>(), { collapsed: false })
const emit = defineEmits<{ (e: 'toggle'): void }>()

const route = useRoute()
const { role } = usePermissions()
const items = computed(() => navForRole(PRIMARY_NAV, role.value))

const widthClass = computed(() => (props.collapsed ? 'w-16' : 'w-64'))
</script>

<template>
  <aside
    class="fixed bottom-0 left-0 top-14 z-30 flex-col border-r border-border bg-sidebar transition-[width]"
    :class="widthClass"
    aria-label="Primary navigation"
  >
    <nav class="flex-1 overflow-y-auto px-2 py-4">
      <ul class="space-y-1">
        <li v-for="item in items" :key="item.to">
          <NuxtLink
            :to="item.to"
            class="flex min-h-11 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium hover:bg-hover"
            :class="[
              isActivePath(item, route.path) ? 'bg-hover text-accent' : 'text-ink-secondary',
              collapsed ? 'justify-center px-0' : '',
            ]"
            :aria-current="isActivePath(item, route.path) ? 'page' : undefined"
            :title="collapsed ? item.label : undefined"
          >
            <AppIcon :name="item.icon" class="shrink-0" />
            <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
            <span
              v-if="!collapsed && item.planned"
              class="ml-auto rounded-full border border-border-strong px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-faint"
            >
              Soon
            </span>
            <span v-if="collapsed && item.planned" class="sr-only">(coming soon)</span>
          </NuxtLink>
        </li>
      </ul>
    </nav>
    <div class="border-t border-border p-2">
      <button
        type="button"
        class="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm text-muted hover:bg-hover hover:text-ink"
        :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :aria-expanded="!collapsed"
        @click="emit('toggle')"
      >
        <AppIcon :name="collapsed ? 'chevron-right' : 'chevron-left'" size="sm" />
        <span v-if="!collapsed">Collapse</span>
      </button>
    </div>
  </aside>
</template>
