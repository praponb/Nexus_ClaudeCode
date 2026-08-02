<script setup lang="ts">
import InlineAlert from '~/components/InlineAlert.vue'

// Administration shell (FR-026/027/030, FR-025 read): admin-only sections.
definePageMeta({ title: 'Administration' })
useHead({ title: 'Administration' })

const route = useRoute()
const { isAdmin } = usePermissions()
const { loaded } = useAuth()

const SECTIONS = [
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/reference-data', label: 'Reference data' },
  { to: '/admin/workflows', label: 'Workflows' },
  { to: '/admin/audit', label: 'Audit log' },
  { to: '/admin/settings', label: 'Settings' },
]

function isActive(to: string): boolean {
  if (to === '/admin/users' && route.path === '/admin') return true
  return route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <div>
    <InlineAlert
      v-if="loaded && !isAdmin"
      tone="warning"
      title="Restricted module"
      message="Administration is limited to system administrators."
    />
    <template v-else>
      <nav aria-label="Administration sections" class="no-print mb-6 overflow-x-auto">
        <ul class="flex gap-1 border-b border-border">
          <li v-for="section in SECTIONS" :key="section.to">
            <NuxtLink
              :to="section.to"
              class="inline-flex min-h-11 items-center gap-2 rounded-t-lg border-b-2 px-4 py-2 text-sm font-medium"
              :class="isActive(section.to)
                ? 'border-accent text-accent'
                : 'border-transparent text-ink-secondary hover:text-ink'"
              :aria-current="isActive(section.to) ? 'page' : undefined"
            >
              {{ section.label }}
            </NuxtLink>
          </li>
        </ul>
      </nav>
      <NuxtPage />
    </template>
  </div>
</template>
