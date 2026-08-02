import {
  parseAssetQuery,
  serializeAssetFilters,
  activeFilterCount,
  type AssetListFilters,
} from '~/utils/filters'

/** URL-synced asset register filters (design §8.3: state in query params). */
export function useAssetFilters() {
  const route = useRoute()
  const router = useRouter()

  const filters = computed<AssetListFilters>(() => parseAssetQuery(route.query))
  const activeCount = computed(() => activeFilterCount(filters.value))

  function setFilters(patch: Partial<AssetListFilters>): void {
    const merged: AssetListFilters = { ...filters.value, ...patch }
    // Any filter/sort change resets to the first page unless page is explicit.
    if (patch.page === undefined) merged.page = 1
    void router.replace({ query: serializeAssetFilters(merged) })
  }

  function clearFilters(): void {
    void router.replace({ query: {} })
  }

  return { filters, activeCount, setFilters, clearFilters }
}
