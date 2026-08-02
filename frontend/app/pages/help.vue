<script setup lang="ts">
import PageHeader from '~/components/PageHeader.vue'

definePageMeta({ title: 'Help' })
useHead({ title: 'Help' })
</script>

<template>
  <div class="max-w-3xl">
    <PageHeader title="Help" description="How to work with the asset register." />

    <div class="space-y-6 text-sm text-ink-secondary">
      <section aria-labelledby="help-search" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="help-search" class="text-base font-semibold text-ink">Finding assets</h2>
        <ul class="mt-2 list-inside list-disc space-y-1">
          <li>Use the global search in the top bar to search by asset tag, serial number, name, model, custodian, or location. Exact tag matches appear first.</li>
          <li>On the asset register, combine filters (status, condition, category, department, location). Active filters appear as removable chips and the URL stays shareable.</li>
          <li>Save frequently used filter combinations as a saved view.</li>
        </ul>
      </section>

      <section aria-labelledby="help-register" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="help-register" class="text-base font-semibold text-ink">Registering and editing assets</h2>
        <ul class="mt-2 list-inside list-disc space-y-1">
          <li>Choose <strong class="text-ink">New asset</strong> from the register or top bar. Required fields are marked with an asterisk.</li>
          <li>Leave the asset tag blank to have one generated automatically.</li>
          <li>Before saving, the app warns you about possible duplicates — review them, then save anyway if the asset is genuinely new.</li>
          <li>If someone else edits the same asset while you work, you will be asked to reload the latest version before saving again.</li>
        </ul>
      </section>

      <section aria-labelledby="help-access" class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="help-access" class="text-base font-semibold text-ink">Access and visibility</h2>
        <p class="mt-2">
          What you can see and do depends on your role and organizational scope. Financial fields are
          restricted to authorized roles. If a page or action is hidden, the backend enforces the same
          restriction — contact an administrator to request changes to your access.
        </p>
      </section>
    </div>
  </div>
</template>
