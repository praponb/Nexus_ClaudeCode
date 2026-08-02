import type { CategoryRef, ConditionRef, NamedRef, StatusRef } from '~/types/api'
import { unwrapList } from '~/types/api'

export interface ReferenceDataState {
  categories: Ref<CategoryRef[]>
  statuses: Ref<StatusRef[]>
  conditions: Ref<ConditionRef[]>
  departments: Ref<NamedRef[]>
  locations: Ref<NamedRef[]>
  pending: Ref<boolean>
  error: Ref<unknown>
  refresh: () => Promise<void>
}

/** Reference data for selects/filters; fetched once per session (client-only). */
export function useReferenceData(): ReferenceDataState {
  const api = useApi()
  const categories = useState<CategoryRef[]>('ref:categories', () => [])
  const statuses = useState<StatusRef[]>('ref:statuses', () => [])
  const conditions = useState<ConditionRef[]>('ref:conditions', () => [])
  const departments = useState<NamedRef[]>('ref:departments', () => [])
  const locations = useState<NamedRef[]>('ref:locations', () => [])
  const pending = useState<boolean>('ref:pending', () => false)
  const error = useState<unknown>('ref:error', () => null)

  async function refresh(): Promise<void> {
    pending.value = true
    error.value = null
    try {
      const [cats, stats, conds, depts, locs] = await Promise.all([
        api.get<unknown>('/reference-data/categories/'),
        api.get<unknown>('/reference-data/statuses/'),
        api.get<unknown>('/reference-data/conditions/'),
        api.get<unknown>('/reference-data/departments/'),
        api.get<unknown>('/reference-data/locations/'),
      ])
      categories.value = unwrapList<CategoryRef>(cats)
      statuses.value = unwrapList<StatusRef>(stats)
      conditions.value = unwrapList<ConditionRef>(conds)
      departments.value = unwrapList<NamedRef>(depts)
      locations.value = unwrapList<NamedRef>(locs)
    } catch (e) {
      error.value = e
    } finally {
      pending.value = false
    }
  }

  if (import.meta.client && !categories.value.length && !statuses.value.length && !pending.value) {
    void refresh()
  }

  return { categories, statuses, conditions, departments, locations, pending, error, refresh }
}
