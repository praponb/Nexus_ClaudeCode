import { describe, expect, it } from 'vitest'
import {
  DEFAULT_FILTERS,
  activeFilterCount,
  hasActiveFilters,
  parseAssetQuery,
  serializeAssetFilters,
  toApiParams,
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
