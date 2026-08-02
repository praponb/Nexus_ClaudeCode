<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'

// Settings & retention (FR-030): the archiving/retention policy as deployed.
// Retention rules are configured server-side; this page documents the
// effective behavior so administrators can act with confidence.
definePageMeta({ title: 'Settings' })
useHead({ title: 'Settings' })

const POLICIES = [
  {
    icon: 'archive' as const,
    title: 'No physical deletion',
    body: 'Business records are never hard-deleted through operational functions. Deactivation and archiving preserve the complete record, its references, and its history.',
  },
  {
    icon: 'clock' as const,
    title: 'Configurable retention rules',
    body: 'Retention periods per record type are configured server-side for the deployment. Contact your platform administrator to review or change the active rules.',
  },
  {
    icon: 'pin' as const,
    title: 'Legal and audit hold',
    body: 'Records under a legal or audit hold cannot be purged, regardless of the retention schedule. Holds are applied and lifted by authorized administrators only.',
  },
  {
    icon: 'success' as const,
    title: 'Archived records stay searchable',
    body: 'Archived and disposed assets remain searchable to authorized users for audit purposes, but cannot be reused for new operations.',
  },
]
</script>

<template>
  <div class="max-w-3xl">
    <PageHeader title="Settings & retention" description="How this deployment retains and archives inventory records." />

    <ul class="space-y-3">
      <li v-for="policy in POLICIES" :key="policy.title" class="flex gap-3 rounded-xl border border-border bg-surface p-4">
        <AppIcon :name="policy.icon" class="mt-0.5 shrink-0 text-accent" />
        <div>
          <h2 class="font-semibold text-ink">{{ policy.title }}</h2>
          <p class="mt-1 text-sm text-ink-secondary">{{ policy.body }}</p>
        </div>
      </li>
    </ul>

    <p class="mt-6 rounded-xl border border-border bg-input p-4 text-sm text-muted">
      Environment-specific settings (session timeouts, upload limits, notification rules) are
      managed through server configuration, not this interface, so they cannot be weakened
      accidentally from the browser.
    </p>
  </div>
</template>
