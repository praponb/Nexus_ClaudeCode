<script setup lang="ts">
import { ApiError } from '~/utils/errors'
import InlineAlert from '~/components/InlineAlert.vue'
import type { MfaSetup } from '~/composables/useAuth'

// Sign-in is a public SSR page; session bootstrap happens client-side (D-11).
definePageMeta({ layout: 'auth', title: 'Sign in' })
useHead({ title: 'Sign in' })

const route = useRoute()
const { login, startMfaSetup, confirmMfa, verifyMfa } = useAuth()

/**
 * `credentials` -> password step.
 * `setup`       -> role requires a second factor and none is enrolled yet.
 * `verify`      -> enrolled; a code is owed.
 * `recovery`    -> enrolment just finished; show the one-time recovery codes.
 */
type Step = 'credentials' | 'setup' | 'verify' | 'recovery'

const step = ref<Step>('credentials')
const username = ref('')
const password = ref('')
const code = ref('')
const recoveryCode = ref('')
const useRecovery = ref(false)
const setup = ref<MfaSetup | null>(null)
const recoveryCodes = ref<string[]>([])
const pending = ref(false)
const error = ref<ApiError | null>(null)
const errorRef = ref<HTMLElement | null>(null)

const sessionExpired = computed(() => route.query.reason === 'expired')

/** Redirect allowlist: only same-origin absolute paths (design §13). */
function safeNext(): string {
  const next = route.query.next
  return typeof next === 'string' && next.startsWith('/') && !next.startsWith('//') ? next : '/'
}

async function showError(e: unknown): Promise<void> {
  error.value = ApiError.fromUnknown(e)
  await nextTick()
  errorRef.value?.focus()
}

/** Any expired/abandoned second-factor attempt sends the user back to the start. */
function resetToCredentials(): void {
  step.value = 'credentials'
  password.value = ''
  code.value = ''
  recoveryCode.value = ''
  useRecovery.value = false
  setup.value = null
}

async function onSubmitCredentials(): Promise<void> {
  if (pending.value) return
  pending.value = true
  error.value = null
  try {
    const result = await login(username.value.trim(), password.value)
    if (!result.mfaRequired) {
      await navigateTo(safeNext())
      return
    }
    if (result.stage === 'setup') {
      setup.value = await startMfaSetup()
      step.value = 'setup'
    } else {
      step.value = 'verify'
    }
  } catch (e) {
    await showError(e)
  } finally {
    pending.value = false
  }
}

async function onConfirmSetup(): Promise<void> {
  if (pending.value) return
  pending.value = true
  error.value = null
  try {
    const { recoveryCodes: codes } = await confirmMfa(code.value.trim())
    recoveryCodes.value = codes
    step.value = 'recovery'
  } catch (e) {
    await showError(e)
    if (ApiError.fromUnknown(e).code === 'MFA_PENDING_EXPIRED') resetToCredentials()
  } finally {
    pending.value = false
  }
}

async function onVerify(): Promise<void> {
  if (pending.value) return
  pending.value = true
  error.value = null
  try {
    await verifyMfa(
      useRecovery.value ? { recoveryCode: recoveryCode.value.trim() } : { code: code.value.trim() },
    )
    await navigateTo(safeNext())
  } catch (e) {
    await showError(e)
    if (ApiError.fromUnknown(e).code === 'MFA_PENDING_EXPIRED') resetToCredentials()
  } finally {
    pending.value = false
  }
}

const inputClass =
  'h-11 w-full rounded-lg border border-border bg-input px-3 text-sm text-ink placeholder:text-faint focus:border-accent'
const buttonClass =
  'inline-flex min-h-11 w-full items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60'
</script>

