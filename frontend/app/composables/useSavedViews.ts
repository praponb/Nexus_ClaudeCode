import type { SavedView } from '~/types/api'
import { unwrapList } from '~/types/api'
import type { AssetListFilters } from '~/utils/filters'
import { serializeAssetFilters } from '~/utils/filters'

/** Saved views: own views CRUD (design FR-006, cycle-1 scope). */
export function useSavedViews() {
  const api = useApi()
  const toast = useToast()
  const views = useState<SavedView[]>('saved-views:list', () => [])
  const loaded = useState<boolean>('saved-views:loaded', () => false)
  const pending = ref(false)

  async function refresh(): Promise<void> {
    try {
      const data = await api.get<unknown>('/saved-views/')
      views.value = unwrapList<SavedView>(data)
      loaded.value = true
    } catch {
      views.value = []
    }
  }

  if (import.meta.client && !loaded.value) {
    void refresh()
  }

  async function saveCurrent(name: string, filters: AssetListFilters): Promise<SavedView | null> {
    pending.value = true
    try {
      const view = await api.post<SavedView>('/saved-views/', {
        name,
        config: serializeAssetFilters(filters),
        shared: false,
        is_default: false,
      })
      views.value = [...views.value, view]
      toast.success(`View “${name}” saved`)
      return view
    } catch (e) {
      toast.error('Could not save the view', e instanceof Error ? e.message : undefined)
      return null
    } finally {
      pending.value = false
    }
  }

  async function remove(uuid: string): Promise<boolean> {
    pending.value = true
    try {
      await api.del(`/saved-views/${uuid}/`)
      views.value = views.value.filter((v) => v.uuid !== uuid)
      toast.success('View deleted')
      return true
    } catch (e) {
      toast.error('Could not delete the view', e instanceof Error ? e.message : undefined)
      return false
    } finally {
      pending.value = false
    }
  }

  return { views, loaded, pending, refresh, saveCurrent, remove }
}
