<script setup lang="ts">
import type { DuplicateWarning } from '~/types/api'
import InlineAlert from '~/components/InlineAlert.vue'

/**
 * Duplicate pre-check results (FR-003, BR-008).
 *
 * The backend groups matched assets under the rule that found them, so each
 * warning renders with its own message and its own matches -- that pairing is
 * what lets the user actually "review them" as the Help page instructs.
 */
defineProps<{ warnings: DuplicateWarning[] }>()
</script>

<template>
  <div class="space-y-3 rounded-lg border border-warning/40 bg-warning/5 p-4">
    <InlineAlert
      tone="warning"
      title="Possible duplicate assets"
      message="Existing assets look similar to the one you are registering. Review them before saving."
    />

    <section v-for="warning in warnings" :key="warning.code" class="space-y-2">
      <p class="text-sm font-medium text-ink-secondary">{{ warning.message }}</p>
      <ul v-if="warning.matches.length" class="space-y-2">
        <li
          v-for="match in warning.matches"
          :key="match.uuid"
          class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2"
        >
          <div class="min-w-0">
            <NuxtLink
              :to="`/assets/${match.uuid}`"
              class="rounded font-mono text-sm text-accent hover:text-accent-hover"
            >
              {{ match.tag }}
            </NuxtLink>
            <span class="ml-2 text-sm text-ink-secondary">{{ match.name }}</span>
          </div>
          <NuxtLink
            :to="`/assets/${match.uuid}`"
            target="_blank"
            class="inline-flex min-h-11 items-center rounded-lg px-3 py-1 text-sm font-medium text-accent hover:bg-hover sm:min-h-0"
          >
            Review<span class="sr-only"> {{ match.tag }} (opens in a new tab)</span>
          </NuxtLink>
        </li>
      </ul>
    </section>
  </div>
</template>
