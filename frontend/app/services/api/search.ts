import type { AssetSummary } from '~/types/api'
import { unwrapList } from '~/types/api'

/** Global asset search: exact tag matches first, permission-scoped (FR-005). */
export function useSearchService() {
  const api = useApi()

  async function searchAssets(q: string, limit = 8): Promise<AssetSummary[]> {
    const data = await api.get<unknown>('/search/assets/', { q, page_size: limit })
    const results = unwrapList<AssetSummary>(data)
    const needle = q.trim().toLowerCase()
    return [...results].sort((a, b) => {
      const aExact = a.tag.toLowerCase() === needle ? 0 : 1
      const bExact = b.tag.toLowerCase() === needle ? 0 : 1
      return aExact - bExact
    })
  }

  return { searchAssets }
}
