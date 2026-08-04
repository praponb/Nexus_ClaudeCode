import { describe, expect, it } from 'vitest'
import {
  DEFAULT_FILTERS,
  activeFilterCount,
  hasActiveFilters,
  parseAssetQuery,
  savedViewConfigToQuery,
  serializeAssetFilters,
  toApiParams,
  toSavedViewConfig,
} from '~/utils/filters'

describe('parseAssetQuery', () => {
  it('returns defaults for an empty query', () => {
    expect(parseAssetQuery({})).toEqual(DEFAULT_FILTERS)
  })

  it('parses strings, arrays, and numeric params', () => {
    const filters = parseAssetQuery({
      q: ['laptop'],
      status: 'assigned',
      page: '3',
      page_size: '50',
      ordering: '-updated_at',
    })
    expect(filters.q).toBe('laptop')
    expect(filters.status).toBe('assigned')
    expect(filters.page).toBe(3)
    expect(filters.pageSize).toBe(50)
    expect(filters.ordering).toBe('-updated_at')
  })

  it('clamps invalid pagination values', () => {
    const filters = parseAssetQuery({ page: '-4', page_size: '99999' })
    expect(filters.page).toBe(1)
    expect(filters.pageSize).toBe(100)
  })
})

describe('serializeAssetFilters', () => {
  it('omits defaults to keep URLs shareable', () => {
    expect(serializeAssetFilters(DEFAULT_FILTERS)).toEqual({})
  })

  it('round-trips through parse', () => {
    const original = {
      ...DEFAULT_FILTERS,
      q: 'macbook',
      status: 'abc',
      page: 2,
      ordering: 'tag',
    }
    expect(parseAssetQuery(serializeAssetFilters(original))).toEqual(original)
  })
})

describe('activeFilterCount / hasActiveFilters', () => {
  it('counts only filter dimensions, not pagination or sort', () => {
    const filters = { ...DEFAULT_FILTERS, page: 3, ordering: 'tag' }
    expect(activeFilterCount(filters)).toBe(0)
    expect(hasActiveFilters({ ...filters, status: 'x' })).toBe(true)
  })
})

describe('toApiParams', () => {
  it('always includes pagination and only set filters', () => {
    expect(toApiParams(DEFAULT_FILTERS)).toEqual({ page: 1, page_size: 25 })
    expect(toApiParams({ ...DEFAULT_FILTERS, q: 'x', page: 2 })).toEqual({
      page: 2,
      page_size: 25,
      q: 'x',
    })
  })
})

describe('saved view config (FR-006)', () => {
  it('nests filter dimensions under `filters`, matching the backend contract', () => {
    const config = toSavedViewConfig({
      ...DEFAULT_FILTERS,
      q: 'laptop',
      category: 'cat-uuid',
      department: 'dept-uuid',
      ordering: '-updated_at',
    })
    // Flat keys at the top level are rejected by the API as "unknown config keys".
    expect(config).toEqual({
      filters: { q: 'laptop', category: 'cat-uuid', department: 'dept-uuid' },
      ordering: '-updated_at',
    })
    expect(Object.keys(config)).not.toContain('category')
  })

  it('does not persist pagination — a view is which assets, not which page', () => {
    const config = toSavedViewConfig({ ...DEFAULT_FILTERS, status: 's-uuid', page: 4 })
    expect(config.filters).toEqual({ status: 's-uuid' })
    expect(config).not.toHaveProperty('page')
    expect(config).not.toHaveProperty('page_size')
  })

  it('persists a non-default page size', () => {
    expect(toSavedViewConfig({ ...DEFAULT_FILTERS, pageSize: 50 }).page_size).toBe(50)
  })

  it('round-trips register state through the stored shape', () => {
    const original = {
      ...DEFAULT_FILTERS,
      q: 'dell',
      status: 'st-uuid',
      location: 'loc-uuid',
      ordering: 'tag',
    }
    const restored = parseAssetQuery(savedViewConfigToQuery(toSavedViewConfig(original)))
    expect(restored.q).toBe('dell')
    expect(restored.status).toBe('st-uuid')
    expect(restored.location).toBe('loc-uuid')
    expect(restored.ordering).toBe('tag')
  })

  it('flattens a stored config into query params', () => {
    const query = savedViewConfigToQuery({
      filters: { record_status: 'active', category: 'cat-uuid' },
      ordering: 'tag',
    })
    expect(query).toEqual({ record_status: 'active', category: 'cat-uuid', ordering: 'tag' })
  })

  it('preserves record_status from a seeded view through to the API params', () => {
    // The seeded "All active assets" view filters on record_status; dropping it
    // would silently change what the view means.
    const filters = parseAssetQuery(
      savedViewConfigToQuery({ filters: { record_status: 'active' }, ordering: 'tag' }),
    )
    expect(filters.recordStatus).toBe('active')
    expect(toApiParams(filters).record_status).toBe('active')
  })

  it('never stringifies a nested object into a query value', () => {
    // Regression: spreading the config produced `?filters=[object Object]`.
    const query = savedViewConfigToQuery({
      filters: { category: 'cat-uuid' },
    } as never)
    for (const value of Object.values(query)) {
      expect(value).not.toContain('[object Object]')
    }
  })

  it('tolerates malformed or empty configs without throwing', () => {
    expect(savedViewConfigToQuery(null)).toEqual({})
    expect(savedViewConfigToQuery(undefined)).toEqual({})
    expect(savedViewConfigToQuery({})).toEqual({})
    expect(savedViewConfigToQuery({ filters: undefined })).toEqual({})
  })
})
