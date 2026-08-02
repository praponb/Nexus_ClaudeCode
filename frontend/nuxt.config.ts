import tailwindcss from '@tailwindcss/vite'

// Nuxt 4 application configuration.
// Rendering: SSR is enabled globally for the shell/sign-in pages; all private
// inventory data is fetched client-side only (see `server: false` in pages),
// so no user-specific data ever appears in SSR payloads or static caches.
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  ssr: true,

  modules: ['@nuxt/eslint'],

  // Typed API service modules are auto-imported alongside composables.
  imports: {
    dirs: ['services/api'],
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      // Only public values may live here. Overridden with NUXT_PUBLIC_API_BASE_URL.
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1',
    },
  },

  app: {
    head: {
      htmlAttrs: { lang: 'en', class: 'dark' },
      title: 'Asset Inventory',
      titleTemplate: '%s · Asset Inventory',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
        { name: 'color-scheme', content: 'dark' },
        { name: 'theme-color', content: '#090D14' },
        { name: 'description', content: 'Company asset inventory: register, track, and audit assets across their full lifecycle.' },
      ],
    },
  },

  vite: {
    plugins: [tailwindcss()],
  },

  typescript: {
    strict: true,
    typeCheck: false,
  },
})
