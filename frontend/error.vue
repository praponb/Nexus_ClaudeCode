<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'

const props = defineProps<{
  error: { statusCode?: number; statusMessage?: string; message?: string }
}>()

const statusCode = computed(() => props.error?.statusCode ?? 500)

const title = computed(() => {
  if (statusCode.value === 404) return 'Page not found'
  if (statusCode.value === 403) return 'Access denied'
  return 'Something went wrong'
})

const message = computed(() => {
  if (statusCode.value === 404) return 'The page you are looking for does not exist or has moved.'
  if (statusCode.value === 403) return 'You do not have permission to view this page.'
  return 'An unexpected error occurred. Try again, or contact support if the problem continues.'
})

useHead({ title })

function goHome(): void {
  void clearError({ redirect: '/' })
}
</script>

<template>
  <div class="flex min-h-dvh flex-col items-center justify-center bg-canvas px-4 text-center">
    <div class="flex h-14 w-14 items-center justify-center rounded-full bg-raised text-muted">
      <AppIcon :name="statusCode === 404 ? 'search' : 'warning'" size="lg" />
    </div>
    <p class="mt-4 font-mono text-sm text-muted">{{ statusCode }}</p>
    <h1 class="mt-1 text-2xl font-bold text-ink">{{ title }}</h1>
    <p class="mt-2 max-w-md text-sm text-muted">{{ message }}</p>
    <button
      type="button"
      class="mt-6 inline-flex min-h-11 items-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover"
      @click="goHome"
    >
      Go to dashboard
    </button>
  </div>
</template>
