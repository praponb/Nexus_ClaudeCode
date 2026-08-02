<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import InlineAlert from '~/components/InlineAlert.vue'

// Sign-in is a public SSR page; session bootstrap happens client-side (D-11).
definePageMeta({ layout: 'auth', title: 'Sign in' })
useHead({ title: 'Sign in' })

const route = useRoute()
const { login } = useAuth()

const username = ref('')
const password = ref('')
const pending = ref(false)
const error = ref<ApiError | null>(null)
const errorRef = ref<HTMLElement | null>(null)

const sessionExpired = computed(() => route.query.reason === 'expired')

/** Redirect allowlist: only same-origin absolute paths (design §13). */
function safeNext(): string {
  const next = route.query.next
  return typeof next === 'string' && next.startsWith('/') && !next.startsWith('//') ? next : '/'
}

async function onSubmit(): Promise<void> {
  if (pending.value) return
  pending.value = true
  error.value = null
  try {
    await login(username.value.trim(), password.value)
    await navigateTo(safeNext())
  } catch (e) {
    error.value = ApiError.fromUnknown(e)
    await nextTick()
    errorRef.value?.focus()
  } finally {
    pending.value = false
  }
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink placeholder:text-faint focus:border-accent'
</script>

<template>
  <div class="rounded-2xl border border-border bg-surface p-6 shadow-xl sm:p-8">
    <h1 class="text-xl font-bold text-ink">Sign in</h1>
    <p class="mt-1 text-sm text-muted">Use your organizational account to access the asset register.</p>

    <div v-if="sessionExpired" class="mt-4">
      <InlineAlert tone="info" message="Your session has expired. Sign in again to continue where you left off." />
    </div>

    <div v-if="error" ref="errorRef" tabindex="-1" class="mt-4">
      <InlineAlert tone="error" :message="error.message || 'Sign-in failed. Check your credentials and try again.'" :correlation-id="error.correlationId" />
    </div>

    <form class="mt-6 space-y-4" novalidate @submit.prevent="onSubmit">
      <div class="space-y-1.5">
        <label for="login-username" class="block text-sm font-medium text-ink-secondary">
          Username <span class="text-danger" aria-hidden="true">*</span>
        </label>
        <input
          id="login-username"
          v-model="username"
          type="text"
          required
          autocomplete="username"
          :class="inputClass"
        >
      </div>
      <div class="space-y-1.5">
        <label for="login-password" class="block text-sm font-medium text-ink-secondary">
          Password <span class="text-danger" aria-hidden="true">*</span>
        </label>
        <input
          id="login-password"
          v-model="password"
          type="password"
          required
          autocomplete="current-password"
          :class="inputClass"
        >
      </div>
      <button
        type="submit"
        class="inline-flex min-h-11 w-full items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="pending || !username.trim() || !password"
      >
        {{ pending ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>
  </div>
</template>
