<script setup lang="ts">
import type { AssetDetail } from '~/types/api'
import AppIcon from '~/components/AppIcon.vue'
import AssetExceptionDialog from '~/components/asset/AssetExceptionDialog.vue'
import AssetReservationDialog from '~/components/asset/AssetReservationDialog.vue'
import AssetLifecycleEndDialog from '~/components/asset/AssetLifecycleEndDialog.vue'

const props = defineProps<{ asset: AssetDetail }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const { canManageAssets, hasRole } = usePermissions()
const exceptionOpen = ref(false)
const reservationOpen = ref(false)
const endDialog = ref<'retire' | 'dispose' | 'reopen' | null>(null)

interface ActionLink {
  to: string
  label: string
  icon: 'user-circle' | 'refresh' | 'back' | 'wrench' | 'archive' | 'tag'
}

const links = computed<ActionLink[]>(() => [
  { to: `/assets/${props.asset.uuid}/assign`, label: 'Assign', icon: 'user-circle' },
  { to: `/assets/${props.asset.uuid}/transfer`, label: 'Transfer', icon: 'refresh' },
  { to: `/assets/${props.asset.uuid}/return`, label: 'Return', icon: 'back' },
])

const secondaryLinks = computed<ActionLink[]>(() => [
  { to: `/assets/${props.asset.uuid}/maintenance`, label: 'Maintenance', icon: 'wrench' },
  { to: `/assets/${props.asset.uuid}/documents`, label: 'Documents', icon: 'archive' },
  { to: `/assets/${props.asset.uuid}/label`, label: 'QR label', icon: 'tag' },
])

/** Retirement/disposal and reopen are elevated actions (FR-014). */
const canRetire = computed(() => hasRole('system_admin', 'asset_manager'))
const statusCode = computed(() => (props.asset.status?.code ?? '').toLowerCase())
const isEndOfLife = computed(() => ['retired', 'disposed'].includes(statusCode.value))

const primaryClass =
  'inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-hover'
</script>

<template>
  <div class="no-print flex flex-wrap items-center gap-2">
    <template v-if="canManageAssets && !isEndOfLife">
      <NuxtLink v-for="link in links" :key="link.to" :to="link.to" :class="primaryClass">
        <AppIcon :name="link.icon" size="sm" />
        {{ link.label }}
      </NuxtLink>
      <button type="button" :class="primaryClass" @click="reservationOpen = true">
        <AppIcon name="clock" size="sm" />
        Reserve
      </button>
      <span class="mx-1 hidden h-6 w-px bg-border sm:inline-block" aria-hidden="true" />
    </template>

    <NuxtLink v-for="link in secondaryLinks" :key="link.to" :to="link.to" :class="primaryClass">
      <AppIcon :name="link.icon" size="sm" />
      {{ link.label }}
    </NuxtLink>

    <button
      v-if="!isEndOfLife"
      type="button"
      class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-danger/50 bg-danger/10 px-3 py-2 text-sm font-medium text-danger hover:bg-danger/20"
      @click="exceptionOpen = true"
    >
      <AppIcon name="warning" size="sm" />
      Report exception
    </button>

    <template v-if="canRetire">
      <template v-if="!isEndOfLife">
        <button type="button" :class="primaryClass" @click="endDialog = 'retire'">
          <AppIcon name="archive" size="sm" />
          Retire
        </button>
        <button
          type="button"
          class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-danger/50 bg-danger/10 px-3 py-2 text-sm font-medium text-danger hover:bg-danger/20"
          @click="endDialog = 'dispose'"
        >
          <AppIcon name="warning" size="sm" />
          Dispose
        </button>
      </template>
      <button v-else type="button" :class="primaryClass" @click="endDialog = 'reopen'">
        <AppIcon name="refresh" size="sm" />
        Reopen
      </button>
    </template>

    <AssetReservationDialog
      :open="reservationOpen"
      :asset="asset"
      @close="reservationOpen = false"
      @reserved="emit('changed')"
    />
    <AssetExceptionDialog
      :open="exceptionOpen"
      :asset="asset"
      @close="exceptionOpen = false"
      @reported="emit('changed')"
    />
    <AssetLifecycleEndDialog
      v-if="endDialog"
      :open="Boolean(endDialog)"
      :asset="asset"
      :mode="endDialog"
      @close="endDialog = null"
      @changed="emit('changed')"
    />
  </div>
</template>
