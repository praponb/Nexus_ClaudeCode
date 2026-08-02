// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  {
    ignores: ['playwright-report/**', 'test-results/**', 'coverage/**'],
  },
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
  {
    // error.vue is a Nuxt framework convention (single-word by design).
    files: ['error.vue'],
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
)
