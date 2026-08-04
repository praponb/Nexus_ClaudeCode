<script setup lang="ts">
import type { AssetDetail } from '~/types/api'
import PageHeader from '~/components/PageHeader.vue'
import AssetForm from '~/components/asset/AssetForm.vue'
import InlineAlert from '~/components/InlineAlert.vue'

definePageMeta({ title: 'Register asset' })
useHead({ title: 'Register asset' })

const { canManageAssets, authResolved } = usePermissions()

function onSaved(asset: AssetDetail): void {
  void navigateTo(`/assets/${asset.uuid}`)
}
</script>

<template>
  <div>
    <PageHeader title="Register asset" description="Add a new asset to the register. You can save a draft and complete details later.">
      <template #breadcrumbs>
        <ol class="flex items-center gap-1">
          <li><NuxtLink to="/assets" class="rounded hover:text-ink">Assets</NuxtLink></li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" class="text-ink-secondary">Register asset</li>
        </ol>
      </template>
    </PageHeader>

    <InlineAlert
      v-if="authResolved && !canManageAssets"
      tone="warning"
      title="You cannot register assets"
      message="Your role does not include asset registration. Contact an asset manager or operator."
    />
    <AssetForm v-else mode="create" @saved="onSaved" />
  </div>
</template>
