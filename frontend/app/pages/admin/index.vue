<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'

// Administration overview: entry points into each section.
definePageMeta({ title: 'Administration' })
useHead({ title: 'Administration' })

const SECTIONS = [
  {
    to: '/admin/users',
    label: 'User administration',
    description: 'View users, assign roles and scopes, activate or deactivate accounts.',
    icon: 'user-circle' as const,
  },
  {
    to: '/admin/reference-data',
    label: 'Reference data',
    description: 'Categories, statuses, conditions, locations, departments, cost centers, and suppliers.',
    icon: 'tag' as const,
  },
  {
    to: '/admin/workflows',
    label: 'Workflow rules',
    description: 'Status transition rules that govern lifecycle changes (read-only view).',
    icon: 'refresh' as const,
  },
  {
    to: '/admin/audit',
    label: 'Audit log',
    description: 'Tamper-evident audit events with actor, action, target, and correlation IDs.',
    icon: 'tasks' as const,
  },
  {
    to: '/admin/settings',
    label: 'Settings & retention',
    description: 'Archiving and retention policy for business records.',
    icon: 'cog' as const,
  },
]
</script>

<template>
  <div>
    <h1 class="mb-4 text-2xl font-bold text-ink">Administration</h1>
    <ul class="grid grid-cols-1 gap-3 md:grid-cols-2">
      <li v-for="section in SECTIONS" :key="section.to">
        <NuxtLink
          :to="section.to"
          class="block h-full rounded-xl border border-border bg-surface p-4 hover:border-border-strong hover:bg-hover"
        >
          <div class="flex items-center gap-2">
            <AppIcon :name="section.icon" class="shrink-0 text-accent" />
            <h2 class="font-semibold text-ink">{{ section.label }}</h2>
          </div>
          <p class="mt-2 text-sm text-muted">{{ section.description }}</p>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
