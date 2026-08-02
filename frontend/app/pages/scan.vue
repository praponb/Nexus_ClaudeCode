<script setup lang="ts">
import { parseScannedTag } from '~/utils/scan'
import type { AssetSummary } from '~/types/api'
import AppIcon from '~/components/AppIcon.vue'
import PageHeader from '~/components/PageHeader.vue'
import ScanCamera from '~/components/scan/ScanCamera.vue'
import ScanManualEntry from '~/components/scan/ScanManualEntry.vue'
import InlineAlert from '~/components/InlineAlert.vue'

// Scanner + manual tag entry (FR-017, layout §15.2). Unknown codes produce a
// clear, non-destructive result; nothing is committed after a scan.
definePageMeta({ title: 'Scan' })
useHead({ title: 'Scan' })

const route = useRoute()
const search = useSearchService()

const lookingUp = ref(false)
const notFoundTag = ref('')
const lookupError = ref('')
const lastDecoded = ref('')

const initialTag = computed(() => {
  const q = route.query.tag
  return typeof q === 'string' ? q : ''
})

async function lookup(raw: string): Promise<void> {
  const tag = parseScannedTag(raw)
  notFoundTag.value = ''
  lookupError.value = ''
  if (!tag) {
    notFoundTag.value = raw.trim()
    return
  }
  if (lookingUp.value) return
  lookingUp.value = true
  try {
    const results: AssetSummary[] = await search.searchAssets(tag, 5)
    const exact = results.find((a) => a.tag.toLowerCase() === tag.toLowerCase()) ?? results[0]
    if (exact) {
      await navigateTo(`/assets/${exact.uuid}`)
      return
    }
    notFoundTag.value = tag
  } catch {
    lookupError.value = 'Lookup failed. Check your connection and try again.'
  } finally {
    lookingUp.value = false
  }
}

function onDecoded(value: string): void {
  if (value === lastDecoded.value) return
  lastDecoded.value = value
  void lookup(value)
}
</script>

<template>
  <div class="mx-auto max-w-2xl">
    <PageHeader title="Scan" description="Scan an asset QR code or enter its tag to open it." />

    <div class="space-y-6">
      <ScanCamera @decoded="onDecoded" />

      <div class="rounded-xl border border-border bg-surface p-4 sm:p-6">
        <ScanManualEntry :initial="initialTag" :busy="lookingUp" @lookup="lookup" />
      </div>

      <InlineAlert v-if="lookupError" tone="error" :message="lookupError" />

      <div
        v-if="notFoundTag"
        role="status"
        class="flex items-start gap-3 rounded-xl border border-warning/40 bg-warning/5 p-4"
      >
        <AppIcon name="warning" class="mt-0.5 shrink-0 text-warning" />
        <div>
          <p class="font-semibold text-ink">Unknown code</p>
          <p class="mt-1 text-sm text-ink-secondary">
            No asset matches <span class="font-mono text-ink">{{ notFoundTag }}</span> in your scope.
            Check the tag or contact an inventory operator. Nothing was changed.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