<template>
  <div class="rounded-2xl border border-border bg-surface p-6 shadow-xl sm:p-8">
    <h1 class="text-xl font-bold text-ink">
      {{ step === 'credentials' ? 'Sign in'
        : step === 'setup' ? 'Set up two-factor authentication'
          : step === 'verify' ? 'Two-factor authentication'
            : 'Save your recovery codes' }}
    </h1>
    <p class="mt-1 text-sm text-muted">
      {{ step === 'credentials' ? 'Use your organizational account to access the asset register.'
        : step === 'setup' ? 'This account requires a second factor. Scan the code with an authenticator app, then enter the 6-digit code it shows.'
          : step === 'verify' ? 'Enter the 6-digit code from your authenticator app.'
            : 'Each code works once. Store them somewhere safe — they are shown only now.' }}
    </p>

    <div v-if="sessionExpired && step === 'credentials'" class="mt-4">
      <InlineAlert tone="info" message="Your session has expired. Sign in again to continue where you left off." />
    </div>

    <div v-if="error" ref="errorRef" tabindex="-1" class="mt-4">
      <InlineAlert
        tone="error"
        :message="error.message || 'Sign-in failed. Check your credentials and try again.'"
        :correlation-id="error.correlationId"
      />
    </div>

    <!-- Step 1: password -->
    <form v-if="step === 'credentials'" class="mt-6 space-y-4" novalidate @submit.prevent="onSubmitCredentials">
      <div class="space-y-1.5">
        <label for="login-username" class="block text-sm font-medium text-ink-secondary">
          Username <span class="text-danger" aria-hidden="true">*</span>
        </label>
        <input id="login-username" v-model="username" type="text" required autocomplete="username" :class="inputClass">
      </div>
      <div class="space-y-1.5">
        <label for="login-password" class="block text-sm font-medium text-ink-secondary">
          Password <span class="text-danger" aria-hidden="true">*</span>
        </label>
        <input id="login-password" v-model="password" type="password" required autocomplete="current-password" :class="inputClass">
      </div>
      <button type="submit" :class="buttonClass" :disabled="pending || !username.trim() || !password">
        {{ pending ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>

    <!-- Step 2a: first-time enrolment -->
    <form v-else-if="step === 'setup'" class="mt-6 space-y-4" novalidate @submit.prevent="onConfirmSetup">
      <!-- eslint-disable-next-line vue/no-v-html -- server-generated QR SVG, same source as asset labels -->
      <div v-if="setup" class="mx-auto w-44 rounded-lg bg-white p-3" v-html="setup.qr_svg" />
      <p v-if="setup" class="text-center text-xs text-muted">
        Can’t scan? Enter this key manually:
        <code class="mt-1 block break-all font-mono text-[11px] text-ink-secondary">{{ setup.secret }}</code>
      </p>
      <div class="space-y-1.5">
        <label for="mfa-setup-code" class="block text-sm font-medium text-ink-secondary">
          6-digit code <span class="text-danger" aria-hidden="true">*</span>
        </label>
        <input
          id="mfa-setup-code" v-model="code" type="text" required inputmode="numeric"
          autocomplete="one-time-code" maxlength="6" :class="inputClass"
        >
      </div>
      <button type="submit" :class="buttonClass" :disabled="pending || code.trim().length < 6">
        {{ pending ? 'Verifying…' : 'Activate and sign in' }}
      </button>
    </form>

    <!-- Step 2b: code from an enrolled authenticator -->
    <form v-else-if="step === 'verify'" class="mt-6 space-y-4" novalidate @submit.prevent="onVerify">
      <div v-if="!useRecovery" class="space-y-1.5">
        <label for="mfa-code" class="block text-sm font-medium text-ink-secondary">
          6-digit code <span class="text-danger" aria-hidden="true">*</span>
        </label>
        <input
          id="mfa-code" v-model="code" type="text" required inputmode="numeric"
          autocomplete="one-time-code" maxlength="6" autofocus :class="inputClass"
        >
      </div>
      <div v-else class="space-y-1.5">
        <label for="mfa-recovery" class="block text-sm font-medium text-ink-secondary">
          Recovery code <span class="text-danger" aria-hidden="true">*</span>
        </label>
        <input id="mfa-recovery" v-model="recoveryCode" type="text" required autocomplete="off" :class="inputClass">
      </div>
      <button
        type="submit" :class="buttonClass"
        :disabled="pending || (useRecovery ? !recoveryCode.trim() : code.trim().length < 6)"
      >
        {{ pending ? 'Verifying…' : 'Verify' }}
      </button>
      <button type="button" class="w-full text-center text-xs text-muted underline" @click="useRecovery = !useRecovery">
        {{ useRecovery ? 'Use an authenticator code instead' : 'Use a recovery code instead' }}
      </button>
    </form>

    <!-- Step 3: one-time recovery codes -->
    <div v-else class="mt-6 space-y-4">
      <ul class="grid grid-cols-2 gap-2 rounded-lg border border-border bg-input p-3 font-mono text-sm text-ink">
        <li v-for="c in recoveryCodes" :key="c">{{ c }}</li>
      </ul>
      <button type="button" :class="buttonClass" @click="navigateTo(safeNext())">
        I have saved these — continue
      </button>
    </div>
  </div>
</template>
