<script setup lang="ts">
import type { AssetDetail } from '~/types/api'
import AppIcon from '~/components/AppIcon.vue'
import AssetStatusBadge from '~/components/asset/AssetStatusBadge.vue'
import AssetConditionBadge from '~/components/asset/AssetConditionBadge.vue'

const props = defineProps<{ asset: AssetDetail }>()

const toast = useToast()

const subtitle = computed(() =>
  [props.asset.category?.name, props.asset.manufacturer, props.asset.model].filter(Boolean).join(' · '),
)

async function copyTag(): Promise<void> {
  try {
    await navigator.clipboard.writeText(props.asset.tag)
    toast.success('Asset tag copied')
  } catch {
    toast.error('Could not copy the tag')
  }
}
</script>

<template>
  <div class="rounded-xl border border-border bg-surface p-4 sm:p-6">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div class="flex min-w-0 items-start gap-4">
        <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-raised text-accent">
          <AppIcon name="cube" size="lg" />
        </div>
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-mono text-sm font-medium text-accent">{{ asset.tag }}</span>
            <button
              type="button"
              class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-muted hover:bg-hover hover:text-ink sm:min-h-8 sm:min-w-8"
              :aria-label="`Copy asset tag ${asset.tag}`"
              @click="copyTag"
            >
              <AppIcon name="copy" size="sm" />
            </button>
          </div>
          <h1 class="mt-1 break-words text-xl font-bold text-ink sm:text-2xl">{{ asset.name }}</h1>
          <p v-if="subtitle" class="mt-1 text-sm text-muted">{{ subtitle }}</p>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <AssetStatusBadge :status="asset.status" />
            <AssetConditionBadge :condition="asset.condition" />
          </div>
        </div>
      </div>
      <div v-if="$slots.actions" class="no-print flex shrink-0 flex-wrap gap-2">
        <slot name="actions" />
      </div>
    </div>

    <dl class="mt-4 grid grid-cols-1 gap-3 border-t border-border pt-4 text-sm sm:grid-cols-3">
      <div>
        <dt class="text-muted">Custodian</dt>
        <dd class="mt-0.5 text-ink">{{ asset.custodian?.display_name || 'Unassigned' }}</dd>
      </div>
      <div>
        <dt class="text-muted">Department</dt>
        <dd class="mt-0.5 text-ink">{{ asset.department?.name || '—' }}</dd>
      </div>
      <div>
        <dt class="text-muted">Location</dt>
        <dd class="mt-0.5 text-ink">{{ asset.location?.name || '—' }}</dd>
      </div>
    </dl>
  </div>
</template>
