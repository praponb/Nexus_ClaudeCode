<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'

const props = defineProps<{
  steps: string[]
  current: number
}>()

function state(index: number): 'done' | 'current' | 'todo' {
  if (index < props.current) return 'done'
  if (index === props.current) return 'current'
  return 'todo'
}
</script>

<template>
  <nav aria-label="Progress">
    <ol class="flex flex-wrap items-center gap-2">
      <li v-for="(step, index) in steps" :key="step" class="flex items-center gap-2">
        <span
          class="flex items-center gap-2 rounded-lg px-2 py-1 text-sm"
          :class="{
            'text-success': state(index) === 'done',
            'font-semibold text-accent': state(index) === 'current',
            'text-faint': state(index) === 'todo',
          }"
          :aria-current="state(index) === 'current' ? 'step' : undefined"
        >
          <span
            class="flex h-6 w-6 items-center justify-center rounded-full border text-xs font-bold"
            :class="{
              'border-success bg-success/10': state(index) === 'done',
              'border-accent bg-accent/10': state(index) === 'current',
              'border-border-strong': state(index) === 'todo',
            }"
          >
            <AppIcon v-if="state(index) === 'done'" name="check" size="sm" />
            <template v-else>{{ index + 1 }}</template>
          </span>
          <span class="hidden sm:inline">{{ step }}</span>
          <span class="sr-only sm:hidden">{{ step }}</span>
        </span>
        <span v-if="index < steps.length - 1" class="text-border-strong" aria-hidden="true">›</span>
      </li>
    </ol>
  </nav>
</template>
