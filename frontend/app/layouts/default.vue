<script setup lang="ts">
const sidebarCollapsed = ref(false)
const drawerOpen = ref(false)
const route = useRoute()
const sessionExpired = useState<boolean>('auth:session-expired', () => false)

watch(sessionExpired, async (expired) => {
  if (!expired) return
  sessionExpired.value = false
  const { clearSession } = useAuth()
  clearSession()
  if (route.path !== '/login') {
    await navigateTo({
      path: '/login',
      query: { next: route.fullPath, reason: 'expired' },
    })
  }
})
</script>

<template>
  <div class="min-h-dvh bg-canvas">
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[70] focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:font-semibold focus:text-on-accent"
    >
      Skip to main content
    </a>

    <ShellTopBar
      @open-drawer="drawerOpen = true"
      @toggle-sidebar="sidebarCollapsed = !sidebarCollapsed"
    />
    <ShellSidebar
      :collapsed="sidebarCollapsed"
      class="hidden lg:flex"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
    />
    <ShellDrawer :open="drawerOpen" @close="drawerOpen = false" />

    <div class="transition-[padding]" :class="sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'">
      <main id="main-content" tabindex="-1" class="mx-auto w-full max-w-7xl px-4 pb-28 pt-6 sm:px-6 lg:pb-12">
        <!--
          Private page bodies are client-only by design (nuxt.config.ts: SSR
          covers the shell and sign-in only; every page fetches with
          `server: false`). Rendering them on the server produced markup the
          client never reproduces -- the server sees a resolved-but-empty
          request and paints an empty state, while the client's first render is
          still pending and paints a skeleton. That swaps element types inside
          `v-if` chains, corrupting the hydrated VDOM and silently breaking
          NuxtLink navigation. Rendering the skeleton on both sides instead
          keeps hydration exact and removes the "No assets registered yet"
          flash that preceded every load.
        -->
        <ClientOnly>
          <slot />
          <template #fallback>
            <LoadingSkeleton :lines="6" label="Loading page…" />
          </template>
        </ClientOnly>
      </main>
    </div>

    <ShellBottomNav class="lg:hidden" @open-more="drawerOpen = true" />
    <AppToasts />
  </div>
</template>
