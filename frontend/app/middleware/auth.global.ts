/**
 * UX-only auth redirect (design §12; stack §6.6: never a security boundary).
 * Runs client-side because the SSR shell carries no session context; private
 * data is fetched client-side and the backend enforces authorization.
 */
export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) return

  const PUBLIC_PATHS = new Set(['/login', '/403', '/404'])
  const { user, loaded, fetchUser } = useAuth()

  if (!loaded.value) {
    await fetchUser()
  }

  if (!user.value && !PUBLIC_PATHS.has(to.path)) {
    return navigateTo({
      path: '/login',
      query: to.fullPath !== '/' ? { next: to.fullPath } : {},
    })
  }

  if (user.value && to.path === '/login') {
    return navigateTo('/')
  }
})
