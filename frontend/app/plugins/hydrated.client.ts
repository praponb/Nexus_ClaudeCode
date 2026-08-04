/**
 * Marks the point at which the initial client-side hydration render has
 * committed (design §12; stack §6.6).
 *
 * The SSR shell deliberately carries no session context, so `auth:user` is
 * always null on the server while `auth.global.ts` has already resolved the
 * real session by the time the client hydrates. Any markup branching on the
 * session would therefore differ between the server render and the first
 * client render -- and for the role-filtered `v-for` navigation lists that
 * mismatch reuses DOM nodes positionally, leaving stale `href`s and a
 * corrupted VDOM that silently breaks subsequent `NuxtLink` navigation.
 *
 * Gating those branches on this flag makes the first client render reproduce
 * the server's "no session" markup exactly; the real values are applied one
 * tick later as an ordinary reactive update rather than a hydration patch.
 */
export default defineNuxtPlugin((nuxtApp) => {
  const hydrated = useState<boolean>('app:hydrated', () => false)

  nuxtApp.hook('app:suspense:resolve', () => {
    hydrated.value = true
  })
})
