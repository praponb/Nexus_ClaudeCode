<script setup lang="ts">
import type { AssetSummary } from '~/types/api'
import AppIcon from '~/components/AppIcon.vue'

const props = withDefaults(defineProps<{ autoFocus?: boolean }>(), { autoFocus: false })

const router = useRouter()
const searchService = useSearchService()

const query = ref('')
const results = ref<AssetSummary[]>([])
const open = ref(false)
const pending = ref(false)
const failed = ref(false)
const activeIndex = ref(-1)
let debounceTimer: ReturnType<typeof setTimeout> | undefined

const listboxId = useId()
const inputRef = ref<HTMLInputElement | null>(null)

onMounted(() => {
  if (props.autoFocus) inputRef.value?.focus()
})

watch(query, (value) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  const q = value.trim()
  activeIndex.value = -1
  if (q.length < 2) {
    results.value = []
    open.value = false
    failed.value = false
    return
  }
  debounceTimer = setTimeout(() => void run(q), 250)
})

async function run(q: string): Promise<void> {
  pending.value = true
  failed.value = false
  try {
    results.value = await searchService.searchAssets(q)
    open.value = true
  } catch {
    results.value = []
    failed.value = true
    open.value = true
  } finally {
    pending.value = false
  }
}

function optionId(index: number): string {
  return `${listboxId}-option-${index}`
}

function choose(asset: AssetSummary): void {
  reset()
  void router.push(`/assets/${asset.uuid}`)
}

function submitSearch(): void {
  const q = query.value.trim()
  if (!q) return
  reset()
  void router.push({ path: '/assets', query: { q } })
}

function reset(): void {
  open.value = false
  results.value = []
  query.value = ''
  activeIndex.value = -1
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'ArrowDown' && results.value.length) {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % results.value.length
  } else if (event.key === 'ArrowUp' && results.value.length) {
    event.preventDefault()
    activeIndex.value = (activeIndex.value - 1 + results.value.length) % results.value.length
  } else if (event.key === 'Enter') {
    if (activeIndex.value >= 0 && results.value[activeIndex.value]) {
      event.preventDefault()
      choose(results.value[activeIndex.value]!)
    } else {
      submitSearch()
    }
  } else if (event.key === 'Escape') {
    open.value = false
    activeIndex.value = -1
  }
}

function onBlur(): void {
  // Delay so mousedown on a suggestion still registers before closing.
  setTimeout(() => {
    open.value = false
  }, 150)
}

const statusMessage = computed(() => {
  if (pending.value) return 'Searching…'
  if (failed.value) return 'Search failed. Try again.'
  if (open.value && !results.value.length) return 'No assets match this search.'
  if (open.value) return `${results.value.length} result${results.value.length === 1 ? '' : 's'} available.`
  return ''
})
</script>

<template>
  <div class="relative w-full">
    <label :for="`${listboxId}-input`" class="sr-only">Search assets by tag, serial, name, model, custodian, or location</label>
    <div class="relative">
      <AppIcon name="search" size="sm" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
      <input
        :id="`${listboxId}-input`"
        ref="inputRef"
        v-model="query"
        type="search"
        role="combobox"
        :aria-expanded="open"
        :aria-controls="listboxId"
        :aria-activedescendant="activeIndex >= 0 ? optionId(activeIndex) : undefined"
        aria-autocomplete="list"
        autocomplete="off"
        placeholder="Search assets…"
        class="h-10 w-full rounded-lg border border-border bg-input pl-9 pr-3 text-sm text-ink placeholder:text-faint focus:border-accent"
        @keydown="onKeydown"
        @blur="onBlur"
      >
    </div>

    <p class="sr-only" role="status">{{ statusMessage }}</p>

    <div
      v-if="open"
      class="absolute left-0 right-0 top-full z-40 mt-1 overflow-hidden rounded-lg border border-border bg-raised shadow-2xl"
    >
      <ul v-if="results.length" :id="listboxId" role="listbox" aria-label="Search results" class="max-h-80 overflow-y-auto py-1">
        <li
          v-for="(asset, index) in results"
          :id="optionId(index)"
          :key="asset.uuid"
          role="option"
          :aria-selected="index === activeIndex"
          class="cursor-pointer px-3 py-2"
          :class="index === activeIndex ? 'bg-hover' : ''"
          @mousedown.prevent="choose(asset)"
          @mouseenter="activeIndex = index"
        >
          <div class="flex items-center justify-between gap-3">
            <span class="font-mono text-sm text-accent">{{ asset.tag }}</span>
            <span v-if="asset.status" class="text-xs text-muted">{{ asset.status.label }}</span>
          </div>
          <p class="truncate text-sm text-ink-secondary">{{ asset.name }}</p>
        </li>
      </ul>
      <p v-else class="px-3 py-3 text-sm" :class="failed ? 'text-danger' : 'text-muted'">
        {{ failed ? 'Search failed. Check your connection and try again.' : 'No assets match this search.' }}
      </p>
    </div>
  </div>
</template>
